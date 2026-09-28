"""Smoke evaluation for v0: a small, hand-picked set of texts.

This is the seed of the real test set (100 cases reviewed by a Sharia
specialist) that is built before the challenge. Run:

    python evaluation/run_eval.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sanad_core import engine  # noqa: E402

with open(os.path.join(ROOT, "evaluation", "smoke_cases.json"), encoding="utf-8") as fh:
    CASES = json.load(fh)

ok = 0
wrong_found = 0
for c in CASES:
    r = engine.search(c["text"], mode="verify")
    exists = r["state"] in ("found", "near")
    good = exists == c["exists"]
    ok += good
    if exists and not c["exists"]:
        wrong_found += 1
    print(("✓" if good else "✗"), r["state"].ljust(9), c["text"])

n = len(CASES)
print(f"\ncorrect: {ok}/{n} ({ok / n:.0%})")
print(f"said 'exists' for a text that is not in the six books: {wrong_found}")
