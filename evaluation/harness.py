"""Search evaluation: runs every case in evaluation/cases.json through
engine.search and computes the metrics. No model, no embeddings: each
expected record is one that contains the query word for word (or one a
human reviewer entered).

Metrics (all between 0 and 1):
- recall@k   ranked cases whose expected record is among the first k results.
- MRR        mean of 1 / rank of the first expected record (0 if not in the top 10).
- verdict precision  of the texts Sanad said exist, the share that do exist.
- verdict recall     of the texts that exist, the share Sanad said exist.
- top-1 precision    of the ranked cases Sanad said exist, the share whose first
                     result is an expected record.
- false "exists"     texts labelled absent that Sanad said exist. Must be 0.

"Ranked cases" are cases with status auto or reviewed and at least one
expected record. Cases with status needs_review count only for the verdict.

Splits: every case has `split` "dev" (may be used for tuning) or "test"
(held out: never used for tuning or training; only reviewed cases). The floors
in thresholds.json apply to the dev split; false "exists" must be 0 on all
cases.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from sanad_core import engine  # noqa: E402

CASES_FILE = os.path.join(HERE, "cases.json")
THRESHOLDS_FILE = os.path.join(HERE, "thresholds.json")
KS = (1, 3, 5, 10)
# Built by build_cases.py from the corpus and the v0 set; always present.
BUILT_CATEGORIES = ("exact", "partial", "variation", "spelling", "not_in_six_books")
# Written by the author and imported with review_sheet.py; may be empty.
#   meaning   a description or paraphrase of a hadith, written by a person
#   conflict  a hadith whose attributed grades differ between scholars
HUMAN_CATEGORIES = ("meaning", "conflict")
CATEGORIES = ("exact", "partial", "variation", "meaning", "conflict", "spelling", "not_in_six_books")
SPLITS = ("dev", "test")
# Category names accepted on import, mapped to the name used in cases.json.
CATEGORY_ALIASES = {"absent": "not_in_six_books"}
# Where training data for a learned model must be written (plan T12). Tests
# check that no held-out test case, and none of its expected records, is in it.
TRAINING_FILE_GLOBS = ("data/verdict_train*", "data/verdict_data*", "evaluation/training/*")
REVIEW_SCOPE = ("labels checked by the author against the source text; "
                "not reviewed by a Sharia specialist")
EXISTS_STATES = ("found", "near")


def load_cases(path=CASES_FILE):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["cases"]


def ranked(c):
    return c["expect"] == "exists" and c["status"] in ("auto", "reviewed") and bool(c["relevant"])


def run_case(c):
    r = engine.search(c["query"], limit=10, mode="verify")
    ids = [x["id"] for x in r["results"]]
    rel = set(c["relevant"])
    rank = next((i + 1 for i, hid in enumerate(ids) if hid in rel), None)
    return {"id": c["id"], "category": c["category"], "split": c.get("split", "dev"),
            "status": c["status"], "expect": c["expect"],
            "query": c["query"], "state": r["state"], "said_exists": r["state"] in EXISTS_STATES,
            "ranked": ranked(c), "rank": rank, "top": ids[:3]}


def metrics(results):
    rk = [r for r in results if r["ranked"]]
    pos = [r for r in results if r["expect"] == "exists"]
    said = [r for r in results if r["said_exists"]]
    m = {"cases": len(results), "ranked_cases": len(rk)}
    for k in KS:
        m[f"recall@{k}"] = _share(sum(1 for r in rk if r["rank"] and r["rank"] <= k), len(rk))
    m["mrr"] = round(sum(1 / r["rank"] for r in rk if r["rank"]) / len(rk), 3) if rk else None
    m["verdict_precision"] = _share(sum(1 for r in said if r["expect"] == "exists"), len(said))
    m["verdict_recall"] = _share(sum(1 for r in pos if r["said_exists"]), len(pos))
    rk_said = [r for r in rk if r["said_exists"]]
    m["top1_precision"] = _share(sum(1 for r in rk_said if r["rank"] == 1), len(rk_said))
    m["false_exists"] = sum(1 for r in results if r["expect"] == "absent" and r["said_exists"])
    m["absent_cases"] = sum(1 for r in results if r["expect"] == "absent")
    m["missed"] = sum(1 for r in pos if not r["said_exists"])
    return m


def _share(a, b):
    return round(a / b, 3) if b else None


def _summary(results):
    out = {"overall": metrics(results), "by_category": {}}
    for cat in CATEGORIES:
        sub = [r for r in results if r["category"] == cat]
        if sub:
            out["by_category"][cat] = metrics(sub)
    return out


def evaluate(cases=None):
    cases = cases if cases is not None else load_cases()
    results = [run_case(c) for c in cases]
    report = _summary(results)
    report["by_split"] = {s: _summary(sub) for s in SPLITS
                          if (sub := [r for r in results if r["split"] == s])}
    report["needs_review"] = sum(1 for c in cases if c["status"] == "needs_review")
    report["reviewed"] = sum(1 for c in cases if c["status"] == "reviewed")
    report["results"] = results
    return report


def load_thresholds(path=THRESHOLDS_FILE):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def check_thresholds(report, th=None):
    """List of failures (empty when every floor holds). Floors are checked on
    the dev split; false "exists" on every case."""
    th = th or load_thresholds()
    fails = []
    if report["overall"]["false_exists"] != 0:
        fails.append(f"false 'exists' = {report['overall']['false_exists']} (must be 0)")
    dev = report.get("by_split", {}).get("dev", report)
    for scope, floors in th["floors"].items():
        m = dev["overall"] if scope == "overall" else dev["by_category"].get(scope)
        if m is None:
            fails.append(f"{scope}: no cases")
            continue
        for name, floor in floors.items():
            v = m.get(name)
            if v is None or v < floor:
                fails.append(f"{scope} {name} = {v} (floor {floor})")
    return fails
