"""Search regression tests over evaluation/cases.json.

    python -m pytest tests/test_eval.py       (or: python -m unittest tests.test_eval)

Two groups:
- CaseFile: the case file is well formed and every expected record really
  contains the query's words (re-checked from the corpus, not trusted).
- Regression: no false "exists", and every floor in evaluation/thresholds.json.
"""
import glob
import gzip
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
            self.assertIn(c.get("split"), harness.SPLITS, c["id"])
            self.assertTrue(c["query"].strip(), c["id"])

    def test_every_built_category_has_cases(self):
        """Built categories are always there; meaning and conflict cases are
        written by a person and may still be missing."""
        present = {c["category"] for c in self.cases}
        self.assertLessEqual(set(harness.BUILT_CATEGORIES), present)

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
                self.assertTrue(c.get("review", {}).get("basis"), c["id"])

    def test_reviewed_labels_fit_the_corpus(self):
        """A reviewed "exists" names real records; a reviewed "absent" text is
        not in any record word for word (mechanical check, not a judgment)."""
        for c in self.cases:
            if c["status"] != "reviewed":
                continue
            if c["expect"] == "exists":
                self.assertTrue(c["relevant"], c["id"])
                for hid in c["relevant"]:
                    self.assertIn(hid, self.corpus.by_id, c["id"])
            else:
                self.assertEqual(self.corpus.containing(words(c["query"])), [], c["id"])

    def test_test_split_is_reviewed_and_held_out(self):
        for c in self.cases:
            if c.get("split") != "test":
                continue
            self.assertEqual(c["status"], "reviewed", c["id"])
            self.assertTrue(c["review"].get("reviewer") and c["review"].get("date"), c["id"])
            self.assertNotEqual(c["origin"].get("kind"), "v0_smoke",
                                f"{c['id']}: v0 cases set the thresholds and must stay in dev")

    def test_human_cases_name_their_author(self):
        for c in self.cases:
            if c["origin"].get("kind") == "human":
                self.assertTrue(c["origin"].get("author"), c["id"])
                self.assertTrue(c["id"].startswith("human-"), c["id"])

    def test_review_never_claims_a_specialist(self):
        """Solo project: labels are checked by the author against the source
        text; no case may say it was reviewed by a Sharia specialist."""
        for c in self.cases:
            if c["status"] == "reviewed":
                self.assertEqual(c["review"].get("scope"), harness.REVIEW_SCOPE, c["id"])

    def test_no_test_case_in_training_files(self):
        test = [c for c in self.cases if c.get("split") == "test"]
        keys = {c["id"] for c in test} | {hid for c in test for hid in c["relevant"]}
        for pattern in harness.TRAINING_FILE_GLOBS:
            for path in glob.glob(os.path.join(ROOT, pattern)):
                opener = gzip.open if path.endswith(".gz") else open
                with opener(path, "rt", encoding="utf-8") as fh:
                    text = fh.read()
                leaked = sorted(k for k in keys if f'"{k}"' in text)
                self.assertEqual(leaked, [], f"{path} holds held-out test cases or their records")


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
