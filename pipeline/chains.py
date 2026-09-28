"""Corpus-level chain building, shared by build_data.py and reparse_chains.py.

Runs the isnad parser on every record, then two corpus-level steps that need
more than one hadith:

1. accusative spellings ("جابرا", "نافعا" -> "جابر", "نافع") when the plain
   form is a frequent narrator-name word in the corpus;
2. "بهذا الإسناد": a route that stops early and says it continues "with this
   chain" is completed from the hadith just before it in the same book, at
   the first name the two share. The inherited names keep a pointer to the
   hadith they were read from (`from`), so they can still be quoted.
"""
import collections
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from sanad_core.isnad import parse_isnad, _prefix_match  # noqa: E402

LOOKBACK = 3  # how many previous hadiths "بهذا الإسناد" may refer to


def add_source_files(recs, lk_files_path=os.path.join(ROOT, "data", "lk_files.json")):
    """Records are stored in the order the CSV files were read (sorted by
    chapter number), so the k-th chapter group of a book is the k-th file.
    Only used when the record does not already carry `src`; checks counts."""
    import json
    from sanad_core.provenance import LK_FOLDER
    if all(r.get("src") for r in recs):
        return
    with open(lk_files_path, encoding="utf-8") as fh:
        files = json.load(fh)["files"]
    groups = collections.defaultdict(list)
    prev = None
    for i, r in enumerate(recs):
        key = (r["book"], r["chapter"])
        if key != prev:
            groups[r["book"]].append([])
            prev = key
        groups[r["book"]][-1].append(i)
    for book, gs in groups.items():
        folder = LK_FOLDER[book]
        nums = files[folder]
        if len(nums) != len(gs):
            raise SystemExit(f"{book}: {len(gs)} chapter groups but {len(nums)} files; not guessing")
        for num, idxs in zip(nums, gs):
            for i in idxs:
                recs[i]["src"] = f"{folder}/Chapter{num}.csv"


def build_chains(recs):
    for r in recs:
        p = parse_isnad(r["isnad"], r["matn"])
        r["routes"] = p["routes"]
        r["fragments"] = p["fragments"]
        r["tahwil"] = p["tahwil"]
        r["same_isnad"] = p["same_isnad"]
        r["chain_repaired"] = p["repaired"]
        r["to_prophet"] = p["to_prophet"]
        for rt in r["routes"]:
            rt["to_prophet"] = p["to_prophet"]

    wc = collections.Counter(w for r in recs for rt in r["routes"] for n in rt["names"] for w in n["name"].split())

    def fix(word):
        if word.endswith("ا") and len(word) > 3 and wc[word[:-1]] >= 20 and wc[word[:-1]] > 3 * wc[word]:
            return word[:-1]
        return word

    for r in recs:
        for rt in r["routes"]:
            for n in rt["names"]:
                n["name"] = " ".join(fix(w) for w in n["name"].split())

    completed = 0
    for i, r in enumerate(recs):
        if not r["same_isnad"]:
            continue
        for rt in r["routes"]:
            tail = rt["names"][-1]["name"] if rt["names"] else None
            if not tail:
                continue
            done = False
            for back in range(1, LOOKBACK + 1):
                j = i - back
                if j < 0 or recs[j]["book"] != r["book"]:
                    break
                for prt in recs[j]["routes"]:
                    k = next((k for k, n in enumerate(prt["names"]) if _prefix_match(n["name"], tail)), None)
                    if k is None or k == len(prt["names"]) - 1:
                        continue
                    inherited = [{**n, "from": recs[j]["id"], "uncertain": True} for n in prt["names"][k + 1:]]
                    rt["names"] = rt["names"] + inherited
                    rt["join"] = rt["join"] + "+prior_isnad"
                    rt["prior"] = recs[j]["id"]
                    rt["to_prophet"] = prt.get("to_prophet", False)
                    done = True
                    break
                if done:
                    break
            completed += done

    for r in recs:
        # v0 field kept for older callers: the primary route
        r["chain"] = r["routes"][-1]["names"] if r["routes"] else []
        r["chain_partial"] = bool(r["fragments"])
    return {"same_isnad_completed": completed}
