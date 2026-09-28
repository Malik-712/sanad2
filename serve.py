"""Local development server: serves public/ and the API on http://127.0.0.1:8000

Binds to localhost by default; set HOST=0.0.0.0 to expose it on your network.
"""
import os
import sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "api"))

import sanad as api  # noqa: E402

# the same headers vercel.json sets in production
STATIC_HEADERS = {
    **api.SECURITY_HEADERS,
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"),
}


class Dev(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=os.path.join(ROOT, "public"), **kw)

    def do_GET(self):
        if self.path.startswith("/api/sanad"):
            return api.handler.do_GET(self)
        # client-side routes (/about/sources, /h/...) fall back to the app shell
        path = self.path.split("?")[0].split("#")[0]
        if not os.path.splitext(path)[1] and path != "/":
            self.path = "/index.html"
        return super().do_GET()

    def end_headers(self):
        if not self.path.startswith("/api/"):
            for k, v in STATIC_HEADERS.items():
                self.send_header(k, v)
        super().end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    api.engine.data()
    print(f"Sanad running on http://{host}:{port}")
    ThreadingHTTPServer((host, port), Dev).serve_forever()
