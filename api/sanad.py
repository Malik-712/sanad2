"""Single serverless entry point for Sanad's API (Vercel Python runtime).

GET /api/sanad?action=search&q=...&mode=auto|verify|topic&book=...
GET /api/sanad?action=hadith&id=bukhari-1
GET /api/sanad?action=tree&id=bukhari-1
GET /api/sanad?action=diff&id=bukhari-1&q=...
GET /api/sanad?action=compare&a=bukhari-1&b=muslim-4927   (wording of two narrations)
GET /api/sanad?action=grades&id=bukhari-1      (Dorar attributions, official API, cached)
GET /api/sanad?action=sources                  (every data source, for /about/sources)
GET /api/sanad?action=health
"""
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from sanad_core import engine  # noqa: E402

MAX_QUERY = engine.MAX_QUERY_CHARS
MAX_URL = 8000
ID_RE = re.compile(r"^[a-z]{3,10}-\d{1,5}(?:-\d{1,2})?$")
BOOKS = {"bukhari", "muslim", "abudawud", "tirmidhi", "nasai", "ibnmajah"}
NOT_FOUND = "لم نجد هذا الحديث في بيانات سند."

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
}


def _id(params):
    hid = params.get("id", "")
    return hid if ID_RE.match(hid) else None


def route(params):
    action = params.get("action", "")
    if action == "search":
        q = params.get("q", "")[:MAX_QUERY]
        mode = params.get("mode", "auto")
        if mode not in ("auto", "verify", "topic"):
            mode = "auto"
        book = params.get("book") or None
        if book and book not in BOOKS:
            return 400, {"error": "اسم الكتاب غير معروف."}
        return 200, engine.search(q, limit=10, book=book, mode=mode)
    if action in ("hadith", "tree", "diff", "grades"):
        hid = _id(params)
        if not hid:
            return 400, {"error": "رقم الحديث غير صالح."}
        if action == "hadith":
            h = engine.hadith(hid)
            return (200, h) if h else (404, {"error": NOT_FOUND})
        if action == "tree":
            t = engine.tree(hid)
            return (200, t) if t else (404, {"error": NOT_FOUND})
        if action == "grades":
            from sanad_core import dorar
            g = dorar.grades_for(hid)
            return (200, g) if g is not None else (404, {"error": NOT_FOUND})
        if action == "diff":
            h = engine.hadith(hid)
            if not h:
                return 404, {"error": NOT_FOUND}
            return 200, {"diff": engine.word_diff(params.get("q", "")[:MAX_QUERY], h["matn"], focus=True)}
    if action == "compare":
        a, b = _id({"id": params.get("a", "")}), _id({"id": params.get("b", "")})
        if not a or not b:
            return 400, {"error": "رقم الحديث غير صالح."}
        ha, hb = engine.hadith_record(a), engine.hadith_record(b)
        if not ha or not hb:
            return 404, {"error": NOT_FOUND}
        return 200, {"a": engine.card(ha), "b": engine.card(hb), "diff": engine.compare_matn(ha["matn"], hb["matn"])}
    if action == "sources":
        from sanad_core import sources
        return 200, sources.catalog()
    if action == "health":
        d = engine.data()
        return 200, {"ok": True, "hadiths": len(d["hadiths"])}
    return 400, {"error": "طلب غير معروف."}


def respond(req, status, body, cache=True):
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req.send_response(status)
    req.send_header("Content-Type", "application/json; charset=utf-8")
    req.send_header("Content-Length", str(len(payload)))
    # errors must not be cached by the CDN
    req.send_header("Cache-Control", "public, max-age=300, s-maxage=86400" if cache and status == 200 else "no-store")
    for k, v in SECURITY_HEADERS.items():
        req.send_header(k, v)
    req.end_headers()
    req.wfile.write(payload)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if len(self.path) > MAX_URL:
            return respond(self, 414, {"error": "الطلب أطول من المسموح."})
        try:
            params = {k: v[0] for k, v in parse_qs(urlparse(self.path).query, max_num_fields=20).items()}
        except ValueError:
            return respond(self, 400, {"error": "طلب غير صالح."})
        try:
            status, body = route(params)
        except Exception as exc:  # never leak a stack trace to the page
            status, body = 500, {"error": "حدث خطأ في الخادم.", "detail": type(exc).__name__}
        # a "grades" answer can change once Dorar has been queried: cache briefly
        respond(self, status, body, cache=not (params.get("action") == "grades" and body.get("status") != "ok"))

    def log_message(self, *args):
        pass
