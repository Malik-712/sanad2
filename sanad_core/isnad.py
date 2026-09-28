"""Parse an isnad (chain of narration) into an ordered list of narrator names.

Version 0 is rule-based and deliberately transparent:
- it splits the chain on transmission words (حدثنا، أخبرنا، عن، ...),
- resolves relative references like "عن أبيه" when the father's name is
  visible in the previous narrator's name,
- flags anything uncertain instead of hiding it.

Known limits (documented, not hidden):
- chains with تحويل (ح) contain several routes; v0 keeps the last route only
  and marks the chain as partial.
- two narrators joined by "و" at the same level: v0 keeps the first one.
"""
import re
from .arabic import normalize

MARKERS = [
    "حدثنا", "حدثني", "حدثناه", "حدثنيه", "حدثه", "حدثهم", "حدث",
    "اخبرنا", "اخبرني", "اخبرناه", "اخبرنيه", "اخبره", "اخبرهم",
    "انبانا", "انباني", "انباه", "ثنا", "نا", "انا",
    "سمعت", "سمعنا", "سمع", "يحدث", "يخبر",
    "عن", "ان", "انه", "انها", "انهم",
    "قال", "قالت", "قالا", "قالوا", "يقول", "تقول", "يقولون",
    "كتب", "كتب الي",
]
FILLER = {
    "كلاهما", "كلهم", "جميعا", "يعني", "واللفظ", "لفظ", "له", "وهذا",
    "لفظه", "حديث", "بهذا", "الاسناد", "وهو", "هو", "ايضا", "مرفوعا",
    "قراءه", "عليه", "واللفظ", "وحده", "نحوه", "مثله", "اسمع", "وانا",
}
_MARKER_RE = re.compile(r"(?:^|\s)(?:و|ف)?(?:" + "|".join(sorted(MARKERS, key=len, reverse=True)) + r")(?=\s|$)")

# Names that are too short or too common to merge safely across chains.
AMBIGUOUS_SINGLE = {
    "سفيان", "حماد", "هشام", "شعبه", "عبد الله", "عبيد الله", "محمد", "يحيي",
    "ابراهيم", "سليمان", "اسماعيل", "عبد الرحمن", "ابو معاويه", "ابو بكر",
    "ابن وهب", "ابو عوانه", "جرير", "ابو اسامه", "عبد الوهاب", "خالد",
    "ابيه", "جده", "عمه", "امه", "رجل", "ابو صالح", "سعيد", "عمرو",
}

_KUNYA_CASE = re.compile(r"^(ابي|ابا)\s")
_TRAILING_JUNK = re.compile(r"\s(قال|قالت|يقول|انه|ان|في|من|و)$")


def canonical(name: str) -> str:
    n = name.strip()
    n = _KUNYA_CASE.sub("ابو ", n)
    n = re.sub(r"\sابن\s", " بن ", n)
    for _ in range(3):
        n = _TRAILING_JUNK.sub("", n)
    return re.sub(r"\s+", " ", n).strip()


_NAME_LINKS = {"بن", "ابن", "ابو", "ابي", "ابا", "ام", "بنت", "عبد", "ذو", "ذي"}
_NOT_A_NAME = {"ابن", "بن", "ابو", "ابي", "ام", "بنت", "اسمع", "وانا", "انا", "قراءه", "عليه", "له", "لي", "لنا"}
_LEADING_NOISE = {"زعم", "زعموا", "ذكر", "ان", "قال", "قالت", "سمعت", "يقول", "حديثه"}
_STOP_IN_NAME = {"يخطب", "وهو", "وهي", "يحدث", "يرفعه", "رفعه", "به", "بذلك", "بمكه", "بالمدينه",
                 "يوم", "وكان", "كان", "انه", "انها", "يذكر", "في", "من", "الي", "حين"}
_READ_PREFIX = re.compile(r"^(قرات|قرا|قرئ|قريت)\s+علي\s+")
_NOT_NAME_ENDING_T = {"بنت", "ثابت", "عصمت"}


def _clean_piece(piece: str) -> str:
    piece = _READ_PREFIX.sub("", piece.strip())
    piece = piece.split(" في ")[0]
    words = [w for w in piece.split() if w not in FILLER]
    if words and len(words[0]) >= 3 and words[0].endswith("ت") and words[0] not in _NOT_NAME_ENDING_T:
        return ""  # a first-person verb such as "صببت" / "دخلت", not a name
    # "و" joining two narrators at the same level: keep the first narrator only.
    # (but not inside a name: "علقمة بن وقاص", "أبو وائل")
    while words and words[0] in _LEADING_NOISE:
        words = words[1:]
    kept = []
    for k, w in enumerate(words):
        if k > 0 and (w in _STOP_IN_NAME or (w == "علي" and words[k - 1] not in _NAME_LINKS)):
            break
        if k > 0 and w.startswith("و") and len(w) > 2 and words[k - 1] not in _NAME_LINKS:
            break
        kept.append(w)
    txt = " ".join(kept).strip()
    if txt in _NOT_A_NAME:
        return ""
    return txt


def repair_segmentation(isnad_norm: str, matn_norm: str):
    """The automatic isnad/matn split sometimes leaves the companion's name at
    the start of the matn (e.g. isnad ends with "عن ابي", matn starts with
    "هريره ان ..."). Move those words back into the isnad for parsing."""
    tail = isnad_norm.split()[-1:] if isnad_norm else []
    if not tail:
        return isnad_norm, False
    if tail[0] in {"عن", "حدثنا", "حدثني", "اخبرنا", "اخبرني", "سمعت", "ابي", "ابو", "ابن", "بن", "ام", "بنت", "عبد"}:
        words = matn_norm.split()
        take = []
        for w in words[:5]:
            if w in {"قال", "قالت", "ان", "انه", "انها", "يقول", "قالا", "عن"}:
                break
            take.append(w)
        if take and len(take) < 5:
            return isnad_norm + " " + " ".join(take), True
    return isnad_norm, False


def parse_isnad(isnad_text: str, matn_text: str = ""):
    """Return dict(names=[...from compiler's teacher to companion], partial, repaired)."""
    isnad = normalize(isnad_text)
    matn = normalize(matn_text)
    isnad, repaired = repair_segmentation(isnad, matn)
    partial = False
    segments = re.split(r"(?:^|\s)و?ح(?=\s)", " " + isnad + " ")
    if len(segments) > 1:
        partial = True
        isnad = segments[-1]
    pieces = _MARKER_RE.split(" " + isnad + " ")
    names = []
    for p in pieces:
        c = _clean_piece(p)
        if not c:
            continue
        n_words = len(c.split())
        if n_words > 8 or "رسول" in c or "النبي" in c:
            continue
        c = canonical(c)
        if c and (not names or names[-1] != c):
            names.append(c)
    # resolve relative references
    resolved = []
    for i, n in enumerate(names):
        rel = None
        if n in {"ابيه", "ابوه"} and resolved:
            prev = resolved[-1]["name"]
            m = re.search(r"\sبن\s(.+)$", prev)
            if m:
                father = m.group(1).split(" بن ")[0]
                rel = father
            else:
                rel = f"والد {prev}"
        elif n == "جده" and resolved:
            rel = f"جد {resolved[-2]['name'] if len(resolved) > 1 else resolved[-1]['name']}"
        elif n in {"عمه", "امه", "خاله"} and resolved:
            rel = f"{n[:-1]} {resolved[-1]['name']}"
        name = rel or n
        fallback = bool(rel) and (rel.startswith("والد ") or rel.startswith("جد ") or " " in rel and rel.split()[0] in {"عم", "ام", "خال"})
        is_last = i == len(names) - 1
        uncertain = fallback or name in AMBIGUOUS_SINGLE or (len(name.split()) == 1 and not is_last and not rel)
        resolved.append({"name": name, "uncertain": uncertain, "relative": bool(rel)})
    # the same narrator written twice in a row ("عمر" then "عمر بن الخطاب")
    merged = []
    for n in resolved:
        if merged:
            a, b = merged[-1]["name"].split(), n["name"].split()
            k = min(len(a), len(b))
            if a[:k] == b[:k]:
                if len(b) > len(a):
                    merged[-1] = n
                continue
        merged.append(n)
    return {"names": merged, "partial": partial, "repaired": repaired}
