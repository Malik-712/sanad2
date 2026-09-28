---
name: religious-sourcing
description: Mandatory rules for any change to Sanad that touches hadith text, grades, narrator names or facts, scholars' statements, or how they are displayed, stored, fetched or documented. Load before editing sanad_core/, api/, pipeline/, public/, data/ or docs about sources.
---

# Religious sourcing rules for Sanad

Sanad shows religious content. It must never become the author of that content.
These rules override convenience, design and completeness. If a rule and a
feature conflict, drop the feature and say so.

## 1. Never generate religious content

Do not generate, paraphrase, summarize, translate, "clean up" or infer:

- hadith text (matn) or chains (isnad)
- grades (صحيح، حسن، ضعيف، ...) or any verdict on a hadith
- narrator facts: full name, kunya, nisba, dates, tabaqa, teachers, students
- scholars' statements (jarh wa ta'dil, takhrij, commentary)

This applies to code, UI copy, placeholder or demo data, tests, docs and commit
messages. Test fixtures quote real text from the corpus verbatim, with its id.

Allowed: Sanad's own *mechanical* outputs, clearly labelled as such, e.g.
"match 87%", "3 routes pass through this name", "branching point (computed)".
These are never phrased as a scholarly judgment.

## 2. Every religious fact carries provenance

Anything shown in the UI that is religious content must carry all five fields:

| field | meaning |
|---|---|
| `source` | name of the source (e.g. "LK Hadith Corpus", "الدرر السنية — الموسوعة الحديثية") |
| `url` | a URL where a person can check it |
| `quote` | the exact short text it came from, verbatim, not normalized |
| `retrieved` | ISO date the data was obtained |
| `method` | how it was extracted (column name, API + parser, rule-based parse, match rule) |

Plus `confidence` whenever a match or parse is involved (`high` / `uncertain`,
and the numbers behind it). Use `sanad_core/provenance.py` to build these
records; do not hand-roll them. The UI renders them in the
"كيف حصلنا على هذه المعلومة؟" box.

## 3. Missing or uncertain → say so

If a fact is missing, or the match/parse is not high-confidence, show exactly:

    غير متوفر في المصدر

Never fill a gap from memory, from another narrator with a similar name, or
from a model. An uncertain match shows candidates and "غير مؤكد", never a pick.

## 4. Forbidden labels

- Sanad never labels a hadith "موضوع" or "متواتر" — not as a verdict state, a
  badge, a filter, a colour or a heading. "Not found in Sanad's sources" is not
  a judgment and must say so.
- Sanad never grades a narrator (ثقة، ضعيف، ...). Such words may appear only
  inside a verbatim quote that is attributed to a named scholar and a source.

## 5. Attribution of grades

A grade is shown as a quote attributed to its scholar and book, e.g.
المحدث: الألباني — المصدر: صحيح أبي داود — الرقم: ... — «...». A grade
with no known scholar is labelled "حكم غير منسوب في مجموعة البيانات" and is
never shown as if it were Sanad's own verdict.

## 6. External sources and access

- Use only access a source officially allows (published API, licence, or
  written permission). Check robots.txt and terms first; record the result in
  docs/PROVENANCE.md.
- If automated access is not permitted: stop, do not work around it (no
  browser-impersonating user agents, no Cloudflare bypass, no HTML scraping of
  pages the API does not cover). Report it.
- Rate-limit every request (at least 2 s between requests to one host),
  identify Sanad in the User-Agent, set timeouts, and cache results in data/
  with full provenance so each fact is fetched once.
- Status as of 2026-09-28: Dorar's official `dorar_api.json` (hadith search)
  is allowed and used for grade attribution. Dorar narrator biographies have
  no API and are not fetched. See docs/PROVENANCE.md.

## 7. Checklist before committing

- [ ] No new religious text was written by hand or by a model.
- [ ] Every new religious field shown has source, url, quote, retrieved, method.
- [ ] Missing data renders "غير متوفر في المصدر".
- [ ] No "موضوع"/"متواتر" as a Sanad label; no narrator grading.
- [ ] Any new source is listed in SOURCES.md and docs/PROVENANCE.md.
