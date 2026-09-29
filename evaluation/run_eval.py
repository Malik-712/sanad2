"""Search evaluation report. Run:

    python evaluation/run_eval.py            # summary table + failures
    python evaluation/run_eval.py -v         # every case
    python evaluation/run_eval.py --json     # machine-readable

Exit code 1 if any false "exists" or any floor in thresholds.json is broken.
Cases and metrics: evaluation/README.md.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import KS, check_thresholds, evaluate, load_thresholds  # noqa: E402

LABELS = {"exact": "exact text", "partial": "partial quote", "variation": "wording variation",
          "spelling": "spelling mistakes", "not_in_six_books": "not in the six books"}


def pct(v):
    return "   —" if v is None else f"{v * 100:3.0f}%"


def table(report):
    cols = [f"R@{k}" for k in KS] + ["MRR", "V-prec", "V-rec", "Top1-P", "false+"]
    head = f"{'':22}{'cases':>6}{'ranked':>7}" + "".join(f"{c:>8}" for c in cols)
    lines = [head, "-" * len(head)]

    def row(name, m):
        vals = [pct(m[f"recall@{k}"]) for k in KS]
        vals.append("   —" if m["mrr"] is None else f"{m['mrr']:.2f}")
        vals += [pct(m["verdict_precision"]), pct(m["verdict_recall"]), pct(m["top1_precision"]), str(m["false_exists"])]
        lines.append(f"{name:22}{m['cases']:>6}{m['ranked_cases']:>7}" + "".join(f"{v:>8}" for v in vals))

    for cat, m in report["by_category"].items():
        row(LABELS.get(cat, cat), m)
    lines.append("-" * len(head))
    row("ALL", report["overall"])
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    report = evaluate()
    fails = check_thresholds(report, load_thresholds())
    if a.json:
        print(json.dumps({k: v for k, v in report.items() if a.verbose or k != "results"} | {"failures": fails},
                         ensure_ascii=False, indent=1))
        return 1 if fails else 0

    o = report["overall"]
    print("Sanad search evaluation\n")
    print(table(report))
    print("""
R@k     recall@k: the expected record is in the first k results
MRR     mean of 1/rank of the first expected record (1.00 = always first)
V-prec  verdict precision: of texts Sanad said exist, how many do
V-rec   verdict recall: of texts that exist, how many Sanad said exist
Top1-P  of ranked texts Sanad said exist, how often the first result is expected
false+  texts labelled absent that Sanad said exist (hard requirement: 0)
ranked  cases with checked expected records; the others count for the verdict only
""")
    print(f"False \"exists\": {o['false_exists']} of {o['absent_cases']} absent texts"
          f"  {'OK' if o['false_exists'] == 0 else 'FAIL'}")
    print(f"Cases waiting for a human reviewer: {report['needs_review']} (see evaluation/README.md)")

    misses = [r for r in report["results"] if (r["ranked"] and r["rank"] != 1) or
              (r["said_exists"] != (r["expect"] == "exists"))]
    if misses or a.verbose:
        print("\nCases not answered perfectly:" if not a.verbose else "\nAll cases:")
        for r in (report["results"] if a.verbose else misses):
            ok = r["said_exists"] == (r["expect"] == "exists") and (not r["ranked"] or r["rank"] == 1)
            rank = "—" if not r["ranked"] else (r["rank"] or ">10")
            print(f"  {'✓' if ok else '✗'} {r['id']:22} expect={r['expect']:6} state={r['state']:9} rank={rank!s:4} {r['query'][:60]}")
    print()
    if fails:
        print("THRESHOLDS BROKEN:")
        for f in fails:
            print("  -", f)
        return 1
    print("All thresholds hold.")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    sys.exit(main())
