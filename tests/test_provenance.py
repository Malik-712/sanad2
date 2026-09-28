"""The provenance report stays in sync with the source catalog, and covers
every provenance-carrying field the API returns."""
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "api"))
import sanad as api  # noqa: E402
from sanad_core.sources import catalog  # noqa: E402


class Report(unittest.TestCase):
    def test_doc_is_generated_from_catalog(self):
        path = os.path.join(ROOT, "docs", "PROVENANCE.md")
        with open(path, encoding="utf-8") as fh:
            before = fh.read()
        subprocess.run([sys.executable, os.path.join(ROOT, "pipeline", "gen_provenance.py")], check=True,
                       capture_output=True)
        with open(path, encoding="utf-8") as fh:
            self.assertEqual(before, fh.read(), "docs/PROVENANCE.md is stale: run pipeline/gen_provenance.py")

    def test_every_source_is_complete(self):
        for s in catalog()["sources"]:
            for k in ("name", "url", "status", "taken", "how", "retrieved", "license"):
                self.assertTrue(s.get(k), f"{s['id']}: {k}")

    def test_fields_cover_api_provenance_keys(self):
        _, h = api.route({"action": "hadith", "id": "bukhari-1"})
        documented = " ".join(f[3] for f in catalog()["fields"])
        for key in [k for k in h if k.endswith("_prov")]:
            self.assertIn(key, documented)

    def test_sources_action(self):
        status, body = api.route({"action": "sources"})
        self.assertEqual(status, 200)
        self.assertIn("dorar-tarajem", [s["id"] for s in body["sources"]])


if __name__ == "__main__":
    unittest.main()
