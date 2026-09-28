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

---

## Phase 2 — Visual identity (2026-09-28)

### Identity
- **One idea, rubrication.** In hadith manuscripts the transmission words
  were written in red ink so the chain stood out. Sanad's rubric red
  (`--rubric`) is used only for transmission words, the chain thread and the
  mark. Verdicts never use red: "not found" is not a judgment.
- **Mark:** the three teeth of «س» drawn as three narrator nodes on one
  baseline; the first node in rubric. `public/favicon.svg` adapts to dark mode.
- **Type:** Amiri for all source text (best tashkeel rendering), Readex Pro
  for the interface. Type scale 13–52 px (ratio 1.25), 4 px spacing scale.
- **Colour tokens** for light and dark (`prefers-color-scheme`, plus a manual
  switch: system / light / dark, remembered per browser). Every text colour
  pair passes WCAG AA; lowest 5.42:1 (light), 6.9:1 (dark).
- Components: buttons, segmented control, verdict, result, provenance box
  («كيف حصلنا على هذه المعلومة؟»), vertical and horizontal chains, notes,
  facts list, tree side panel, legend.

### Pages (all rebuilt, RTL, mobile first)
- Clean URLs (`/search`, `/h/:id`, `/tree/:id`, `/about`, `/about/sources`);
  old `#/` links still work. ES modules, no build step.
- **Home:** the input, texts to try, and a real isnad (Bukhari 1) read live
  from the API with its transmission words rubricated and its narrators lifted
  into a chain: the one load animation, off under reduced motion.
- **Results:** verdict, source citation, word diff with legend, match meter
  (labelled as a computation), unattributed grade tagged as such.
- **Hadith page:** matn, rubricated isnad, every route (compact when there are
  several), fragments, notes on automatic segmentation, source panel, grade,
  other narrations, link to the tree. Provenance box on every field.
- **Tree:** restyled; legend explains every symbol (full rework in Phase 3).
- **About:** rewritten; states what Sanad does not do.
- Skip link, visible focus, `aria-current` in navigation, `aria-live` results,
  reduced motion respected, no horizontal scroll at 390 px (checked with
  Playwright on every page, desktop and mobile, light and dark).

### Data fixes found while reviewing screenshots
- The corpus CSVs store empty cells as the string "nan" (a pandas missing
  value). 30,401 fields were shown as text, e.g. a comment reading «nan».
  They are now empty and display «غير متوفر في المصدر» (`clean_fields` in
  `pipeline/chains.py`).
- 4 hadiths carry an unattributed dataset grade containing «موضوع» or
  «متواتر». Sanad does not show these words unless attributed to a named
  scholar, so these grades are withheld with an explanation.

### Security
- CSP keeps `script-src 'self'` (no inline scripts; the theme is applied by
  `/js/theme.js`). `style-src` allows `'unsafe-inline'` because the vendored
  Cytoscape sets inline styles.

---

## Phase 3 — A stronger isnad tree (2026-09-28)

- **Opens large and clear:** if the whole tree fits at a readable zoom
  (≥ 0.85) it is fitted; otherwise it opens at that zoom with the Prophet at
  the top and the view centred on the branching point (المدار).
- **Full screen** (button or F; Esc to leave), **zoom in / out / fit**
  (buttons or + − 0), **minimap** (click to jump; hidden below 600 px).
- **Find a narrator in the tree:** Arabic-normalized search over names and
  their variant spellings, keyboard navigable (combobox); the hit is centred,
  outlined in blue and its routes are shown.
- **Filters:** all companions, one companion (with route counts), the
  companion with the most routes, by book, the two Sahihs only, the shortest
  chain only, minimum matn similarity. The selected hadith always stays.
- **Kept:** المدار highlight (toggle), focus mode on a narrator (routes through
  it; the rest fades), dashed borders for uncertain merges.
- **Compare the wording of two routes:** word diff between their matns
  (new `action=compare`, `engine.compare_matn`; both texts kept verbatim,
  compared after normalization); the two routes are drawn in red and green.
- **Export PNG** (full tree, 2×) and a **shareable deep link**: filters,
  focused narrator and compared routes live in the URL
  (`?comp=&books=&sahih=1&short=1&sim=&mudar=0&focus=&cmp=`).
- **Legend** explains every symbol, including focus, search hit and
  comparison colours. **Routes as text** list for screen readers.
- Fixes: Arabic labels were clipped. Cytoscape measured them before the web
  font loaded and drew centred text shifted under the inherited RTL
  direction; labels are now measured by Sanad and the canvas is LTR (Arabic
  still shapes correctly).
- Checked with an interactive Playwright script: 17 checks (search, filters,
  deep-link restore, compare, full screen, PNG, share, minimap, mobile
  overflow), no page errors.

---

## Phase 4 — Dorar (الدرر السنية) (2026-09-28)

### Access investigation (done first)
| check | result |
|---|---|
| `https://dorar.net/robots.txt` | `User-agent: * / Disallow:` (nothing disallowed) |
| Official API | Yes: `https://dorar.net/dorar_api.json?skey=…`, published in article 389 («خدمة واجهة الموسوعة الحديثية API») for sites to show hadith-encyclopedia search results. Returns HTML inside JSON: text, الراوي، المحدث، المصدر، الصفحة أو الرقم، خلاصة حكم المحدث. |
| Terms of use | No terms page found; the footer says «جميع الحقوق محفوظة لمؤسسة الدرر السنية». |
| Narrator biographies | **No API.** Only HTML pages (`/hadith/tarajem`, «تراجم المحدثين»). The site serves Cloudflare's bot-challenge script, and a third-party wrapper project reports (issue #29, 2026-05) that Cloudflare protection stopped its scraping. |
| Honest user agent | The API answers `Sanad/1.0 (…)` normally; no impersonation needed. |

**Decision.** Grade attribution uses the official API only. **Narrator
profiles from Dorar were stopped**, as instructed: automated access to
biographies is not offered, the pages are all-rights-reserved and protected
against bots, and Sanad does not work around that.

### Built
- `sanad_core/dorar.py`: official-API client. Identifies itself (`Sanad/1.0`),
  15 s timeout, at least 2.5 s between requests (process-wide lock), parses
  only the fields the API returns, verbatim. Cached: `data/dorar_grades.json.gz`
  (committed, built by `pipeline/fetch_dorar_grades.py`) and a git-ignored
  runtime cache. `SANAD_DORAR_LIVE=0` disables network access.
- **Matching** a Dorar result to a narration: `same_source` (the book's own
  entry, same number) → high; `same_text` (≥ 80 % of words in order, comparable
  lengths) → high; anything weaker, a different number in the same book, or a
  short excerpt → «غير مؤكد» with the numbers, never picked silently. Every
  item stores confidence and the matching method.
- **Hadith page:** «الحكم منسوبًا إلى قائله» shows each attribution with Dorar's
  own labels (المحدث، المصدر، الصفحة أو الرقم، خلاصة حكم المحدث) and the verdict
  verbatim, plus its provenance box and a link to the same search on Dorar.
  Verdicts are not rewritten into «صححه فلان» (that would be a paraphrase).
  The unattributed dataset grade moves into a collapsed note when attributed
  grades exist.
- **Narrator profile** (tree): only what the isnad texts show: the name as
  written and its variants, teachers and students *within this tree* (read
  from the chains, labelled as such), and every biographical field (full
  name, kunya, nisba, birth, death, tabaqa, scholars' statements) as
  «غير متوفر في المصدر» with the reason.
- Prefetch: 56 queries (66 hadiths: the evaluation's existing texts, their
  narrations and demo hadiths). One transient connection error mid-run; one
  diagnostic request showed HTTP 200 and no Cloudflare mitigation, and the
  run was resumed once. 63/66 hadiths have attributions, 48 with a
  high-confidence match, 13 matched to the book's own entry and number.
- `tests/test_dorar.py`: 8 offline tests (parser on a real two-result API
  response, attribution, confidence rules, policy constants).

---

## Phase 5 — Provenance report (2026-09-28)

- Every religious field and every narrator-profile field has an expandable
  «كيف حصلنا على هذه المعلومة؟» box: source (linked), the exact quote,
  retrieval date, extraction method and, where a parse or match is involved,
  confidence with its numbers. Missing fields say «غير متوفر في المصدر» and the
  box says why.
- `sanad_core/sources.py`: one catalog of every data source (LK corpus, Dorar
  API, Dorar biographies — not used, Sanad's parser output, libraries, fonts),
  every field shown and where it comes from, the Dorar access record, and the
  open risks.
- `docs/PROVENANCE.md` is generated from it (`python pipeline/gen_provenance.py`);
  a test fails if the file is stale or if an API provenance key is undocumented.
- `/about/sources` page (API `action=sources`) renders the same catalog.
- Copy fix: the spelling note said «صحّحنا الإملاء» when a word simply does not
  occur in the six books (e.g. «الصين»). It now says the word was not found
  and which nearest word was searched.
- Tests: 56 (was 44 after Phase 1).
