"""API tests: input validation, limits, error handling, provenance shape.

    python -m unittest discover -s tests -v
"""
import json
import os
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "api"))
import sanad as api  # noqa: E402
from sanad_core import engine  # noqa: E402

PROV_KEYS = {"source", "url", "quote", "retrieved", "method"}


class Validation(unittest.TestCase):
    def test_unknown_action(self):
        self.assertEqual(api.route({"action": "nope"})[0], 400)

    def test_bad_ids_rejected(self):
        for bad in ["", "../etc/passwd", "bukhari-1<script>", "x" * 500, "bukhari-", "BUKHARI-1"]:
            self.assertEqual(api.route({"action": "hadith", "id": bad})[0], 400, bad)
            self.assertEqual(api.route({"action": "tree", "id": bad})[0], 400, bad)

    def test_missing_hadith_is_404(self):
        self.assertEqual(api.route({"action": "hadith", "id": "bukhari-99999"})[0], 404)

    def test_unknown_book_rejected(self):
        self.assertEqual(api.route({"action": "search", "q": "الدين النصيحة", "book": "x"})[0], 400)

    def test_bad_mode_falls_back(self):
        status, body = api.route({"action": "search", "q": "الدين النصيحة", "mode": "evil"})
        self.assertEqual(status, 200)
        self.assertIn(body["mode"], ("verify", "topic"))

    def test_markup_in_query_is_returned_as_data(self):
        status, body = api.route({"action": "search", "q": "<img src=x onerror=alert(1)>", "mode": "verify"})
        self.assertEqual(status, 200)
        self.assertEqual(body["state"], "empty")


class Limits(unittest.TestCase):
    def test_long_query_is_fast(self):
        h = engine.data()["hadiths"][engine.data()["by_id"]["bukhari-1"]]
        q = ((h["matn"] + " ") * 10)[:5000]
        t = time.time()
        status, _ = api.route({"action": "search", "q": q, "mode": "verify"})
        self.assertEqual(status, 200)
        self.assertLess(time.time() - t, 3.0)

    def test_empty_query(self):
        status, body = api.route({"action": "search", "q": ""})
        self.assertEqual(status, 200)
        self.assertEqual(body["state"], "empty")


class Modes(unittest.TestCase):
    def test_hadith_starting_with_ma_is_verified_not_topic(self):
        self.assertEqual(engine.detect_mode("ما من مسلم يغرس غرسا"), "verify")

    def test_topic_prefix(self):
        self.assertEqual(engine.detect_mode("ابحث عن فضل الصبر"), "topic")


class Provenance(unittest.TestCase):
    def test_hadith_fields_carry_provenance(self):
        _, h = api.route({"action": "hadith", "id": "bukhari-1"})
        for key in ("matn_prov", "isnad_prov", "source_prov"):
            self.assertTrue(PROV_KEYS <= set(h[key]), key)
        for r in h["routes"]:
            for n in r["names"]:
                self.assertTrue(PROV_KEYS <= set(n["prov"]))
                self.assertIn(n["prov"]["confidence"], ("high", "uncertain"))
                self.assertTrue(n["prov"]["quote"])

    def test_unattributed_grade_is_marked(self):
        d = engine.data()
        h = next(x for x in d["hadiths"] if x["grade"])
        _, body = api.route({"action": "hadith", "id": h["id"]})
        self.assertIs(body["grade_prov"]["attributed"], False)
        self.assertEqual(body["grade_prov"]["quote"], h["grade"])

    def test_source_url_points_to_csv_file(self):
        _, h = api.route({"action": "hadith", "id": "muslim-4414"})
        self.assertRegex(h["matn_prov"]["url"], r"/blob/master/Muslim/Chapter\d+\.csv$")


class Tree(unittest.TestCase):
    def test_bukhari_1_tree(self):
        _, t = api.route({"action": "tree", "id": "bukhari-1"})
        nodes = {n["key"]: n for n in t["nodes"]}
        self.assertEqual(nodes[t["mudar"]]["label"], "يحيي بن سعيد الانصاري")
        self.assertEqual(t["summary"]["companion_names"], ["عمر بن الخطاب"])
        json.dumps(t, ensure_ascii=False)  # serializable

    def test_tahwil_routes_all_drawn(self):
        _, t = api.route({"action": "tree", "id": "muslim-4414"})
        own = [c for c in t["chains"] if c["hid"] == "muslim-4414"]
        self.assertEqual(len(own), 6)


if __name__ == "__main__":
    unittest.main()
