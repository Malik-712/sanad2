# سجل التغييرات — Changelog

كل ما يُبنى فوق نسخة الأساس (v0، 28 سبتمبر 2026) يُسجَّل هنا مرحلةً مرحلة.
Everything built on top of the v0 baseline is recorded here, phase by phase.

قواعد المصادر التي تلتزمها كل المراحل: `.claude/skills/religious-sourcing/SKILL.md`.

---

## Phase 1 — Audit and fixes (2026-09-28)

### Isnad parser (`sanad_core/isnad.py`, rewritten)
The parser now works on tokens and keeps, for every name, the span of the
original diacritized words it was read from, so each name can be quoted.

- **تحويل (ح)**: every segment is parsed. A segment is joined to a later one
  only when the text says where: «كلاهما عن X» (previous segment),
  «كلهم / جميعا / كل هؤلاء عن X» (all open segments), or a name shared by
  both segments. A segment that already names the Prophet is a complete
  route. Anything else is kept as a *fragment* and not drawn. v0 kept only
  the last route.
- **Co-narrators joined by «و»** at one level each get their own route
  (v0 kept the first). «فلان أو فلان، شك فلان» keeps both, marked uncertain.
- **Noise is not a name**: narration after the chain («قال كان…», «لما…»),
  first-person and narrative verbs, wording notes («قال أحمد حدثنا وقال
  الآخران أخبرنا»), explanations («وهو ابن فلان», «يعني…»), the listener after
  «يحدّث أباه», the compiler's remarks («قال أبو عيسى…»), and text after the
  Prophet is named.
- New transmission words: حدثتني، أخبرتني، حدثتنا، سألت، لقيت، «رده إلى»، «قرأت على»، «كتب إليّ».
- «وحدثنا» in the middle of a chain starts a new route; «وقال فلان» / «وروى»
  (ta'liq) become fragments instead of being drawn as connected chains.
- «بهذا الإسناد»: completed from the preceding hadith in the same book at
  the first shared name (829 routes), marked uncertain, with a pointer to
  the hadith the names were read from.
- Relatives: «عن أبيه» → the father's name only when the name itself says
  it («X بن Y» → Y, keeping compounds such as «عبد الله»); otherwise
  «والد X», marked uncertain. «ابن X» is never used to infer a father.
  «أبي بن كعب» is no longer turned into «أبو بن كعب».
- Segmentation repair now also handles «أن أبا» + «هريرة…».
- `pipeline/chains.py` (shared by `build_data.py`) and
  `pipeline/reparse_chains.py` (re-parses `data/hadiths.json.gz` in place;
  no corpus or scikit-learn needed).

### Engine and API
- **Performance**: a 1,500-character query took 9.3 s (a denial-of-service
  risk on a 30 s function); now 0.56 s (alignment capped at 120 words and
  12 anchors, word-similarity cache).
- Auto mode treated any text starting with «ما» (e.g. «ما من مسلم…») as a
  topic search. Fixed.
- The tree draws **every route** of every narration. A route that does not
  name the Prophet after its last narrator is drawn with an "unlinked" edge
  and is not listed as a companion; a one-name cut route is not drawn
  (`incomplete`). Prefix merges are flagged (`merge: "prefix"`).
- **Provenance** (`sanad_core/provenance.py`): matn, isnad, source, grade
  and every narrator name now carry source, URL (the exact CSV file in the
  LK repository), verbatim quote, retrieval date, method and confidence.
  The dataset grade is flagged `attributed: false`.
- API: ids validated by pattern, book validated, at most 20 query fields,
  URL length cap, errors served with `Cache-Control: no-store`, security
  headers, `Content-Length`.
- `serve.py` binds to 127.0.0.1 by default (was 0.0.0.0), sends the same
  CSP and security headers as `vercel.json`, and serves client routes.
- `vercel.json`: CSP (no inline scripts), `X-Frame-Options`, `nosniff`,
  `Referrer-Policy`.
- `evaluation/run_eval.py` crashed on Windows consoles (cp1252). Fixed.

### Front end (minimal, before the Phase 2 rework)
- Escaped a missing attribute value; removed a `javascript:` link (blocked
  by the new CSP); malformed links no longer crash the router; a slow
  response can no longer overwrite a newer page.

### Tests
- `tests/test_isnad.py` (29 tests on real chains read by id from the corpus)
  and `tests/test_api.py` (15 tests). `python -m unittest discover -s tests`.
- `evaluation/parser_metrics.py`: corpus-wide parser metrics with a fixed
  noise list, so they are comparable across versions.

### Results (before → after)

| measure | v0 | Phase 1 |
|---|---|---|
| `run_eval.py` correct | 22/22 | 22/22 |
| said "exists" for a text not in the six books | 0 | 0 |
| worst-case query time (1,500 chars) | 9.3 s | 0.56 s |
| noise words parsed as narrator names | 1,155 | 3 |
| names with trailing noise («… أو», «… شك …») | 203 | 3 |
| routes per تحويل hadith | 1.00 | 2.22 |
| hadiths with several routes | 0 | 6,363 |
| total routes | 34,060 | 43,277 |
| same name twice in one route | 642 | 585 |
| hadiths with nothing parsed | 28 | 23 |
| hadiths with only a ta'liq/fragment (v0 drew these as connected chains) | — | 33 |
| bukhari-1 tree: routes / companions / المدار | 14 / 2 / يحيى بن سعيد الأنصاري | 14 / 1 / يحيى بن سعيد الأنصاري |

The bukhari-1 "second companion" in v0 was «سليمان بن منصور», a chain cut
by the automatic isnad/matn split (nasai-75). It is now reported as
incomplete instead of being drawn under the Prophet.
