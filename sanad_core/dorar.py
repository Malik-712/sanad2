"""Grade attributions from الدرر السنية (dorar.net), via its official API only.

Access policy (checked 2026-09-28, see docs/PROVENANCE.md):
- Dorar publishes `https://dorar.net/dorar_api.json?skey=...` for sites that
  want to show results of its hadith encyclopedia (article 389). robots.txt
  allows all paths. That API is the only Dorar channel Sanad uses.
- Narrator biographies have no API; their pages are "all rights reserved"
  and behind Cloudflare bot management. Sanad does not fetch them.

What is taken: for each result, exactly the fields the API returns
(الراوي، المحدث، المصدر، الصفحة أو الرقم، خلاصة حكم المحدث) and the result's
text, verbatim. Nothing is paraphrased: a verdict is shown as the quote the
API gave, attributed to the scholar and book the API named.

Every request: identifies Sanad in the User-Agent, times out, and waits at
least MIN_INTERVAL seconds after the previous one (process-wide lock).
Results are cached with their retrieval date so each query is fetched once.
"""
import datetime
import difflib
import gzip
import html
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request

from . import engine
from .arabic import normalize

API = "https://dorar.net/dorar_api.json"
SEARCH_PAGE = "https://dorar.net/hadith/search"   # human-checkable page for the same query
USER_AGENT = "Sanad/1.0 (hadith verification tool; AI Serving Islamic Content challenge 2026)"
MIN_INTERVAL = 2.5      # seconds between two requests to dorar.net
TIMEOUT = 15
SOURCE_NAME = "الدرر السنية — الموسوعة الحديثية (واجهة API الرسمية)"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILT_CACHE = os.path.join(ROOT, "data", "dorar_grades.json.gz")      # committed, built by pipeline
RUNTIME_CACHE = os.environ.get("SANAD_DORAR_CACHE",
                               os.path.join(ROOT, "data", "dorar_runtime_cache.json"))  # git-ignored
LIVE = os.environ.get("SANAD_DORAR_LIVE", "1") != "0"

# how our book titles appear as Dorar's "المصدر" for the compiler's own entry
BOOK_SOURCE = {
    "bukhari": ("صحيح البخاري",), "muslim": ("صحيح مسلم",), "abudawud": ("سنن أبي داود",),
    "tirmidhi": ("سنن الترمذي", "جامع الترمذي"), "nasai": ("سنن النسائي", "المجتبى"),
    "ibnmajah": ("سنن ابن ماجه",),
}
T_SAME_TEXT = 0.80      # word similarity for "the same wording"
T_CANDIDATE = 0.60      # below this a result is ignored; between: shown as غير مؤكد

_lock = threading.Lock()
_last = [0.0]
_mem = {}


# ------------------------------------------------------------------ fetching
def _query_for(matn):
    """A search key from the start of the matn: plain letters, up to 9 words."""
    words = normalize(matn).split()
    return " ".join(words[:9])


def fetch(skey):
    """One rate-limited request to the official API. Returns the raw 'result' HTML."""
    url = f"{API}?{urllib.parse.urlencode({'skey': skey})}"
    with _lock:
        wait = _last[0] + MIN_INTERVAL - time.time()
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                body = r.read(2_000_000).decode("utf-8", "replace")
        finally:
            _last[0] = time.time()
    data = json.loads(body)
    return (data.get("ahadith") or {}).get("result", "") if isinstance(data, dict) else ""


_BLOCK = re.compile(r'<div class="hadith"[^>]*>(.*?)</div>\s*<div class="hadith-info">(.*?)</div>', re.S)
_FIELD = re.compile(r'<span class="info-subtitle">\s*([^<:]+?)\s*:\s*</span>(.*?)(?=<span class="info-subtitle">|$)', re.S)
FIELD_KEYS = {"الراوي": "rawi", "المحدث": "muhaddith", "المصدر": "book", "الصفحة أو الرقم": "ref",
              "خلاصة حكم المحدث": "verdict"}


def _text(frag):
    t = html.unescape(re.sub(r"<[^>]+>", "", frag))
    return re.sub(r"\s+", " ", t).strip()


def parse(result_html):
    """The API's HTML -> [{text, rawi, muhaddith, book, ref, verdict}], verbatim."""
    out = []
    for body, info in _BLOCK.findall(result_html or ""):
        text = re.sub(r"^\s*\d+\s*-\s*", "", _text(body))
        rec = {"text": text}
        for label, value in _FIELD.findall(info):
            key = FIELD_KEYS.get(label.strip())
            if key:
                rec[key] = _text(value)
        out.append(rec)
    return out


# ------------------------------------------------------------------ matching
def _words(t):
    return [w for w in normalize(t).split() if w]


def text_similarity(a, b):
    """Share of the shorter text's words found, in order, in the longer one."""
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return 0.0
    sm = difflib.SequenceMatcher(a=wa, b=wb, autojunk=False)
    same = sum(m.size for m in sm.get_matching_blocks())
    return round(same / min(len(wa), len(wb)), 3)


def _num(s):
    m = re.search(r"\d+", s or "")
    return m.group(0) if m else ""


def match(h, results, skey, retrieved):
    """Attributions for hadith h among Dorar results. Never picks one when unsure:
    an uncertain match is returned with confidence "uncertain" and its numbers."""
    own_books = {normalize(b) for b in BOOK_SOURCE.get(h["book"], ())}
    items = []
    for r in results:
        if not r.get("verdict") or not r.get("muhaddith"):
            continue
        sim = text_similarity(h["matn"], r["text"])
        if sim < T_CANDIDATE:
            continue
        same_book = normalize(r.get("book", "")) in own_books
        same_num = same_book and _num(r.get("ref")) == str(h["number"])
        if same_num and sim >= T_CANDIDATE:
            kind, conf = "same_source", "high"
            how = (f"نتيجة من واجهة الدرر الرسمية مصدرها {r.get('book')} برقم {r.get('ref')}، "
                   f"وهو كتاب هذا الحديث ورقمه، وتشابه النصين {round(sim * 100)}%.")
        elif sim >= T_SAME_TEXT:
            # a short excerpt contained in a long text is not "the same wording"
            la, lb = len(_words(h["matn"])), len(_words(r["text"]))
            comparable = min(la, lb) / max(la, lb) >= 0.5
            kind, conf = "same_text", "high" if comparable and not same_book else "uncertain"
            how = (f"نتيجة من واجهة الدرر الرسمية لفظها قريب من لفظ هذا الحديث (تشابه الكلمات {round(sim * 100)}%). "
                   "الحكم لقائله على روايته في كتابه المذكور، ونسبته إلى هذه الرواية بتشابه اللفظ.")
            if same_book:
                how += " الكتاب نفسه لكن الرقم مختلف، فقد تختلف الطبعة: المطابقة غير مؤكدة."
            if not comparable:
                how += " أحد النصين أطول من الآخر بكثير، فقد يكون الحكم على جزء من الحديث: المطابقة غير مؤكدة."
        else:
            kind, conf = "candidate", "uncertain"
            how = f"نتيجة مرشحة: تشابه اللفظ {round(sim * 100)}% فقط، فالمطابقة غير مؤكدة."
        quote = " | ".join(f"{lab}: {r[k]}" for lab, k in (("الراوي", "rawi"), ("المحدث", "muhaddith"), ("المصدر", "book"),
                                                          ("الصفحة أو الرقم", "ref"), ("خلاصة حكم المحدث", "verdict")) if r.get(k))
        items.append({
            "muhaddith": r["muhaddith"], "book": r.get("book", ""), "ref": r.get("ref", ""), "verdict": r["verdict"],
            "rawi": r.get("rawi", ""), "text": r["text"][:300], "similarity": sim, "match": kind,
            "prov": {"source": SOURCE_NAME, "url": f"{SEARCH_PAGE}?{urllib.parse.urlencode({'q': skey})}",
                     "quote": quote, "retrieved": retrieved, "method": how + f" طلب الواجهة: skey=«{skey}».",
                     "confidence": conf, "score": sim},
        })
    order = {"same_source": 0, "same_text": 1, "candidate": 2}
    items.sort(key=lambda x: (order[x["match"]], -x["similarity"]))
    return items[:12]


# ------------------------------------------------------------------ cache
def _load_built():
    if "built" not in _mem:
        try:
            with gzip.open(BUILT_CACHE, "rt", encoding="utf-8") as fh:
                _mem["built"] = json.load(fh)
        except (OSError, ValueError):
            _mem["built"] = {"queries": {}}
    return _mem["built"]


def _load_runtime():
    if "runtime" not in _mem:
        try:
            with open(RUNTIME_CACHE, encoding="utf-8") as fh:
                _mem["runtime"] = json.load(fh)
        except (OSError, ValueError):
            _mem["runtime"] = {"queries": {}}
    return _mem["runtime"]


def _save_runtime():
    try:
        tmp = RUNTIME_CACHE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(_mem["runtime"], fh, ensure_ascii=False)
        os.replace(tmp, RUNTIME_CACHE)
    except OSError:
        pass  # read-only filesystem (serverless): keep the in-memory copy


def cached_query(skey, live=LIVE):
    """{"results": [...], "retrieved": date} for a query, fetching once if allowed."""
    for store in (_load_built(), _load_runtime()):
        hit = store["queries"].get(skey)
        if hit:
            return hit
    if not live:
        return None
    results = parse(fetch(skey))
    entry = {"results": results, "retrieved": datetime.date.today().isoformat()}
    _load_runtime()["queries"][skey] = entry
    _save_runtime()
    return entry


def grades_for(hid, live=LIVE):
    """Attributed grades for a hadith, or a status explaining why there are none."""
    h = engine.hadith_record(hid)
    if h is None:
        return None
    base = {"id": hid, "source": SOURCE_NAME, "api": API, "dataset_grade": engine.card(h)["grade_prov"]}
    if not h["matn"]:
        return {**base, "status": "no_text", "items": []}
    skey = _query_for(h["matn"])
    try:
        entry = cached_query(skey, live=live)
    except Exception as exc:  # network error, timeout, unexpected format
        return {**base, "status": "unavailable", "detail": type(exc).__name__, "items": [], "query": skey}
    if entry is None:
        return {**base, "status": "not_fetched", "items": [], "query": skey}
    items = match(h, entry["results"], skey, entry["retrieved"])
    return {**base, "status": "ok" if items else "no_match", "items": items, "query": skey,
            "results_seen": len(entry["results"]), "retrieved": entry["retrieved"],
            "search_url": f"{SEARCH_PAGE}?{urllib.parse.urlencode({'q': skey})}"}
