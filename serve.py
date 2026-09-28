"""Local development server: serves public/ and the API on http://localhost:8000"""
import os
import sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "api"))

import sanad as api  # noqa: E402


class Dev(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=os.path.join(ROOT, "public"), **kw)

    def do_GET(self):
        if self.path.startswith("/api/sanad"):
            return api.handler.do_GET(self)
        return super().do_GET()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    api.engine.data()
    print(f"Sanad running on http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Dev).serve_forever()
