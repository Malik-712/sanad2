"""Tests for evaluation/review_sheet.py (export, import rules, CSV round trip).

No query or label is written here: every text comes from evaluation/cases.json
or the corpus at run time. Nothing is written to the repository.
"""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "evaluation"))
os.environ.setdefault("SANAD_DORAR_LIVE", "0")
import harness  # noqa: E402
import review_sheet as rs  # noqa: E402
from corpus_check import Corpus  # noqa: E402

TODAY = "2026-10-04"


class ReviewSheet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = harness.load_cases()
        cls.corpus = Corpus()
        cls.exact = next(c for c in cls.cases if c["category"] == "exact" and c["status"] == "auto")
        cls.v0_absent = next(c for c in cls.cases if c["category"] == "not_in_six_books"
                             and c["origin"]["kind"] == "v0_smoke")

    def row(self, **kw):
        r = {k: "" for k in rs.COLUMNS}
        r.update(kw)
        return r

    def apply(self, *rows):
        return rs.apply_rows(self.cases, list(rows), self.corpus, today=TODAY)

    def test_export_round_trip_changes_nothing(self):
        rows = rs.export_rows(self.cases, self.corpus)
        self.assertEqual([r["id"] for r in rows], [c["id"] for c in self.cases])
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "sheet.csv")
            rs.write_sheet(path, rows)
            with open(path, "rb") as fh:
                self.assertEqual(fh.read(3), b"\xef\xbb\xbf", "UTF-8 BOM for Excel")
            back = rs.read_sheet(path)
        self.assertEqual([r["query"] for r in back], [c["query"] for c in self.cases])
        new, s = self.apply(*back)
        self.assertEqual(new, self.cases)
        self.assertEqual(s["accepted"], 0)

    def test_new_human_row_is_added_as_reviewed_test_case(self):
        # Reuses an existing query and its records only to exercise the tool.
        src = self.exact
        new, s = self.apply(self.row(category="meaning", query=src["query"],
                                     relevant=" ".join(src["relevant"]), basis="tool test", decision="accept"))
        self.assertEqual((s["accepted"], s["added"]), (1, 1))
        c = new[-1]
        self.assertTrue(c["id"].startswith("human-meaning-"))
        self.assertEqual((c["status"], c["split"], c["expect"]), ("reviewed", "test", "exists"))
        self.assertEqual(c["origin"], {"kind": "human", "author": rs.DEFAULT_REVIEWER, "added": TODAY})
        self.assertEqual(c["review"]["reviewer"], "Malik (author)")
        self.assertEqual(c["review"]["date"], TODAY)
        self.assertEqual(c["review"]["scope"], harness.REVIEW_SCOPE)
        self.assertEqual([e["id"] for e in c["evidence"]], c["relevant"])
        for e in c["evidence"]:
            self.assertIn(e["quote"], self.corpus.by_id[e["id"]]["matn"])
        # Importing the same row again updates the case instead of adding one.
        again, s2 = rs.apply_rows(new, [self.row(category="meaning", query=src["query"],
                                                 relevant=" ".join(src["relevant"]), basis="tool test 2",
                                                 decision="accept")], self.corpus, today=TODAY)
        self.assertEqual((len(again), s2["added"]), (len(new), 0))

    def test_absent_alias_and_word_for_word_guard(self):
        with self.assertRaisesRegex(rs.SheetError, "contain the words in order"):
            self.apply(self.row(category="absent", query=self.exact["query"], basis="x", decision="accept"))

    def test_rules(self):
        q = self.exact["query"]
        bad = [
            (self.row(category="meaning", query=q, relevant=self.exact["relevant"][0], decision="accept"), "basis"),
            (self.row(category="meaning", query=q, basis="x", decision="accept"), "at least one record"),
            (self.row(category="meaning", query=q, relevant="nosuch-1", basis="x", decision="accept"), "unknown"),
            (self.row(category="nonsense", query=q, basis="x", decision="accept"), "category"),
            (self.row(category="meaning", query=q, relevant=self.exact["relevant"][0], expect="absent",
                      basis="x", decision="accept"), "does not fit"),
            (self.row(id=self.v0_absent["id"], category="not_in_six_books", query=self.v0_absent["query"],
                      split="test", basis="x", decision="accept"), "stay in dev"),
            (self.row(id=self.exact["id"], decision="remove"), "only cases you added"),
            (self.row(id=self.exact["id"], category="exact", query=q, relevant="", basis="x",
                      decision="accept"), "at least one record"),
            (self.row(category="meaning", query=q, relevant=self.exact["relevant"][0], basis="x",
                      date="04/10/2026", decision="accept"), "YYYY-MM-DD"),
            (self.row(decision="maybe"), "decision"),
        ]
        for r, msg in bad:
            with self.subTest(msg=msg), self.assertRaisesRegex(rs.SheetError, msg):
                self.apply(r)

    def test_one_bad_row_blocks_the_whole_import(self):
        good = self.row(id=self.v0_absent["id"], category="not_in_six_books", query=self.v0_absent["query"],
                        basis="x", decision="accept")
        bad = self.row(category="meaning", query=self.exact["query"], basis="x", decision="accept")
        with self.assertRaises(rs.SheetError):
            self.apply(good, bad)

    def test_existing_case_accepted_keeps_dev_split(self):
        c = self.v0_absent
        new, _ = self.apply(self.row(id=c["id"], category="not_in_six_books", query=c["query"],
                                     basis="x", decision="accept"))
        got = next(x for x in new if x["id"] == c["id"])
        self.assertEqual((got["status"], got["split"], got["relevant"]), ("reviewed", "dev", []))
        self.assertNotIn("check", got)

    def test_fill_lists_candidates_for_new_rows_only(self):
        rows = [self.row(query=self.exact["query"]), self.row(id=self.exact["id"], query=self.exact["query"])]
        self.assertEqual(rs.fill_rows(rows, self.corpus), 1)
        self.assertIn(self.exact["relevant"][0], rows[0]["candidates"])
        self.assertEqual(rows[1]["candidates"], "")


if __name__ == "__main__":
    unittest.main()
