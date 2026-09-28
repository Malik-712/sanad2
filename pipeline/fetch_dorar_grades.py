"""Prefetch Dorar grade attributions for a bounded list of hadiths.

Uses only Dorar's official API (see sanad_core/dorar.py for the access
policy), one request per distinct query, at least 2.5 s apart, and stores the
raw parsed results with their retrieval date in data/dorar_grades.json.gz.
Queries already stored are not fetched again. Run:

    python pipeline/fetch_dorar_grades.py            # default list
    python pipeline/fetch_dorar_grades.py bukhari-1  # specific ids
"""
import datetime
import gzip
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sanad_core import dorar, engine  # noqa: E402

MAX_QUERIES = 80
FAMILY_PER_CASE = 6


def default_ids():
    """The texts the evaluation says exist, their family, and the demo hadiths."""
    with open(os.path.join(ROOT, "evaluation", "smoke_cases.json"), encoding="utf-8") as fh:
        cases = json.load(fh)
    ids = ["bukhari-1", "bukhari-134", "muslim-4414"]
    for c in cases:
        if not c["exists"]:
            continue
        r = engine.search(c["text"], mode="verify")
        if not r["results"]:
            continue
        top = r["results"][0]["id"]
        ids.append(top)
        ids += [x["id"] for x in engine.hadith(top)["family"][:FAMILY_PER_CASE]]
    return list(dict.fromkeys(ids))


def main(ids):
    store = {"queries": {}}
    if os.path.exists(dorar.BUILT_CACHE):
        with gzip.open(dorar.BUILT_CACHE, "rt", encoding="utf-8") as fh:
            store = json.load(fh)
    todo = []
    for hid in ids:
        h = engine.hadith_record(hid)
        if h and h["matn"]:
            q = dorar._query_for(h["matn"])
            if q and q not in store["queries"] and q not in todo:
                todo.append(q)
    todo = todo[:MAX_QUERIES]
    print(f"{len(ids)} hadiths, {len(todo)} new queries (at least {dorar.MIN_INTERVAL}s apart)")
    for n, q in enumerate(todo, 1):
        try:
            results = dorar.parse(dorar.fetch(q))
        except Exception as exc:
            print(f"  {n}/{len(todo)} failed ({type(exc).__name__}); stopping, nothing is retried")
            break
        store["queries"][q] = {"results": results, "retrieved": datetime.date.today().isoformat()}
        print(f"  {n}/{len(todo)} {len(results)} results")
    store["meta"] = {"source": dorar.SOURCE_NAME, "api": dorar.API, "user_agent": dorar.USER_AGENT,
                     "min_interval_s": dorar.MIN_INTERVAL, "updated": datetime.date.today().isoformat()}
    with gzip.open(dorar.BUILT_CACHE, "wt", encoding="utf-8", compresslevel=9) as fh:
        json.dump(store, fh, ensure_ascii=False, separators=(",", ":"))
    print("stored queries:", len(store["queries"]))


if __name__ == "__main__":
    main(sys.argv[1:] or default_ids())
