"""Search regression tests over evaluation/cases.json.

    python -m pytest tests/test_eval.py       (or: python -m unittest tests.test_eval)

Two groups:
- CaseFile: the case file is well formed and every expected record really
  contains the query's words (re-checked from the corpus, not trusted).
- Regression: no false "exists", and every floor in evaluation/thresholds.json.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "evaluation"))
os.environ.setdefault("SANAD_DORAR_LIVE", "0")
import harness  # noqa: E402
from corpus_check import Corpus, words  # noqa: E402

PROV_KEYS = {"source", "url", "quote", "retrieved", "method"}
STATUSES = {"auto", "needs_review", "reviewed"}
REQUIRED = {"id", "category", "query", "expect", "status", "relevant", "evidence", "origin"}

_report = {}


def report():
    if not _report:
        _report.update(harness.evaluate())
    return _report


class CaseFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = harness.load_cases()
        cls.corpus = Corpus()

    def test_fields_and_values(self):
        ids = set()
        for c in self.cases:
            self.assertTrue(REQUIRED <= set(c), c.get("id"))
            self.assertNotIn(c["id"], ids, "duplicate id")
            ids.add(c["id"])
            self.assertIn(c["category"], harness.CATEGORIES, c["id"])
            self.assertIn(c["expect"], ("exists", "absent"), c["id"])
            self.assertIn(c["status"], STATUSES, c["id"])
            self.assertTrue(c["query"].strip(), c["id"])

    def test_every_category_has_cases(self):
        present = {c["category"] for c in self.cases}
        self.assertEqual(present, set(harness.CATEGORIES))

    def test_absent_cases_have_no_expected_records(self):
        for c in self.cases:
            if c["expect"] == "absent":
                self.assertEqual(c["relevant"], [], c["id"])

    def test_needs_review_is_never_ranked(self):
        for c in self.cases:
            if c["status"] == "needs_review":
                self.assertEqual(c["relevant"], [], c["id"])
                self.assertIn("review", c, c["id"])

    def test_evidence_is_complete_provenance(self):
        for c in self.cases:
            self.assertEqual([e["id"] for e in c["evidence"]], c["relevant"], c["id"])
            for e in c["evidence"]:
                self.assertTrue(PROV_KEYS <= set(e), c["id"])
                for k in PROV_KEYS:
                    self.assertTrue(str(e[k]).strip(), f"{c['id']} {k}")

    def test_expected_records_exist_and_contain_the_words(self):
        """For auto cases the expected records must still contain the query
        word for word, and must be all such records (nothing picked by hand)."""
        for c in self.cases:
            if c["status"] != "auto" or c["expect"] != "exists":
                continue
            qw = words(c.get("clean_query") or c["query"])
            for hid in c["relevant"]:
                self.assertIn(hid, self.corpus.by_id, c["id"])
                self.assertIsNotNone(self.corpus.span(hid, qw), f"{c['id']}: {hid} does not contain the query")
            self.assertEqual(sorted(c["relevant"]), sorted(self.corpus.containing(qw)), c["id"])

    def test_evidence_quotes_are_verbatim(self):
        for c in self.cases:
            for e in c["evidence"]:
                self.assertIn(e["quote"], self.corpus.by_id[e["id"]]["matn"], c["id"])

    def test_reviewed_cases_name_a_reviewer(self):
        for c in self.cases:
            if c["status"] == "reviewed":
                self.assertTrue(c.get("review", {}).get("reviewer"), c["id"])
                self.assertTrue(c.get("review", {}).get("date"), c["id"])


class Regression(unittest.TestCase):
    def test_no_false_exists(self):
        """Hard requirement: a text labelled absent is never reported as existing."""
        bad = [r["id"] for r in report()["results"] if r["expect"] == "absent" and r["said_exists"]]
        self.assertEqual(bad, [])

    def test_absent_cases_are_present(self):
        self.assertGreater(report()["overall"]["absent_cases"], 0)

    def test_floors(self):
        fails = harness.check_thresholds(report())
        self.assertEqual(fails, [], "\n".join(fails))


if __name__ == "__main__":
    unittest.main()
