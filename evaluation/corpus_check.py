"""Word-for-word checks against the corpus, independent of the search engine.

Used to build and to re-check evaluation/cases.json. It answers only one
mechanical question: "which records contain these words, in this order?".
It never decides which hadith a text "is"; a text that is not found word for
word is left for a human reviewer (see evaluation/README.md).

Tokens are the record's Arabic_Matn words after Sanad's normalization
(diacritics and letter variants removed, honorifics dropped), each linked to
the original word it came from, so the exact source quote can be shown.
"""
import collections
import difflib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from sanad_core import engine, provenance as prov  # noqa: E402
from sanad_core.arabic import normalize, _HONORIFICS  # noqa: E402

_HONORIFIC_RUNS = sorted((normalize(h, False).split() for h in _HONORIFICS), key=len, reverse=True)

CONTAINS_METHOD = ("كلمات النص موجودة بهذا الترتيب في عمود Arabic_Matn من المدونة، بعد توحيد الكتابة "
                   "(حذف التشكيل وتوحيد صور الحروف)، مع قبول واو أو فاء متصلة بأول كلمة. فحص آلي في evaluation/corpus_check.py، وليس حكمًا علميًا.")


def tokenize(text):
    """[(normalized word, index of the original word)], honorifics removed."""
    toks = []
    for i, w in enumerate((text or "").split()):
        for t in normalize(w, drop_honorifics=False).split():
            toks.append((t, i))
    out, j = [], 0
    while j < len(toks):
        for run in _HONORIFIC_RUNS:
            if [t for t, _ in toks[j:j + len(run)]] == run:
                j += len(run)
                break
        else:
            out.append(toks[j])
            j += 1
    return out


def words(text):
    return [t for t, _ in tokenize(text)]


def _first_ok(tok, q0):
    """The first word may carry an attached و or ف (e.g. «ومن» for «من»)."""
    return tok == q0 or tok in ("و" + q0, "ف" + q0)


class Corpus:
    def __init__(self):
        self.hadiths = engine.data()["hadiths"]
        self.by_id = {h["id"]: h for h in self.hadiths}
        self.toks = {h["id"]: tokenize(h["matn"]) for h in self.hadiths}
        self.index = collections.defaultdict(set)
        for hid, ts in self.toks.items():
            for t, _ in ts:
                self.index[t].add(hid)

    def containing(self, qwords):
        """Ids of records whose matn contains qwords contiguously (in corpus order)."""
        if not qwords:
            return []
        first = self.index.get(qwords[0], set()) | self.index.get("و" + qwords[0], set()) | self.index.get("ف" + qwords[0], set())
        rest = [self.index.get(w, set()) for w in set(qwords[1:])]
        cands = set.intersection(first, *rest)
        return [h["id"] for h in self.hadiths if h["id"] in cands and self.span(h["id"], qwords)]

    def span(self, hid, qwords):
        """(first, last) original-word index of the first occurrence, or None."""
        ts = self.toks[hid]
        n = len(qwords)
        for i in range(len(ts) - n + 1):
            if _first_ok(ts[i][0], qwords[0]) and all(ts[i + k][0] == qwords[k] for k in range(1, n)):
                return ts[i][1], ts[i + n - 1][1]
        return None

    def evidence(self, hid, qwords):
        """A provenance record quoting the exact original words that matched."""
        h = self.by_id[hid]
        a, b = self.span(hid, qwords)
        quote = " ".join(h["matn"].split()[a:b + 1])
        rec = prov.lk(h, "Arabic_Matn", quote, method=CONTAINS_METHOD)
        return {"id": hid, "book_title": h["book_title"], "number": h["number"], **rec}

    def closest(self, qwords, n=3):
        """Records sharing the most words with qwords, for a human reviewer.
        This is a list of candidates to look at, never an answer."""
        qset = set(qwords)
        need = max(1, len(qset) // 2)
        counts = collections.Counter()
        for w in qset:
            for hid in self.index.get(w, ()):
                counts[hid] += 1
        scored = []
        for hid, c in counts.items():
            if c < need:
                continue
            tw = [t for t, _ in self.toks[hid]]
            sm = difflib.SequenceMatcher(a=qwords, b=tw, autojunk=False)
            matched = sum(m.size for m in sm.get_matching_blocks())
            scored.append((matched / len(qwords), c, hid))
        scored.sort(key=lambda x: (-x[0], -x[1], x[2]))
        out = []
        for share, _, hid in scored[:n]:
            h = self.by_id[hid]
            out.append({"id": hid, "book_title": h["book_title"], "number": h["number"],
                        "url": prov.lk_url(h), "query_words_matched_in_order": round(share, 2)})
        return out
