"""Search and isnad-tree engine (pure Python, loaded once per server process)."""
import collections
import difflib
import gzip
import json
import math
import os
import re

from .arabic import normalize, tokens, char_ngrams, STOPWORDS
from .isnad import quote as isnad_quote, _tokens as isnad_tokens, _is_marker, TAHWIL
from . import provenance as prov

DATA_DIR = os.environ.get("SANAD_DATA", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))

# Decision thresholds for the three result states, set by hand on the v0 smoke
# examples (evaluation/v0_smoke_cases.json). Nothing here is learned. A model
# that replaces them must be trained on training data only, never on the
# held-out test cases (split "test" in evaluation/cases.json).
T_FOUND = 0.85      # ordered word alignment with the best matn -> "موجود في المصادر"
T_NEAR = 0.70       # -> "يوجد حديث قريب"
T_FAMILY = 0.45     # matn similarity to count as the same hadith in the tree

# Input limits: alignment is quadratic in the query length, so long pastes are
# cut before alignment (a hadith is rarely longer than this).
MAX_QUERY_CHARS = 1500
MAX_ALIGN_WORDS = 120
MAX_ANCHORS = 12

PROPHET = "النبي ﷺ"

_state = {}


def _load(name):
    with gzip.open(os.path.join(DATA_DIR, name), "rt", encoding="utf-8") as fh:
        return json.load(fh)


def data():
    if not _state:
        _state["hadiths"] = _load("hadiths.json.gz")
        _state["by_id"] = {h["id"]: i for i, h in enumerate(_state["hadiths"])}
        idx = _load("search_index.json.gz")
        _state["N"], _state["avgdl"], _state["dl"], _state["post"] = idx["N"], idx["avgdl"], idx["dl"], idx["post"]
        _state["families"] = _load("families.json.gz")
        tri = collections.defaultdict(set)
        for w in _state["post"]:
            for g in _grams(w):
                tri[g].add(w)
        _state["vocab_tri"] = tri
    return _state


def _grams(word):
    w = f" {word} "
    return {w[i:i + 3] for i in range(len(w) - 2)}


# ---------------------------------------------------------------- fuzzy terms
def expand_term(term, max_alts=3):
    """Return [(vocab_term, weight)]: the term itself if known, else close spellings."""
    d = data()
    if term in d["post"]:
        return [(term, 1.0)]
    g = _grams(term)
    cand = collections.Counter()
    for x in g:
        for w in d["vocab_tri"].get(x, ()):
            cand[w] += 1
    scored = []
    for w, c in cand.most_common(60):
        jac = c / len(g | _grams(w))
        if jac >= 0.4:
            scored.append((w, round(jac, 3)))
    scored.sort(key=lambda x: -x[1])
    return scored[:max_alts]


# ------------------------------------------------------------------- BM25
def bm25(query_terms, k1=1.4, b=0.75, limit=200):
    d = data()
    N, avgdl, dl, post = d["N"], d["avgdl"], d["dl"], d["post"]
    scores = collections.defaultdict(float)
    for term, weight in query_terms:
        p = post.get(term)
        if not p:
            continue
        df = len(p) // 2
        idf = math.log(1 + (N - df + 0.5) / (df + 0.5))
        for j in range(0, len(p), 2):
            doc, tf = p[j], p[j + 1]
            scores[doc] += weight * idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl[doc] / avgdl))
    return sorted(scores.items(), key=lambda x: -x[1])[:limit]


def _cos_counts(a, b):
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def containment(q_norm, doc_norm):
    """How much of the query's character 3-grams appear in the document."""
    q = collections.Counter(char_ngrams(q_norm))
    dset = set(char_ngrams(doc_norm))
    tot = sum(q.values())
    return sum(v for k, v in q.items() if k in dset) / tot if tot else 0.0


# ------------------------------------------------------ ordered alignment
_PREFIX = re.compile(r"^(وال|فال|بال|كال|لل|ال|و|ف|ب)(?=..)")


def _stem(w):
    return _PREFIX.sub("", w)


_SIM_CACHE = {}


def _word_sim(a, b):
    key = (a, b)
    r = _SIM_CACHE.get(key)
    if r is None:
        r = _word_sim_raw(a, b)
        if len(_SIM_CACHE) > 200_000:
            _SIM_CACHE.clear()
        _SIM_CACHE[key] = r
    return r


def _word_sim_raw(a, b):
    if a == b:
        return 1.0
    sa, sb = _stem(a), _stem(b)
    if sa == sb:
        return 0.95
    r = difflib.SequenceMatcher(None, sa, sb).ratio()
    return r if r >= 0.75 else 0.0


def idf(term):
    d = data()
    p = d["post"].get(term)
    df = len(p) // 2 if p else 1
    return math.log(1 + (d["N"] - df + 0.5) / (df + 0.5))


def alignment(query_norm, doc_norm):
    """Weighted share of the query words found in the same order inside one
    contiguous window of the document (tolerates small spelling differences).
    Rare words weigh more than common ones, so "من الإيمان" alone is weak."""
    q = query_norm.split()[:MAX_ALIGN_WORDS]
    doc = doc_norm.split()
    if not q or not doc:
        return 0.0
    w = [max(0.15, idf(t)) if t not in STOPWORDS else 0.15 for t in q]
    total = sum(w)
    best = 0.0
    anchors = {i for i, dw in enumerate(doc) for qw in q[:3] if _word_sim(qw, dw)}
    if not anchors:
        anchors = {i for i, dw in enumerate(doc) for qw in q[:12] if _word_sim(qw, dw)}
    span = len(q) + 3
    for a in sorted(anchors)[:MAX_ANCHORS]:
        win = doc[max(0, a - 1): a - 1 + span + 1]
        # ordered weighted LCS
        prev = [0.0] * (len(win) + 1)
        for i, qw in enumerate(q):
            cur = [0.0] * (len(win) + 1)
            for j, dw in enumerate(win):
                sim = _word_sim(qw, dw)
                cur[j + 1] = max(prev[j + 1], cur[j], prev[j] + w[i] * sim)
            prev = cur
        best = max(best, prev[-1] / total)
    return best


# ------------------------------------------------------------------ search
TOPIC_PREFIX = re.compile(r"^(?:حديث|احاديث|ابحث|اريد|ما هو|ما هي)\s+(?:(?:عن|في|حديث)\s+)?")


def detect_mode(query):
    return "topic" if TOPIC_PREFIX.match(normalize(query)) else "verify"


def search(query, limit=10, book=None, mode="auto"):
    """mode="verify": the user pasted a text and wants to know if it exists.
    mode="topic": the user describes a subject; results are listed without a verdict."""
    d = data()
    query = (query or "")[:MAX_QUERY_CHARS]
    if mode == "auto":
        mode = detect_mode(query)
    qn = normalize(query)
    if mode == "topic":
        qn = TOPIC_PREFIX.sub("", qn).strip()
    qterms = tokens(qn)
    if not qterms:
        return {"query": query, "mode": mode, "state": "empty", "results": []}
    expanded, corrections = [], {}
    for t in dict.fromkeys(qterms):
        alts = expand_term(t)
        expanded.extend(alts)
        if alts and alts[0][0] != t:
            corrections[t] = alts[0][0]
    cands = bm25(expanded, limit=150)
    if not cands:
        return {"query": query, "mode": mode, "state": "not_found", "results": [], "corrections": corrections}
    top_bm = cands[0][1]
    pre = []
    for doc, s in cands:
        h = d["hadiths"][doc]
        if book and h["book"] != book:
            continue
        pre.append((s / top_bm, doc))
    pre = pre[:40]
    results = []
    for bm, doc in pre:
        h = d["hadiths"][doc]
        al = alignment(qn, h["nm"])
        shortness = 1.0 / (1.0 + len(h["nm"].split()) / 60.0)  # prefer the focused narration
        score = (0.35 * bm + 0.6 * al + 0.05 * shortness) if mode == "verify" else (0.7 * bm + 0.25 * al + 0.05 * shortness)
        results.append((score, al, doc))
    results.sort(key=lambda x: -x[0])
    results = results[:limit]
    best_al = max((r[1] for r in results), default=0)
    if mode == "topic":
        state = "topic" if results else "not_found"
    elif best_al >= T_FOUND and len(qterms) >= 2:
        state = "found"
    elif best_al >= T_NEAR:
        state = "near"
    else:
        state = "not_found"
    out = []
    for score, al, doc in results:
        h = d["hadiths"][doc]
        item = {**card(h), "score": round(score, 3), "match": round(al, 3)}
        if mode == "verify" and al >= T_NEAR:
            item["diff"] = word_diff(qn, h["matn"], focus=True)
        out.append(item)
    return {"query": query, "mode": mode, "state": state, "corrections": corrections, "results": out}


# Sanad never shows these words as a label. A dataset grade containing them
# has no named scholar, so it is withheld (see the religious-sourcing skill).
FORBIDDEN_LABELS = ("موضوع", "متواتر")


def card(h):
    withheld = any(w in h["grade"] for w in FORBIDDEN_LABELS)
    grade = "" if withheld else h["grade"]
    return {
        "id": h["id"], "book": h["book"], "book_title": h["book_title"], "number": h["number"],
        "chapter": h["chapter"], "section": h["section"], "matn": h["matn"], "grade": grade, "grade_withheld": withheld,
        "matn_prov": prov.lk(h, "Arabic_Matn", h["matn"][:160] + ("…" if len(h["matn"]) > 160 else "")) if h["matn"] else None,
        "grade_prov": prov.lk(h, "Arabic_Grade", h["grade"],
                              method="نُقل كما هو من عمود Arabic_Grade في المدونة. المدونة لا تذكر قائل الحكم.",
                              attributed=False) if grade else None,
        "source_prov": prov.lk(h, "Chapter_Arabic / Hadith_number", f"{h['chapter']} — {h['number']}"),
    }


# ------------------------------------------------------------- word diff
def word_diff(user_text, source_text, focus=False, context=8):
    """Word-level diff between the user's text and the source matn.
    Words are compared after normalization, so only real differences show.
    With focus=True, only the part of the source around the match is returned."""
    a = [_stem(w) for w in normalize(user_text).split()]
    b_orig = source_text.split()
    b = [_stem(normalize(w)) for w in b_orig]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    blocks = [m for m in sm.get_matching_blocks() if m.size]
    lo, hi = 0, len(b)
    if focus and blocks:
        lo = max(0, blocks[0].b - context)
        hi = min(len(b), blocks[-1].b + blocks[-1].size + context)
    user_words = normalize(user_text).split()
    ops = []
    if lo > 0:
        ops.append({"t": "gap", "src": "…"})
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        j1c, j2c = max(j1, lo), min(j2, hi)
        src = " ".join(b_orig[j1c:j2c]) if j2c > j1c else ""
        if tag == "equal":
            if src:
                ops.append({"t": "same", "src": src})
        else:
            inside = (j2 > lo and j1 < hi) or (j1 == j2 and lo <= j1 <= hi)
            if not (inside and (src or i2 > i1)):
                continue
            # source words before the first match / after the last match are
            # just context the user did not paste, not a difference
            outside_core = blocks and i1 == i2 and (j2 <= blocks[0].b or j1 >= blocks[-1].b + blocks[-1].size)
            if outside_core:
                ops.append({"t": "ctx", "src": src})
            else:
                ops.append({"t": tag, "user": " ".join(user_words[i1:i2]), "src": src})
    if hi < len(b):
        ops.append({"t": "gap", "src": "…"})
    return ops


def compare_matn(a_text, b_text):
    """Word diff between two source texts, both kept verbatim.
    Words are compared after normalization and prefix stripping, so only real
    wording differences show (not diacritics or spelling variants)."""
    a_orig, b_orig = (a_text or "").split(), (b_text or "").split()
    a = [_stem(normalize(w)) for w in a_orig]
    b = [_stem(normalize(w)) for w in b_orig]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    ops = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        ops.append({"t": tag, "a": " ".join(a_orig[i1:i2]), "b": " ".join(b_orig[j1:j2])})
    same = sum(i2 - i1 for tag, i1, i2, _, _ in sm.get_opcodes() if tag == "equal")
    return {"ops": ops, "shared_words": same, "a_words": len(a), "b_words": len(b)}


# ------------------------------------------------------------- hadith + tree
def routes_of(h):
    """All routes of a hadith (v1 data), or the single v0 chain."""
    if h.get("routes") is not None:
        return h["routes"]
    return [{"names": h["chain"], "join": "direct", "to_prophet": True}] if h.get("chain") else []


def _name_view(h, n, join):
    """A narrator name as read from the isnad, with the words it came from."""
    d = data()
    src = h
    if n.get("from"):
        k = d["by_id"].get(n["from"])
        src = d["hadiths"][k] if k is not None else h
    q = isnad_quote(src["isnad"], src["matn"], n["span"]) if n.get("span") else ""
    how = prov.parse_method(join)
    if n.get("relative"):
        how += " الاسم مبني من إحالة في النص (مثل «عن أبيه»)، وليس مكتوبًا بلفظه."
    if n.get("from"):
        how += f" هذا الاسم من سند الحديث {src['book_title']} {src['number']}."
    return {
        "name": n["name"], "uncertain": bool(n.get("uncertain")), "relative": bool(n.get("relative")),
        "doubt": bool(n.get("doubt")), "from": n.get("from"),
        "prov": prov.lk(src, "Arabic_Isnad", q, method=how,
                        confidence="uncertain" if n.get("uncertain") else "high"),
    }


def isnad_words(h):
    """The isnad's original words, each tagged for display:
    "m" transmission word (rubricated), "n" part of a parsed name, "" other.
    Tags come from the parser's own tokens and spans, never from the display."""
    words = h["isnad"].split()
    kinds = [""] * len(words)
    for w, oi in isnad_tokens(h["isnad"]):
        if oi < len(words) and (_is_marker(w) or w in TAHWIL):
            kinds[oi] = "m"
    for r in routes_of(h):
        for n in r["names"]:
            if n.get("from") or not n.get("span"):
                continue
            for k in range(n["span"][0], min(n["span"][1], len(words))):
                if kinds[k] != "m":
                    kinds[k] = "n"
    for f in h.get("fragments", []):
        for n in f:
            for k in range(n["span"][0], min(n["span"][1], len(words))):
                if kinds[k] != "m":
                    kinds[k] = "n"
    return [[w, k] for w, k in zip(words, kinds)]


def hadith_record(hid):
    d = data()
    i = d["by_id"].get(hid)
    return d["hadiths"][i] if i is not None else None


def hadith(hid):
    d = data()
    i = d["by_id"].get(hid)
    if i is None:
        return None
    h = d["hadiths"][i]
    fam = family(i)
    routes = [{"join": r["join"], "to_prophet": r.get("to_prophet", True), "prior": r.get("prior"),
               "names": [_name_view(h, n, r["join"]) for n in r["names"]]} for r in routes_of(h)]
    fragments = [[_name_view(h, n, "direct") for n in f] for f in h.get("fragments", [])]
    return {**card(h), "isnad": h["isnad"], "comment": h["comment"], "compiler": h["compiler"],
            "gold_segmentation": h["gold_segmentation"], "chain": h["chain"],
            "chain_partial": h["chain_partial"], "refers_to": h.get("refers_to"),
            "routes": routes, "fragments": fragments, "tahwil": bool(h.get("tahwil")),
            "isnad_words": isnad_words(h), "repaired": bool(h.get("chain_repaired")),
            "same_isnad": bool(h.get("same_isnad")),
            "isnad_prov": prov.lk(h, "Arabic_Isnad", h["isnad"]),
            "comment_prov": prov.lk(h, "Arabic_Comment", h["comment"]) if h["comment"] else None,
            "family": [{**card(d["hadiths"][j]), "similarity": s} for j, s in fam if j != i]}


def family(i):
    """Other narrations of the same hadith: similar matn above T_FAMILY.
    A matn that only says "بمثله" is attached to the hadith it refers to."""
    d = data()
    h = d["hadiths"][i]
    base = i
    if h.get("refers_to"):
        base = d["by_id"].get(h["refers_to"], i)
    members = {base: 1.0, i: 1.0}
    for j, s in d["families"][base]:
        if s >= T_FAMILY:
            members[j] = s
    # narrations that point back ("بمثله") to a member join the family too
    for j in list(members):
        k = j + 1
        while k < len(d["hadiths"]) and d["hadiths"][k].get("refers_to") == d["hadiths"][j]["id"]:
            members.setdefault(k, members[j])
            k += 1
    return sorted(members.items(), key=lambda x: -x[1])


def _words_prefix(a, b):
    """True if one name is a word-prefix of the other ("عمر" / "عمر بن الخطاب")."""
    wa, wb = a.split(), b.split()
    k = min(len(wa), len(wb))
    return k >= 1 and wa[:k] == wb[:k]


def tree(hid, min_similarity=0.0):
    """Tree of all routes of a hadith, from the Prophet down to the compilers.

    Every route of every narration in the family is drawn (a تحويل chain or
    co-narrators give several routes per narration). Routes are merged
    top-down: at each level, a narrator joins an existing branch only if it
    hangs under the SAME teacher and the names match (equal, or one is a
    word-prefix of the other). That teacher-context rule avoids merging two
    different people who share a short name like "سفيان". Prefix merges are
    flagged (merge="prefix") and drawn dashed."""
    d = data()
    i = d["by_id"].get(hid)
    if i is None:
        return None
    nodes = {"prophet": {"key": "prophet", "label": PROPHET, "kind": "prophet", "uncertain": False,
                         "merge": "exact", "variants": [], "chains": set(), "hids": set(), "books": set(),
                         "parent": None, "depth": 0, "linked": True}}
    children = collections.defaultdict(list)
    chains = []
    incomplete = []
    counter = [0]

    def child(parent, name, kind, uncertain):
        for ck in children[parent]:
            c = nodes[ck]
            if c["kind"] == kind and (c["label"] == name or (kind != "book" and _words_prefix(c["label"], name))):
                if name != c["label"]:
                    c["merge"] = "prefix"
                if len(name.split()) > len(c["label"].split()):
                    c["variants"].append(c["label"])
                    c["label"] = name
                elif name != c["label"] and name not in c["variants"]:
                    c["variants"].append(name)
                c["uncertain"] = c["uncertain"] and uncertain
                return ck
        counter[0] += 1
        key = f"n{counter[0]}"
        nodes[key] = {"key": key, "label": name, "kind": kind, "uncertain": uncertain, "merge": "exact",
                      "variants": [], "chains": set(), "hids": set(), "books": set(), "parent": parent,
                      "depth": nodes[parent]["depth"] + 1, "linked": False}
        children[parent].append(key)
        return key

    for j, sim in family(i):
        if sim < min_similarity:
            continue
        h = d["hadiths"][j]
        for k, rt in enumerate(routes_of(h)):
            names = rt["names"]
            if not names:
                continue
            rid = f"{h['id']}#{k}"
            # one name and no mention of the Prophet after it: the chain was
            # cut (usually by the automatic isnad/matn split); not drawn
            if len(names) < 2 and not rt.get("to_prophet", True):
                incomplete.append({"id": rid, "hid": h["id"], "book_title": h["book_title"], "number": h["number"]})
                continue
            path = ["prophet"]
            cur = "prophet"
            for depth, n in enumerate(reversed(names)):
                cur = child(cur, n["name"], "companion" if depth == 0 else "narrator", bool(n.get("uncertain")))
                path.append(cur)
                if "prov" not in nodes[cur] and n.get("span"):
                    nodes[cur]["prov"] = _name_view(h, n, rt["join"])["prov"]
            if rt.get("to_prophet", True):
                nodes[path[1]]["linked"] = True
            cur = child(cur, h["compiler"], "book", False)
            path.append(cur)
            for key in path:
                nodes[key]["chains"].add(rid)
                nodes[key]["hids"].add(h["id"])
                nodes[key]["books"].add(h["book"])
            chains.append({"id": rid, "hid": h["id"], "book": h["book"], "book_title": h["book_title"],
                           "number": h["number"], "partial": bool(h.get("fragments")), "join": rt["join"],
                           "to_prophet": bool(rt.get("to_prophet", True)), "similarity": sim,
                           "length": len(names), "nodes": path})

    # companion label per route (after merging)
    for c in chains:
        c["companion"] = nodes[c["nodes"][1]]["label"] if len(c["nodes"]) > 2 else ""
    # convergence point (المدار): where the routes start to branch.
    # A node scores by how many routes pass through it times how many
    # branches leave it; the best-scoring node is where the routes fan out.
    mudar = None
    if len(chains) > 1:
        best = 0
        for n in nodes.values():
            if n["kind"] not in ("companion", "narrator"):
                continue
            branches = len(children[n["key"]])
            score = len(n["chains"]) * (branches - 1)
            if branches >= 2 and score > best:
                best, mudar = score, n["key"]
    edges = []
    for n in nodes.values():
        if n["parent"]:
            edges.append({"source": n["parent"], "target": n["key"], "chains": sorted(n["chains"]),
                          "unlinked": n["parent"] == "prophet" and not n["linked"]})
    for n in nodes.values():
        # teachers / students of a narrator inside this tree, read from the isnads
        n["teachers"] = [nodes[n["parent"]]["label"]] if n["parent"] and n["kind"] != "companion" else []
        n["students"] = [nodes[c]["label"] for c in children[n["key"]] if nodes[c]["kind"] != "book"]
        n["compilers"] = [nodes[c]["label"] for c in children[n["key"]] if nodes[c]["kind"] == "book"]
        if n["kind"] in ("companion", "narrator") and n.get("prov"):
            hid0 = n["prov"]["url"]
            n["relations_prov"] = prov.make(prov.LK_NAME, hid0, n["prov"]["quote"], prov.LK_RETRIEVED,
                                            "الشيوخ والتلاميذ هنا هم من قبله ومن بعده في أسانيد هذه الشجرة فقط، "
                                            "كما قرأها سند آليًا من نصوص الأسانيد. ليست قائمة كاملة بشيوخه وتلاميذه.",
                                            "uncertain" if n["uncertain"] or n["merge"] == "prefix" else "high")
    for n in nodes.values():
        n["chains"] = sorted(n["chains"])
        n["hids"] = sorted(n["hids"])
        n["books"] = sorted(n["books"])
    companions = sorted({c["companion"] for c in chains if c["companion"] and c["to_prophet"]})
    return {
        "id": hid, "nodes": list(nodes.values()), "edges": edges, "chains": chains, "mudar": mudar,
        "incomplete": incomplete,
        "summary": {"routes": len(chains), "narrations": len({c["hid"] for c in chains}),
                    "companions": len(companions), "companion_names": companions,
                    "books": sorted({c["book_title"] for c in chains})},
    }
