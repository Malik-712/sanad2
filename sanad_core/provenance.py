"""Provenance records for every religious fact Sanad shows.

See .claude/skills/religious-sourcing/SKILL.md. A record always has
source, url, quote, retrieved, method; plus confidence when a match or a
parse is involved. The UI renders it in "كيف حصلنا على هذه المعلومة؟".
"""

MISSING = "غير متوفر في المصدر"

# ---------------------------------------------------------------- LK corpus
LK_NAME = "مدونة LK للحديث (LK Hadith Corpus) — جامعة ليدز وجامعة الملك سعود"
LK_REPO = "https://github.com/ShathaTm/LK-Hadith-Corpus"
# The v0 data files were built from the corpus on or before this date (first
# commit of this repository). Upstream has not changed since 2023-05-03.
LK_RETRIEVED = "2026-09-28"
LK_FOLDER = {"bukhari": "Bukhari", "muslim": "Muslim", "abudawud": "AbuDaud",
             "tirmidhi": "Tirmizi", "nasai": "Nesai", "ibnmajah": "IbnMaja"}


def lk_url(h):
    src = h.get("src")
    if src:
        return f"{LK_REPO}/blob/master/{src}"
    return f"{LK_REPO}/tree/master/{LK_FOLDER.get(h['book'], '')}"


def make(source, url, quote, retrieved, method, confidence=None, **extra):
    rec = {"source": source, "url": url, "quote": quote if quote else MISSING,
           "retrieved": retrieved, "method": method}
    if confidence is not None:
        rec["confidence"] = confidence
    rec.update(extra)
    return rec


def lk(h, column, quote, method=None, confidence=None, **extra):
    """A fact read from one column of the LK corpus CSV row of hadith h."""
    where = f"{h.get('src') or LK_FOLDER.get(h['book'], '')}، رقم الحديث {h['number']}"
    return make(LK_NAME, lk_url(h), quote, LK_RETRIEVED,
                method or f"نُقل كما هو من عمود {column} في ملف المدونة ({where}).",
                confidence, **extra)


# ------------------------------------------------------------------ methods
PARSE_METHOD = {
    "direct": "قراءة آلية للسند بقواعد مكتوبة: تقسيم النص عند ألفاظ التحديث (حدثنا، أخبرنا، عن ...).",
    "co_narrator": "راويان أو أكثر معطوفان بالواو في طبقة واحدة؛ لكل منهما طريق.",
    "convergence": "وصل طريق التحويل (ح) بما بعد «كلاهما/كلهم/جميعًا عن» كما في نص السند.",
    "shared_name": "وصل طريق التحويل (ح) عند اسم مشترك يتكرر في الطريقين.",
    "complete_segment": "طريق قبل التحويل (ح) يذكر النبي ﷺ بعد آخر راوٍ فيه.",
    "shared_name_taliq": "وصل السند بما بعد «وقال لي فلان» عند اسم مشترك.",
    "prior_isnad": "السند يقول «بهذا الإسناد»، فأكمله سند من الحديث الذي قبله في الكتاب نفسه عند أول اسم مشترك.",
}


def parse_method(join):
    parts = [p for p in (join or "direct").split("+") if p]
    return " ".join(PARSE_METHOD.get(p, p) for p in parts)
