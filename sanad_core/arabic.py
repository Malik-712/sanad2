"""Arabic text normalization used by both the offline pipeline and the API.

Normalization is intentionally conservative: it only removes variation that
does not change meaning for search purposes (diacritics, tatweel, letter
variants). The original, diacritized text is always kept for display.
"""
import re

_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ]")
_TATWEEL = "ـ"
_NON_ARABIC = re.compile(r"[^ء-ي0-9\s]")
_SPACES = re.compile(r"\s+")

_LETTER_MAP = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
    "ى": "ي", "ئ": "ي",
    "ؤ": "و",
    "ة": "ه",
})

# Phrases that appear in the text but carry no content for search.
_HONORIFICS = [
    "صلى الله عليه وسلم", "صلي الله عليه وسلم",
    "رضى الله عنهما", "رضي الله عنهما", "رضى الله عنها", "رضي الله عنها",
    "رضى الله عنه", "رضي الله عنه", "رضى الله عنهم", "رضي الله عنهم",
    "عليه السلام", "عليه الصلاه والسلام",
]


def strip_diacritics(text: str) -> str:
    return _DIACRITICS.sub("", text or "").replace(_TATWEEL, "")


def normalize(text: str, drop_honorifics: bool = True) -> str:
    t = strip_diacritics(text).translate(_LETTER_MAP)
    t = _NON_ARABIC.sub(" ", t)
    t = _SPACES.sub(" ", t).strip()
    if drop_honorifics:
        for h in sorted(_HONORIFICS, key=len, reverse=True):
            t = t.replace(h.translate(_LETTER_MAP), " ")
        t = _SPACES.sub(" ", t).strip()
    return t


# Very frequent words that add noise to ranking.
STOPWORDS = set(normalize(w, False) for w in """
في من على عن الى إلى ان أن إن ما لا لم لن قد ثم او أو و ف ب ل هو هي هم هن انا أنا انت
نحن كان كانت يكون قال قالت فقال فقالت يقول تقول قالوا الله رسول النبي صلى عليه وسلم
هذا هذه ذلك تلك الذي التي الذين حتى اذا إذا كل بن ابن ابي أبي ابو أبو عنه عنها له لها
به بها منه منها فيه فيها يا اي أي مع بعد قبل عند
""".split())


def tokens(text: str, keep_stopwords: bool = False):
    words = normalize(text).split()
    if keep_stopwords:
        return words
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


def char_ngrams(text: str, n: int = 3):
    """Character n-grams inside word boundaries (robust to typos)."""
    grams = []
    for w in normalize(text).split():
        w = f" {w} "
        grams.extend(w[i:i + n] for i in range(max(1, len(w) - n + 1)))
    return grams
