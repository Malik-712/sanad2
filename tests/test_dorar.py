"""Dorar layer tests. Offline: never contacts dorar.net (live fetching off).

    python -m unittest discover -s tests -v
"""
import json
import os
import sys
import unittest

os.environ["SANAD_DORAR_LIVE"] = "0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "api"))
from sanad_core import dorar, engine  # noqa: E402
import sanad as api  # noqa: E402

PROV_KEYS = {"source", "url", "quote", "retrieved", "method", "confidence"}
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "dorar_api_sample.json")


class Parse(unittest.TestCase):
    def test_parses_every_field_verbatim(self):
        with open(FIXTURE, encoding="utf-8") as fh:
            res = dorar.parse(json.load(fh)["ahadith"]["result"])
        self.assertEqual(len(res), 2)
        first = res[0]
        self.assertEqual(set(first), {"text", "rawi", "muhaddith", "book", "ref", "verdict"})
        self.assertEqual(first["muhaddith"], "الألباني")
        self.assertEqual(first["book"], "صحيح الترغيب")
        self.assertEqual(first["verdict"], "صحيح")
        self.assertFalse(first["text"][0].isdigit())   # the "1 - " counter is removed

    def test_empty_or_garbage(self):
        self.assertEqual(dorar.parse(""), [])
        self.assertEqual(dorar.parse("<div>nothing</div>"), [])


class Attribution(unittest.TestCase):
    def test_bukhari_1_same_source(self):
        g = dorar.grades_for("bukhari-1", live=False)
        self.assertEqual(g["status"], "ok")
        own = [i for i in g["items"] if i["match"] == "same_source"]
        self.assertTrue(own)
        i = own[0]
        self.assertEqual((i["muhaddith"], i["book"], i["ref"]), ("البخاري", "صحيح البخاري", "1"))
        self.assertTrue(PROV_KEYS <= set(i["prov"]))
        self.assertIn(i["verdict"], i["prov"]["quote"])            # the quote contains the verdict verbatim
        self.assertIn("dorar.net", i["prov"]["url"])

    def test_every_item_has_provenance_and_known_confidence(self):
        for hid in ("bukhari-1", "bukhari-134", "muslim-4414"):
            g = dorar.grades_for(hid, live=False)
            for i in g["items"]:
                self.assertTrue(PROV_KEYS <= set(i["prov"]))
                self.assertIn(i["prov"]["confidence"], ("high", "uncertain"))
                if i["match"] == "candidate":
                    self.assertEqual(i["prov"]["confidence"], "uncertain")

    def test_uncached_is_not_fetched_offline(self):
        g = dorar.grades_for("ibnmajah-4000", live=False)
        self.assertIn(g["status"], ("not_fetched", "ok", "no_match", "no_text"))
        if g["status"] == "not_fetched":
            self.assertEqual(g["items"], [])

    def test_short_excerpt_is_not_high_confidence(self):
        h = engine.hadith_record("bukhari-1")
        fake = [{"text": "انما الاعمال بالنيات", "muhaddith": "x", "book": "y", "ref": "1", "verdict": "z"}]
        items = dorar.match(h, fake, "q", "2026-09-28")
        self.assertTrue(all(i["prov"]["confidence"] == "uncertain" for i in items))

    def test_api_route(self):
        status, body = api.route({"action": "grades", "id": "bukhari-1"})
        self.assertEqual(status, 200)
        self.assertEqual(api.route({"action": "grades", "id": "../x"})[0], 400)


class Policy(unittest.TestCase):
    def test_client_identifies_itself_and_waits(self):
        self.assertTrue(dorar.USER_AGENT.startswith("Sanad/"))
        self.assertNotIn("Mozilla", dorar.USER_AGENT)
        self.assertGreaterEqual(dorar.MIN_INTERVAL, 2)
        self.assertTrue(dorar.API.startswith("https://dorar.net/dorar_api.json"))


if __name__ == "__main__":
    unittest.main()
