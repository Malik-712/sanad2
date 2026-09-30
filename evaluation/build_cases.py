"""Builds evaluation/cases.json. Deterministic: the same corpus gives the same file.

    python evaluation/build_cases.py

Where the cases come from:
- The 22 texts of the v0 smoke set (their exists / absent label is kept as it
  was written; see "label_source").
- A fixed sample of corpus records (chosen by a hash of the record id), used
  word for word: the whole matn ("exact"), a run of words from its middle
  ("partial"), or that run with two mechanical typos ("spelling").

The expected records of a case are only ever the records that contain the
query's words in the same order (evaluation/corpus_check.py). Nothing here
decides which hadith a text "is". A text that is not in the corpus word for
word gets status "needs_review" and no expected records; a human fills them.
Cases a human has marked "reviewed" are kept as they are on a rebuild, and so
are all cases written by a person (origin.kind "human", imported with
evaluation/review_sheet.py), whatever their status.

Every generated case has split "dev": these cases (and the v0 set, which was
used to set the thresholds) may be used for tuning. Held-out "test" cases are
set only through review_sheet.py.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from corpus_check import Corpus, words  # noqa: E402
from sanad_core.arabic import STOPWORDS  # noqa: E402
from sanad_core import provenance as prov  # noqa: E402

CASES_FILE = os.path.join(HERE, "cases.json")
V0_FILE = os.path.join(HERE, "v0_smoke_cases.json")
SEED = "sanad-eval-v1"
BOOKS = ["bukhari", "muslim", "abudawud", "tirmidhi", "nasai", "ibnmajah"]
PER_BOOK = 3            # records per book per generated category
MAX_RELEVANT = 8        # skip generic phrases found in more records than this
PARTIAL_WORDS = 8
SPELLING_WORDS = 10

# Typo rules: letters people mix up when typing Arabic. Applied to the
# normalized query, so they are real differences, not spelling variants that
# normalization already removes (أ/ا, ة/ه, ى/ي).
CONFUSABLE = {"ذ": "ز", "ز": "ذ", "ض": "ظ", "ظ": "ض", "س": "ص", "ص": "س", "ت": "ط", "ط": "ت", "ح": "ه", "ث": "س"}


def _h(s):
    return int(hashlib.sha1(f"{SEED}:{s}".encode()).hexdigest(), 16)


def _clean(text):
    return " ".join(text.replace("‏", " ").replace("‎", " ").split())


def typo(word, n):
    """One deterministic typo in word. Returns (new word, rule name)."""
    rules = ["confusable", "drop_letter", "swap_letters"]
    for r in rules[n % 3:] + rules[:n % 3]:
        if r == "confusable":
            for i, ch in enumerate(word):
                if ch in CONFUSABLE:
                    return word[:i] + CONFUSABLE[ch] + word[i + 1:], "حرف مكان حرف يشبهه نطقًا (" + ch + "←" + CONFUSABLE[ch] + ")"
        elif r == "drop_letter" and len(word) >= 5:
            i = len(word) // 2
            return word[:i] + word[i + 1:], "سقوط حرف"
        elif r == "swap_letters" and len(word) >= 4:
            i = len(word) // 2 - 1
            if word[i] != word[i + 1]:
                return word[:i] + word[i + 1] + word[i] + word[i + 2:], "تبديل حرفين متجاورين"
    return None, None


def case(cid, category, query, expect, relevant, corpus, qwords, origin, status="auto", **extra):
    c = {"id": cid, "category": category, "query": query, "expect": expect, "status": status,
         "split": "dev", "relevant": relevant,
         "evidence": [corpus.evidence(hid, qwords) for hid in relevant],
         "origin": origin}
    c.update(extra)
    return c


def from_v0(corpus):
    with open(V0_FILE, encoding="utf-8") as fh:
        v0 = json.load(fh)
    out = []
    for i, c in enumerate(v0, 1):
        qw = words(c["text"])
        cont = corpus.containing(qw)
        origin = {"kind": "v0_smoke", "label_source": "مجموعة v0 (evaluation/v0_smoke_cases.json): التسمية موجود/غير موجود كما كُتبت فيها"}
        cid = f"v0-{i:02d}"
        if c["exists"] and cont:
            whole = any(len(corpus.toks[h]) == len(qw) for h in cont)
            out.append(case(cid, "exact" if whole else "partial", c["text"], "exists", cont,
                            corpus, qw, origin))
        elif c["exists"]:
            out.append(case(cid, "variation", c["text"], "exists", [], corpus, qw, origin, status="needs_review",
                            review={"why": "النص ليس في أي سجل من المدونة بهذه الألفاظ وهذا الترتيب؛ يلزم مراجع يحدد السجلات المقصودة.",
                                    "candidates": corpus.closest(qw),
                                    "candidates_note": "مرشحون بعدد الكلمات المشتركة فقط، ليسوا جوابًا."}))
        else:
            if cont:
                raise SystemExit(f"{cid}: labelled absent but found word for word in {cont[:3]}; fix the label first")
            out.append(case(cid, "not_in_six_books", c["text"], "absent", [], corpus, qw, origin, status="needs_review",
                            check={"contained_in_any_record": False, "closest_records": corpus.closest(qw),
                                   "note": "لا يوجد سجل يحوي هذه الكلمات بترتيبها. كون النص ليس في الكتب الستة بأي لفظ يحتاج تأكيد مراجع."},
                            review={"why": "تأكيد أن النص ليس في الكتب الستة بلفظ آخر."}))
    return out


def sample(corpus, book, key, ok):
    ids = sorted((h["id"] for h in corpus.hadiths if h["book"] == book), key=lambda i: _h(key + i))
    for hid in ids:
        if ok(hid):
            yield hid


def generated(corpus):
    out, used = [], set()

    def origin(hid, rule):
        return {"kind": "corpus_sample", "record": hid, "rule": rule}

    for book in BOOKS:
        # exact: the whole matn, verbatim with its diacritics
        n = 0
        for hid in sample(corpus, book, "exact", lambda i: i not in used and 6 <= len(corpus.toks[i]) <= 30):
            qw = [t for t, _ in corpus.toks[hid]]
            cont = corpus.containing(qw)
            if len(cont) > MAX_RELEVANT:
                continue
            used.add(hid)
            out.append(case(f"exact-{hid}", "exact", _clean(corpus.by_id[hid]["matn"]), "exists", cont, corpus, qw,
                            origin(hid, "متن السجل كاملًا كما هو")))
            n += 1
            if n == PER_BOOK:
                break
        # partial: a run of words from the middle, verbatim
        n = 0
        for hid in sample(corpus, book, "partial", lambda i: i not in used and len(corpus.toks[i]) >= 20):
            ts = corpus.toks[hid]
            s = len(ts) // 3
            qw = [t for t, _ in ts[s:s + PARTIAL_WORDS]]
            cont = corpus.containing(qw)
            if len(cont) > MAX_RELEVANT:
                continue
            used.add(hid)
            a, b = ts[s][1], ts[s + PARTIAL_WORDS - 1][1]
            query = _clean(" ".join(corpus.by_id[hid]["matn"].split()[a:b + 1]))
            out.append(case(f"partial-{hid}", "partial", query, "exists", cont, corpus, qw,
                            origin(hid, f"{PARTIAL_WORDS} كلمات متتالية من وسط المتن كما هي")))
            n += 1
            if n == PER_BOOK:
                break
        # spelling: a run of words (normalized) with two typos
        n = 0
        for hid in sample(corpus, book, "spelling", lambda i: i not in used and len(corpus.toks[i]) >= 16):
            ts = corpus.toks[hid]
            s = len(ts) // 4
            qw = [t for t, _ in ts[s:s + SPELLING_WORDS]]
            cont = corpus.containing(qw)
            if len(cont) > MAX_RELEVANT:
                continue
            targets = [j for j, w in enumerate(qw) if len(w) >= 4 and w not in STOPWORDS]
            if len(targets) < 2:
                continue
            picks = sorted({targets[_h(hid) % len(targets)], targets[-1]})
            if len(picks) < 2:
                picks = [targets[0], targets[-1]]
            typed, typos = list(qw), []
            for k, j in enumerate(picks):
                new, rule = typo(qw[j], _h(hid) + k)
                if new:
                    typed[j] = new
                    typos.append({"from": qw[j], "to": new, "rule": rule})
            if len(typos) < 2:
                continue
            used.add(hid)
            out.append(case(f"spelling-{hid}", "spelling", " ".join(typed), "exists", cont, corpus, qw,
                            origin(hid, f"{SPELLING_WORDS} كلمات متتالية من المتن بعد توحيد الكتابة، مع خطأين إملائيين آليين"),
                            clean_query=" ".join(qw), typos=typos))
            n += 1
            if n == PER_BOOK:
                break
    return out


def reviewed_evidence(c, corpus):
    """Fill the provenance of records a human reviewer chose (quote = the
    record's matn as it is, since the query need not match it word for word)."""
    rv = c.get("review", {})
    method = (f"اختاره {rv.get('reviewer', '?')} بتاريخ {rv.get('date', '?')} بمقابلة نص المصدر "
              f"(ليس مراجعة مختص شرعي). {rv.get('basis', '')}").strip()
    c["evidence"] = []
    for hid in c["relevant"]:
        h = corpus.by_id[hid]
        quote = " ".join(h["matn"].split()[:30])
        c["evidence"].append({"id": hid, "book_title": h["book_title"], "number": h["number"],
                              **prov.lk(h, "Arabic_Matn", quote, method=method)})
    return c


def main():
    corpus = Corpus()
    kept, human = {}, []
    if os.path.exists(CASES_FILE):
        with open(CASES_FILE, encoding="utf-8") as fh:
            old = json.load(fh)["cases"]
        kept = {c["id"]: c for c in old if c.get("status") == "reviewed"}
        human = [c for c in old if c.get("origin", {}).get("kind") == "human"]
    cases = from_v0(corpus) + generated(corpus)
    cases = [reviewed_evidence(kept[c["id"]], corpus) if c["id"] in kept else c for c in cases]
    cases += [reviewed_evidence(c, corpus) if c["status"] == "reviewed" else c for c in human]
    doc = {
        "format": "sanad-eval-cases/1",
        "about": "حالات تقييم البحث. انظر evaluation/README.md لمعنى كل حقل.",
        "cases": cases,
    }
    with open(CASES_FILE, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    by = {}
    for c in cases:
        by.setdefault((c["category"], c["status"]), 0)
        by[(c["category"], c["status"])] += 1
    print(f"{len(cases)} cases written to {os.path.relpath(CASES_FILE)}")
    for (cat, st), n in sorted(by.items()):
        print(f"  {cat:18} {st:13} {n}")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    main()
