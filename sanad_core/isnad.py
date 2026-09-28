"""Parse an isnad (chain of narration) into routes of narrator names.

Rule-based and deliberately transparent. The parser only *reads* the chain;
it never adds a name that is not written in the text. Every name keeps the
span of original (diacritized) words it came from, so the UI can quote it.

What it handles:
- transmission words (حدثنا، أخبرنا، حدثتني، عن، أن، سمعت، ...), which split
  the chain into levels;
- two or more narrators joined by "و" at one level ("حدثنا فلان وفلان قالا"):
  each becomes its own route;
- doubt between two narrators ("عن فلان أو عن فلان، شك فلان"): both kept as
  alternatives and marked uncertain;
- تحويل (ح): the chain is cut into segments. A segment is joined to a later
  one only when the text says where:
    * "كلاهما عن X" joins the previous open segment at X,
    * "كلهم / جميعا / كل هؤلاء عن X" joins every open segment at X,
    * a segment that stops at a name which appears again in a later segment
      joins there (shared name).
  A segment that cannot be joined this way is returned as a fragment and is
  not used in the tree. Nothing is guessed.
- "قال فلان حدثنا وقال الآخران أخبرنا": wording notes, not narrators;
- relative references ("عن أبيه"، "حدثني أبي"، "عن جده"، "أخي"): resolved
  from the previous name only when the name itself says it ("X بن Y عن
  أبيه" → Y); otherwise written as "والد X" and marked uncertain;
- verbs and narration words that follow the chain ("قال كان ...", "لما"):
  dropped instead of becoming names.
"""
import re

from .arabic import normalize

# ------------------------------------------------------------------ lexicon
MARKERS = {
    "حدثنا", "حدثني", "حدثناه", "حدثنيه", "حدثه", "حدثهم", "حدث", "حدثناها",
    "حدثتني", "حدثتنا", "حدثته", "حدثتهم", "حدثاني", "حدثانا", "حدثونا", "حدثوني",
    "اخبرنا", "اخبرني", "اخبرناه", "اخبرنيه", "اخبره", "اخبرهم", "اخبرتني", "اخبرتنا",
    "اخبرته", "اخبراني", "اخبرانا", "اخبرونا",
    "انبانا", "انباني", "انباه", "ثنا", "نا", "انا",
    "سمعت", "سمعنا", "سمع", "سمعته", "سمعا", "يحدث", "يحدثنا", "يحدثه", "يخبر", "يخبرنا",
    "عن", "ان", "انه", "انها", "انهم", "انهما",
    "قال", "قالت", "قالا", "قالوا", "يقول", "تقول", "يقولون", "يقولان",
    "كتب", "سالت", "فسالت", "لقيت",
}
# two-word markers: "قرات على مالك" / "قرئ على" / "كتب الي"
READ_ON = {"قرات", "قرا", "قرئ", "قريت"}
TO_ME = {"الي", "الينا"}

# a later segment starts after ح
TAHWIL = {"ح", "وح"}
# "كلاهما عن X" / "كلهم عن X" ...: open segments converge at X
CONVERGE_TWO = {"كلاهما", "كلاهم"}
CONVERGE_ALL = {"كلهم", "جميعا", "هولاء", "جميعهم"}
OTHERS = {"الاخران", "الاخرون", "الاخر", "الباقون"}
# "بهذا الاسناد": the chain continues as in the previous hadith
SAME_ISNAD = {"باسناده", "باسنادهما", "باسنادهم", "باسناد"}

# honorifics removed before parsing (normalized form, word sequences)
_HONORIFICS = [s.split() for s in (
    "صلي الله عليه وسلم", "رضي الله عنهما", "رضي الله عنها", "رضي الله عنهم",
    "رضي الله عنه", "رضي الله عنهن", "عليه السلام", "عليه الصلاه والسلام", "رحمه الله",
    "تعالي", "عز وجل",
)]

# a new "وحدثنا" after a chain has started is a new route (like ح)
RESTART = {"وحدثنا", "وحدثني", "واخبرنا", "واخبرني", "وحدثناه", "واخبرناه", "وانبانا", "وحدثنيه"}
NARRATED = {"روي", "وروي", "رواه", "ورواه", "ورواه"}
COMPILER_REMARK = {"ابو عيسي", "ابو داود", "ابو عبد الرحمن", "ابو الحسن"}

FILLER = {
    "كلاهما", "كلهم", "جميعا", "يعني", "له", "لفظه", "بهذا", "الاسناد", "ايضا", "مرفوعا",
    "قراءه", "عليه", "وحده", "نحوه", "مثله", "اسمع", "وانا", "انا", "هو", "وهو",
}
# words after which the rest of the piece is not part of a name
STOP_IN_NAME = {
    "يخطب", "وهو", "وهي", "يحدث", "يرفعه", "رفعه", "به", "بذلك", "بمكه", "بالمدينه",
    "يوم", "وكان", "كان", "انه", "انها", "يذكر", "في", "من", "الي", "حين", "او", "شك",
    "رده", "باسناد", "باسناده", "بهذا", "مثل", "بمثل", "معناه", "بمعناه", "بمعني", "نحو", "نحوه",
    "بنحوه", "مثله", "بمثله", "واللفظ", "اللفظ", "والفاظهم", "وهذا", "لفظه", "قصه", "بقصه",
    "حديث", "بحديث", "الحديث", "كل", "هولاء", "كلاهما", "كلهم", "جميعا", "موقوفا", "مرفوعا",
    "وغيره", "وغيرهما", "وغير", "غير", "ونحن", "وانا", "قراءه", "عليه", "عليها", "وذكر", "وزاد",
    "زاد", "ذكر", "يعني", "قالا", "قال", "قالت",
}
# the first word of a piece that means the piece is narration, not a name
NON_NAME_START = {
    "كان", "كانت", "كنا", "كنت", "لما", "اذا", "اذ", "ثم", "جاء", "جاءنا", "ذكر", "زاد",
    "دخل", "دخلنا", "خرج", "خرجنا", "سال", "سالت", "سالنا", "سالني", "سالوا", "بعث", "امر",
    "انت", "فينا", "بينا", "بينما", "عندنا", "علينا", "اصحابنا", "بلغني", "بلغه", "قلت",
    "فقلت", "قلنا", "اتي", "اتينا", "اتانا", "راي", "رايت", "لو", "ما", "لا", "هل", "كيف", "اما",
    "نحوه", "مثله", "بمثله", "بنحوه", "بمعناه", "بهذا", "بذلك", "باسناده", "يرفعه", "رفعه",
    "مرفوعا", "موقوفا", "شك", "او", "نحو", "مثل", "معناه", "حديثا", "خبرا", "فذكر", "فذكرنا",
    "واللفظ", "اللفظ", "والفاظهم", "لفظ", "هكذا", "كذا", "قد", "لقد", "انما", "والله", "لي",
    "لنا", "له", "لها", "لهم", "اني", "انا", "نحن", "هذا", "هذه", "ذلك", "يوما", "فلما",
    "حتي", "الا", "ليس", "وكان", "وقد", "فقال", "فقالت", "وقال", "وقالت", "يا", "امراه", "رجلا",
}
EXPLAIN = {"وهو", "هو", "يعني", "وهي", "اعني"}
# words that stand for a narrator the chain does not name
UNNAMED = {"الثقه", "رجل", "شيخ", "بعض اصحابنا", "رجل من اصحابه", "بعضهم", "من لا اتهم"}
NAME_LINKS = {"بن", "ابن", "ابو", "ابي", "ابا", "ام", "بنت", "عبد", "ذو", "ذي", "ذا", "اخو", "اخي", "مولي"}
NOT_A_NAME = {"ابن", "بن", "ابو", "ابا", "ام", "بنت", "عبد", "اسمع", "وانا", "انا", "قراءه",
              "عليه", "له", "لي", "لنا", "رجال", "ناس", "اناس", "غيره", "غيرهما", "بعضهم"}
LEADING_NOISE = {"زعم", "زعموا", "ان", "قال", "قالت", "سمعت", "يقول", "حديثه", "ايضا"}
# narrators whose names start with "و" (not a conjunction)
WAW_NAMES = {"وكيع", "وهب", "وهيب", "واصل", "وائل", "وايل", "ورقاء", "ورقاء", "وبره", "وحشي",
             "واقد", "وردان", "وضاح", "ورقه", "وابصه", "واثله", "وهبان", "وقاص", "والان", "وعله"}
# first words ending like first-person verbs that are nevertheless names
NAME_ENDING_T = {"بنت", "ثابت", "عصمت", "فرات", "الصلت", "صلت", "رافت", "شوكت", "حيوت", "بخت"}
NAME_ENDING_NI = {"هاني", "مثني", "يماني", "رباني", "عاني", "سفياني"}

# relative references: word -> (relation, speaker is "me" or "him")
RELATIVE = {
    "ابيه": "father", "ابوه": "father", "اباه": "father", "ابيها": "father", "ابيهما": "father",
    "ابي": "father", "والده": "father", "جده": "grandfather", "جدي": "grandfather",
    "جدته": "grandmother", "جدتي": "grandmother", "عمه": "uncle", "عمي": "uncle",
    "امه": "mother", "امي": "mother", "خاله": "maternal_uncle", "خالي": "maternal_uncle",
    "اخيه": "brother", "اخي": "brother", "اخوه": "brother", "اخته": "sister", "اختي": "sister",
}
RELATIVE_LABEL = {
    "father": "والد", "grandfather": "جد", "grandmother": "جدة", "uncle": "عم", "mother": "أم",
    "maternal_uncle": "خال", "brother": "أخو", "sister": "أخت",
}

# Names that are too short or too common to merge safely across chains.
AMBIGUOUS_SINGLE = {
    "سفيان", "حماد", "هشام", "شعبه", "عبد الله", "عبيد الله", "محمد", "يحيي",
    "ابراهيم", "سليمان", "اسماعيل", "عبد الرحمن", "ابو معاويه", "ابو بكر",
    "ابن وهب", "ابو عوانه", "جرير", "ابو اسامه", "عبد الوهاب", "خالد",
    "ابيه", "جده", "عمه", "امه", "رجل", "ابو صالح", "سعيد", "عمرو",
}

MAX_ROUTES = 24          # cap on routes expanded from one isnad
MAX_NAME_WORDS = 8


# ------------------------------------------------------------------ helpers
def canonical(name: str) -> str:
    """Spelling-level normalization of a name (never changes who it is)."""
    ws = name.split()
    # "ابي هريره" / "ابا هريره" -> "ابو هريره"; but "ابي بن كعب" is the name
    # Ubayy, not a kunya
    if ws and ws[0] in {"ابي", "ابا"} and len(ws) > 1 and ws[1] not in {"بن", "ابن"}:
        ws[0] = "ابو"
    ws = ["بن" if (w == "ابن" and i > 0) else w for i, w in enumerate(ws)]
    while ws and ws[-1] in {"قال", "قالت", "يقول", "انه", "ان", "في", "من", "و"}:
        ws.pop()
    return " ".join(ws)


def _tokens(text, offset=0):
    """Normalized words, each with the index of the original word it came from."""
    out = []
    for oi, ow in enumerate((text or "").split()):
        for w in normalize(ow, drop_honorifics=False).split():
            out.append((w, oi + offset))
    # drop honorific word sequences
    i, clean = 0, []
    while i < len(out):
        for h in _HONORIFICS:
            if [t[0] for t in out[i:i + len(h)]] == h:
                i += len(h)
                break
        else:
            clean.append(out[i])
            i += 1
    return clean


def _is_marker(w):
    if w in MARKERS:
        return True
    return len(w) > 2 and w[0] in "وف" and w[1:] in MARKERS


def _looks_like_verb(w):
    if w in NON_NAME_START:
        return True
    if w.startswith("ال"):
        return False
    if len(w) >= 3 and w.endswith("ت") and w not in NAME_ENDING_T:
        return True
    if len(w) >= 3 and w.endswith("نا"):
        return True
    if len(w) >= 4 and w.endswith("ني") and w not in NAME_ENDING_NI:
        return True
    if len(w) >= 4 and w.endswith("وا"):
        return True
    return False


def _name(words):
    """Build a name dict from [(word, orig_idx), ...] or None if not a name."""
    if not words:
        return None
    txt = canonical(" ".join(w for w, _ in words))
    if not txt or txt in NOT_A_NAME or len(txt.split()) > MAX_NAME_WORDS:
        return None
    if "رسول" in txt.split() or "النبي" in txt.split():
        return None
    # four words or more with no link word (بن، أبو، عبد ...) is text, not a name
    if len(txt.split()) >= 4 and not any(w in NAME_LINKS for w in txt.split()):
        return None
    return {"name": txt, "span": [words[0][1], words[-1][1] + 1]}


# ------------------------------------------------------------------ pieces
def _split_pieces(tokens):
    """Cut a token list at transmission words.
    Returns [(marker_before, piece_tokens)]; marker_before is '' for the first."""
    pieces, cur, marker = [], [], ""
    i = 0
    while i < len(tokens):
        w = tokens[i][0]
        nxt = tokens[i + 1][0] if i + 1 < len(tokens) else ""
        if w in READ_ON and nxt == "علي":
            pieces.append((marker, cur))
            cur, marker = [], "قرات علي"
            i += 2
            continue
        if w in {"رده", "يرفعه", "رفعه"} and nxt in TO_ME:
            pieces.append((marker, cur))
            cur, marker = [], "رده الي"
            i += 2
            continue
        if w == "كتب" and nxt in TO_ME:
            pieces.append((marker, cur))
            cur, marker = [], "كتب الي"
            i += 2
            continue
        if _is_marker(w):
            pieces.append((marker, cur))
            cur, marker = [], w
        else:
            cur.append(tokens[i])
        i += 1
    pieces.append((marker, cur))
    return [(m, p) for m, p in pieces if p or m]


def _piece_names(piece):
    """One piece of text between two transmission words -> list of co-narrators
    (usually one), plus flags. Returns (names, flags)."""
    flags = set()
    words = list(piece)
    while words and (words[0][0] in LEADING_NOISE or words[0][0] in FILLER):
        words = words[1:]
    if any(w in CONVERGE_TWO for w, _ in piece):
        flags.add("converge_two")
    if any(w in CONVERGE_ALL for w, _ in piece):
        flags.add("converge_all")
    if any(w in SAME_ISNAD for w, _ in piece) or any(
            a == "بهذا" and b in {"الاسناد", "الحديث"} for (a, _), (b, _) in zip(piece, piece[1:])):
        flags.add("same_isnad")
    if piece and piece[-1][0] == "او":
        flags.add("doubt_next")
    if words and words[0][0] in OTHERS:
        flags.add("others")
        return [], flags
    if not words or _looks_like_verb(words[0][0]):
        return [], flags
    if (len(words) > 1 and words[0][0] in RELATIVE and words[0][0] not in {"ابي", "ابا"}
            and words[1][0] not in STOP_IN_NAME | {"بن", "ابن"} and not words[1][0].startswith("و")):
        words = words[1:]
    names, cur = [], []
    explaining = False
    for k, (w, oi) in enumerate(words):
        prev = words[k - 1][0] if k else ""
        # "فلان وهو ابن فلان ..." / "يعني ابن فلان": an explanation of the name
        # before it; skip it up to the next co-narrator ("وفلان"), if any
        if k and w in EXPLAIN:
            explaining = True
            continue
        if explaining:
            if w.startswith("و") and len(w) > 2 and w not in WAW_NAMES and prev not in NAME_LINKS:
                explaining = False
            else:
                continue
        if k and (w in STOP_IN_NAME or (w == "علي" and prev not in NAME_LINKS)):
            break
        if k and prev not in NAME_LINKS and _looks_like_verb(w) and not w.startswith("و"):
            break
        bare_relative = k == 1 and prev in RELATIVE
        conj = w == "و" or (k and w.startswith("و") and len(w) > 2
                              and (prev not in NAME_LINKS or bare_relative) and w not in WAW_NAMES)
        if conj:
            rest = w[1:]
            n = _name(cur)
            if n:
                names.append(n)
            cur = []
            if not rest or rest in {"غيره", "غيرهما", "غير", "حده", "اللفظ", "الفاظهم", "هذا", "هو", "هي"}:
                if rest in {"غيره", "غيرهما", "غير", "اللفظ", "الفاظهم", "هذا"}:
                    break
                continue
            if _looks_like_verb(rest):
                break
            cur = [(rest, oi)]
            continue
        cur.append((w, oi))
    n = _name(cur)
    if n:
        names.append(n)
    return names, flags


# ------------------------------------------------------------------ segments
def _segments(tokens):
    """Split the chain into segments. Returns [(kind, tokens)] where kind is
    first | tahwil (after ح, or a new "وحدثنا" once a chain has started) |
    others ("وقال الآخران") | taliq ("وقال فلان ..." / "وروى ...": a chain the
    compiler mentions without his own connected link; kept as a fragment).
    The compiler's own remarks ("قال أبو عيسى ...") end the chain."""
    segs, cur, kind = [], [], "first"
    reached = False  # the Prophet was named: the rest is not chain, until a new segment
    i = 0
    while i < len(tokens):
        w = tokens[i][0]
        nxt = tokens[i + 1][0] if i + 1 < len(tokens) else ""
        nxt2 = tokens[i + 2][0] if i + 2 < len(tokens) else ""
        if reached and not (w in TAHWIL or w in RESTART or w in NARRATED
                            or (w in {"حدثنا", "اخبرنا"} and nxt in {"بذلك", "به", "بهذا"})):
            i += 1
            continue
        if cur and (w in {"النبي", "للنبي"} or (w in {"رسول", "لرسول"} and nxt == "الله")):
            cur.append(tokens[i])
            if nxt == "الله":
                cur.append(tokens[i + 1])
            reached = True
            i += 2 if nxt == "الله" else 1
            continue
        if reached:
            reached = False
        if w in {"قال", "وقال"} and f"{nxt} {nxt2}" in COMPILER_REMARK:
            if cur or segs:
                break
            i += 3  # "قال أبو داود حدثنا ...": the compiler introduces his chain
            continue
        # "... حدثنا بذلك فلان": after a mention, the compiler's own chain
        if w in {"حدثنا", "اخبرنا", "حدثني", "اخبرني"} and nxt in {"بذلك", "به", "بهذا"} and (
                kind == "taliq" or len(cur) >= 2):
            segs.append((kind, cur))
            cur, kind = [tokens[i]], "tahwil"
            i += 2
            continue
        if w in RESTART and len(cur) >= 2:
            segs.append((kind, cur))
            cur, kind = [], "tahwil"
            cur.append(tokens[i])
            i += 1
            continue
        if (w in NARRATED or (w == "وقال" and nxt not in OTHERS and len(cur) >= 2
                              and any(_is_marker(t[0]) and t[0] not in {"قال", "وقال"}
                                      for t in tokens[i + 1:i + 7]))):
            segs.append((kind, cur))
            cur, kind = [], "taliq"
            i += 1
            continue
        if w in TAHWIL:
            segs.append((kind, cur))
            cur, kind = [], "tahwil"
            i += 1
            continue
        if w in {"قال", "وقال"} and nxt in OTHERS:
            segs.append((kind, cur))
            cur, kind = [], "others"
            i += 2
            continue
        cur.append(tokens[i])
        i += 1
    segs.append((kind, cur))
    return [(k, t) for k, t in segs if t]


def _parse_segment(tokens):
    """-> dict(levels=[[name,...],...], converge=[(level_idx, 'two'|'all')],
    restated=name|None, same_isnad=bool)."""
    levels, converge, restated = [], [], None
    same_isnad = False
    doubt = False
    after_lafz = False
    pieces = _split_pieces(tokens)
    for pi, (marker, piece) in enumerate(pieces):
        names, flags = _piece_names(piece)
        if marker in {"يحدث", "يحدثه", "يخبر"} and len(names) == 1 and names[0]["name"] in RELATIVE:
            names = []
        same_isnad |= "same_isnad" in flags
        next_marker = pieces[pi + 1][0] if pi + 1 < len(pieces) else ""
        # "قال أبو بكر حدثنا ...": names which of the co-narrators above says
        # the following words; it is not a new narrator.
        # "قال أبو بكر حدثنا ..." / "وقال إسحاق أخبرنا": names which of the
        # narrators above says the following words; it is not a new narrator.
        if names and marker in {"قال", "وقال"} and levels:
            hit = [n for lv in levels for n in lv if _prefix_match(n["name"], names[0]["name"])]
            if hit:
                if hit[0] in levels[0] and len(levels[0]) > 1:
                    restated = hit[0]
                continue
        # "جميعا عن يحيى القطان واللفظ لزهير حدثنا يحيى بن سعيد": after a
        # wording note, the same first name again restates the level above
        if (names and after_lafz and levels and len(names) == 1
                and names[0]["name"].split()[0] == levels[-1][0]["name"].split()[0]):
            names = []
        after_lafz = any(w in {"واللفظ", "اللفظ", "والفاظهم"} for w, _ in piece)
        if names:
            if doubt and levels:
                for n in names:
                    n["doubt"] = True
                for n in levels[-1]:
                    n["doubt"] = True
                levels[-1].extend(names)
            else:
                levels.append(names)
        # convergence words stand before the marker that introduces the
        # common narrator: "... كلاهما عن X" -> X is the next level
        # ...unless it follows co-narrators of this segment ("فلان وفلان جميعا
        # عن X"): then it only says those co-narrators share X
        within = bool(levels) and len(levels[-1]) > 1
        if "converge_two" in flags and not within:
            converge.append((len(levels), "two"))
        elif "converge_all" in flags and not within:
            converge.append((len(levels), "all"))
        doubt = "doubt_next" in flags and bool(names or levels)
    return {"levels": levels, "converge": converge, "restated": restated, "same_isnad": same_isnad}


def _prefix_match(a, b):
    wa, wb = a.split(), b.split()
    k = min(len(wa), len(wb))
    return k >= 1 and wa[:k] == wb[:k]


def _dedupe_levels(levels):
    """The same narrator written twice in a row ("عمر" then "عمر بن الخطاب")."""
    out = []
    for lv in levels:
        if out and len(lv) == 1 and len(out[-1]) == 1 and _prefix_match(out[-1][0]["name"], lv[0]["name"]):
            if len(lv[0]["name"].split()) > len(out[-1][0]["name"].split()):
                lv[0]["span"] = [min(lv[0]["span"][0], out[-1][0]["span"][0]), lv[0]["span"][1]]
                out[-1] = lv
            continue
        out.append(lv)
    return out


# ------------------------------------------------------------------ relatives
def _resolve_relatives(levels):
    """Replace "أبيه"، "جده"، "أخي" ... by a label built from the previous name."""
    for li, lv in enumerate(levels):
        for n in lv:
            rel = RELATIVE.get(n["name"])
            n["relative"] = bool(rel)
            n["uncertain"] = n.get("doubt", False)
            if not rel:
                continue
            if li == 0:
                n["uncertain"] = True
                continue
            prev = levels[li - 1][0]
            # the pronoun refers to the previous narrator; "عن أبيه عن جده" is
            # conventionally read as the grandfather of the first speaker
            # (and is ambiguous, so it is always marked uncertain)
            if rel == "grandfather" and prev.get("relative") and prev.get("speaker"):
                base = prev["speaker"]
            else:
                base = prev["name"]
            label = _father_from_name(base) if rel == "father" else None
            if label:
                n["name"] = label
                n["uncertain"] = n["uncertain"] or len(label.split()) == 1 or label in AMBIGUOUS_SINGLE
            else:
                n["name"] = f"{RELATIVE_LABEL[rel]} {base}"
                n["uncertain"] = True
            n["speaker"] = base
    return levels


def _father_from_name(name):
    """'X بن Y ...' -> 'Y ...' (dropping a final nisba).
    'ابن Y' alone is not used: it may name a grandfather or a family."""
    ws = name.split()
    if ws and ws[0] == "ابن":
        return None
    if "بن" in ws:
        rest = ws[ws.index("بن") + 1:]
    else:
        return None
    while len(rest) > 1 and rest[-1].startswith("ال") and rest[-2] not in NAME_LINKS:
        rest = rest[:-1]
    return canonical(" ".join(rest)) or None


def _mark_uncertain(levels):
    last = len(levels) - 1
    for li, lv in enumerate(levels):
        for n in lv:
            if n.get("relative"):
                continue
            n["uncertain"] = (n.get("uncertain") or n["name"] in AMBIGUOUS_SINGLE or n["name"] in UNNAMED
                              or (len(n["name"].split()) == 1 and li != last))
    return levels


# ------------------------------------------------------------------ main
def repair_segmentation(isnad_tokens, matn_tokens):
    """The automatic isnad/matn split sometimes leaves the companion's name at
    the start of the matn (isnad ends with "عن ابي", matn starts with
    "هريره ان ..."). Move those words back into the isnad for parsing."""
    if not isnad_tokens:
        return isnad_tokens, False
    tail = isnad_tokens[-1][0]
    if tail in {"عن", "حدثنا", "حدثني", "اخبرنا", "اخبرني", "سمعت", "ابي", "ابو", "ابا", "ابن",
                "بن", "ام", "بنت", "عبد"}:
        take = []
        for t in matn_tokens[:5]:
            if (t[0] in {"قال", "قالت", "ان", "انه", "انها", "يقول", "قالا", "عن"} or _is_marker(t[0])
                    or _looks_like_verb(t[0])):
                break
            take.append(t)
        if take and len(take) < 5:
            return isnad_tokens + take, True
    return isnad_tokens, False


def _reaches_prophet(tokens, last_idx, matn_tokens):
    """Is the Prophet named right after the last narrator (in the isnad tail or
    the first words of the matn)? Used to say whether the top of a route is
    followed by the Prophet in the text itself."""
    after = [w for w, oi in tokens if oi >= last_idx] + [w for w, _ in matn_tokens[:12]]
    for a, b in zip(after, after[1:] + [""]):
        if a in {"النبي", "للنبي", "بالنبي", "والنبي", "نبي"} or (a in {"رسول", "لرسول", "برسول"} and b == "الله"):
            return True
    return False


def parse_isnad(isnad_text: str, matn_text: str = ""):
    """Return a dict:
      names      primary route (compiler's teacher -> top), kept for v0 callers
      routes     [{"names": [...], "join": how the route was assembled}]
      fragments  segments of a ح chain that the text does not join
      tahwil     True if the chain contains ح
      same_isnad True if it says "بهذا الإسناد" (continues a previous chain)
      repaired   True if words were moved back from the matn
      to_prophet True if the Prophet is named right after the last narrator
    Each name: {"name", "span": [start, end) over isnad words + matn words,
                "uncertain", "relative", optional "doubt"}.
    """
    n_isnad_words = len((isnad_text or "").split())
    itoks = _tokens(isnad_text)
    mtoks = _tokens(matn_text, offset=n_isnad_words)
    itoks, repaired = repair_segmentation(itoks, mtoks)
    segs_raw = _segments(itoks)
    tahwil = any(k == "tahwil" for k, _ in segs_raw)

    segs = []
    for kind, toks in segs_raw:
        s = _parse_segment(toks)
        s["kind"] = kind
        s["toks"] = toks
        segs.append(s)

    # "وقال الآخران": wording note, or the route of the other co-narrators
    merged = []
    for s in segs:
        # "وقال إسحاق أخبرنا ..." where إسحاق is one of the co-narrators at
        # the head of the previous segment: the same as "وقال الآخر"
        if (s["kind"] == "taliq" and merged and s["levels"] and len(merged[-1]["levels"]) >= 1
                and len(merged[-1]["levels"][0]) > 1):
            head = merged[-1]["levels"][0]
            hit = next((n for n in head if _prefix_match(n["name"], s["levels"][0][0]["name"])), None)
            if hit:
                s["levels"] = s["levels"][1:]
                s["kind"] = "others"
                s["named_other"] = hit
        if s["kind"] == "others" and merged:
            prev = merged[-1]
            if prev["restated"] and len(prev["levels"]) > 1 and prev["levels"][0]:
                head = prev["levels"][0]
                others = [s["named_other"]] if s.get("named_other") else [
                    n for n in head if n is not prev["restated"]]
                prev["levels"][0] = [prev["restated"]]
                s["levels"] = [others] + s["levels"]
                s["kind"] = "others_route"
                merged.append(s)
            else:
                # nothing after "قال فلان حدثنا": only the wording differs
                off = len(prev["levels"])
                prev["toks"] = prev["toks"] + s["toks"]
                prev["levels"].extend(s["levels"])
                prev["converge"].extend((i + off, k) for i, k in s["converge"])
                prev["same_isnad"] |= s["same_isnad"]
            continue
        merged.append(s)
    taliq = [s for s in merged if s["kind"] == "taliq" and s["levels"]]
    segs = [s for s in merged if s["levels"] and s["kind"] != "taliq"]
    if not segs:
        return {"names": [], "routes": [], "fragments": [[n for lv in s["levels"] for n in lv[:1]] for s in taliq],
                "tahwil": tahwil,
                "same_isnad": False, "repaired": repaired, "to_prophet": False}

    for s in segs:
        s["levels"] = _mark_uncertain(_resolve_relatives(_dedupe_levels(s["levels"])))
        end = max((n["span"][1] for lv in s["levels"] for n in lv), default=0)
        # a segment before ح that already names the Prophet after its last
        # narrator is a complete route of its own
        s["complete"] = _reaches_prophet(s["toks"], end, [])

    for t in taliq:
        t["levels"] = _mark_uncertain(_resolve_relatives(_dedupe_levels(t["levels"])))
    last = len(segs) - 1
    # the main chain may stop at a name and continue in a following
    # "وقال لي فلان ..." segment that reaches the same name
    if taliq and not segs[last]["complete"]:
        tail = segs[last]["levels"][-1][0]["name"]
        for t in taliq:
            hit = next((k for k, lv in enumerate(t["levels"][:-1]) if _prefix_match(tail, lv[0]["name"])), None)
            if hit is not None:
                segs[last]["levels"] = segs[last]["levels"] + [lv[:1] for lv in t["levels"][hit + 1:]]
                segs[last]["taliq_join"] = True
                break

    # --- join segments ------------------------------------------------------
    # join[i] = (j, level_index_in_j, method): segment i continues with
    # segment j's levels from that index on.
    join = {}
    open_ = []
    for j, s in enumerate(segs):
        for lvl, kind in s["converge"]:
            if lvl >= len(s["levels"]):
                continue
            targets = open_[-1:] if kind == "two" else list(open_)
            for i in targets:
                join[i] = (j, lvl, "convergence")
                open_.remove(i)
        open_.append(j)
    for i in list(open_):
        if i == last or segs[i]["complete"]:
            continue
        tail = segs[i]["levels"][-1][0]["name"]
        for j in range(i + 1, len(segs)):
            hit = next((k for k, lv in enumerate(segs[j]["levels"])
                        if any(_prefix_match(tail, n["name"]) for n in lv)), None)
            if hit is not None:
                # the shared name itself is already the last level of i
                join[i] = (j, hit + 1, "shared_name")
                open_.remove(i)
                break

    def full(i, depth=0):
        if depth > 10:
            return None, []
        levels = list(segs[i]["levels"])
        methods = []
        if i in join:
            j, lvl, how = join[i]
            rest, m = full(j, depth + 1)
            if rest is None:
                return None, []
            if how == "shared_name":
                # keep the fuller spelling of the shared name
                shared = rest[lvl - 1] if lvl - 1 < len(rest) else None
                if shared and len(shared[0]["name"].split()) > len(levels[-1][0]["name"].split()):
                    levels[-1] = shared
            levels = levels + rest[lvl:]
            methods = [how] + m
        elif i != last and segs[i]["complete"]:
            methods = ["complete_segment"]
        elif i != last:
            return None, []
        return levels, methods

    routes, fragments = [], []
    for t in taliq:
        fragments.append([n for lv in t["levels"] for n in lv[:1]])
    for i, s in enumerate(segs):
        levels, methods = full(i)
        if levels is None:
            fragments.append([n for lv in s["levels"] for n in lv[:1]])
            continue
        for names in _expand(levels):
            how = methods[0] if methods else ("shared_name_taliq" if s.get("taliq_join") else "direct")
            if any(len(lv) > 1 for lv in levels):
                how = how + "+co_narrator" if how != "direct" else "co_narrator"
            routes.append({"names": names, "join": how})
            if len(routes) >= MAX_ROUTES:
                break
        if len(routes) >= MAX_ROUTES:
            break

    # primary route: the last segment, first co-narrator at each level (v0 shape)
    primary = next((r["names"] for r in routes if r["names"] and segs and
                    r["names"][0] is segs[last]["levels"][0][0]), routes[-1]["names"] if routes else [])
    last_span = max((n["span"][1] for lv in segs[last]["levels"] for n in lv), default=0)
    to_prophet = _reaches_prophet(itoks, last_span, mtoks)
    same_isnad = any(s["same_isnad"] for s in segs)
    return {"names": primary, "routes": routes, "fragments": fragments, "tahwil": tahwil,
            "same_isnad": same_isnad, "repaired": repaired, "to_prophet": to_prophet}


def _expand(levels):
    out = [[]]
    for lv in levels:
        out = [r + [n] for r in out for n in lv]
        if len(out) > MAX_ROUTES:
            out = out[:MAX_ROUTES]
    return out


def quote(isnad_text, matn_text, span):
    """The original (diacritized) words a name was read from."""
    words = (isnad_text or "").split() + (matn_text or "").split()
    s, e = span
    return " ".join(words[s:e])
