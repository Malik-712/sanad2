"""Single serverless entry point for Sanad's API (Vercel Python runtime).

GET /api/sanad?action=search&q=...&mode=auto|verify|topic&book=...
GET /api/sanad?action=hadith&id=bukhari-1
GET /api/sanad?action=tree&id=bukhari-1
GET /api/sanad?action=diff&id=bukhari-1&q=...
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from sanad_core import engine  # noqa: E402

MAX_QUERY = 1500


def route(params):
    action = params.get("action", "")
    if action == "search":
        q = params.get("q", "")[:MAX_QUERY]
        mode = params.get("mode", "auto")
        if mode not in ("auto", "verify", "topic"):
            mode = "auto"
        book = params.get("book") or None
        return 200, engine.search(q, limit=10, book=book, mode=mode)
    if action == "hadith":
        h = engine.hadith(params.get("id", ""))
        return (200, h) if h else (404, {"error": "لم نجد هذا الحديث في بيانات سند."})
    if action == "tree":
        t = engine.tree(params.get("id", ""))
        return (200, t) if t else (404, {"error": "لم نجد هذا الحديث في بيانات سند."})
    if action == "diff":
        h = engine.hadith(params.get("id", ""))
        if not h:
            return 404, {"error": "لم نجد هذا الحديث في بيانات سند."}
        return 200, {"diff": engine.word_diff(params.get("q", "")[:MAX_QUERY], h["matn"], focus=True)}
    if action == "health":
        d = engine.data()
        return 200, {"ok": True, "hadiths": len(d["hadiths"])}
    return 400, {"error": "طلب غير معروف."}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
        try:
            status, body = route(params)
        except Exception as exc:  # never leak a stack trace to the page
            status, body = 500, {"error": "حدث خطأ في الخادم.", "detail": type(exc).__name__}
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=300, s-maxage=86400")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass
