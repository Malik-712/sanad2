# Search evaluation

Measures how well `engine.search` finds a pasted text in the six books. There is
no model and no embedding anywhere in this folder: each case's expected records
are either the records that contain the query **word for word**, or records a
named human reviewer chose.

```
python evaluation/build_cases.py     # rebuild cases.json (deterministic)
python evaluation/run_eval.py        # report; -v for every case, --json for tools
python -m pytest tests/test_eval.py  # regression gate (also part of the full suite)
```

## Files

| file | what it is |
|---|---|
| `cases.json` | all cases (generated; human reviews are kept on rebuild) |
| `v0_smoke_cases.json` | the original 22 texts and their exists/absent labels, unchanged |
| `build_cases.py` | builds `cases.json` from the v0 texts and a fixed corpus sample |
| `corpus_check.py` | the word-for-word check, separate from the search engine |
| `harness.py` | runs the cases and computes the metrics |
| `thresholds.json` | the floors the tests enforce |
| `run_eval.py` | the readable report |
| `review_sheet.py` | export cases to a CSV for Excel, and import the decisions |

## Case format

```json
{
 "id": "partial-bukhari-420",
 "category": "partial",
 "query": "مِنَ الثَّنِيَّةِ إِلَى مَسْجِدِ بَنِي زُرَيْقٍ ...",
 "expect": "exists",
 "status": "auto",
 "relevant": ["bukhari-420", "bukhari-2866"],
 "evidence": [{"id": "bukhari-420", "source": "...", "url": "...", "quote": "...", "retrieved": "...", "method": "..."}],
 "origin": {"kind": "corpus_sample", "record": "bukhari-420", "rule": "..."}
}
```

- `category`: `exact` (the whole matn), `partial` (a run of words from it),
  `variation` (different wording), `spelling` (typos), `not_in_six_books`
  (texts not in the six books; the review sheet also accepts `absent`),
  and two categories written by a person, never generated:
  `meaning` (a description or paraphrase of a hadith) and `conflict` (a
  hadith whose attributed grades differ between scholars; today it is scored
  as a search case like the others).
- `expect`: `exists` or `absent` (`absent` only for `not_in_six_books`).
- `split`: `dev` (may be used for tuning) or `test` (held out: never used for
  tuning or training). Test cases must be `reviewed`. The v0 cases set the
  thresholds, so they stay in `dev`. The floors in `thresholds.json` apply to
  `dev` only; false "exists" must be 0 on every case.
- `status`:
  - `auto`: `relevant` is exactly the set of records whose matn contains the
    query's words in order (a و or ف attached to the first word is accepted).
    The tests re-check this against the corpus on every run.
  - `needs_review`: nobody has decided the expected records. `relevant` is
    empty. The case counts only for the exists/absent verdict. `review.candidates`
    lists records that share the most words, **to look at, not an answer**.
  - `reviewed`: a human chose `relevant` (see below).
- `evidence`: one provenance record per expected record. The quote is the
  record's original words, copied as they are.
- `origin.label_source` (v0 cases): the exists/absent label comes from the v0
  smoke set as written, not from this harness.
- Spelling cases also carry `clean_query` (the words before the typos) and
  `typos` (each change and the rule that made it). The typos are mechanical
  test input, not a text shown to anyone.

## Who checks the labels

Sanad has one team member. Reviewed labels are **checked by the author
(Malik) against the source text; they are not reviewed by a Sharia
specialist.** Every reviewed case stores this in `review.scope`, the report
prints it, and a test fails if a reviewed case says anything else.

## Reviewing cases and adding your own (review sheet)

```
python evaluation/review_sheet.py export                    # -> evaluation/review_sheet.csv (git-ignored)
# open it in Excel; add your rows; save as "CSV UTF-8"
python evaluation/review_sheet.py fill evaluation/review_sheet.csv    # candidates for your new rows
python evaluation/review_sheet.py import evaluation/review_sheet.csv  # apply rows with decision=accept
python -m unittest discover -s tests
```

- **Existing case:** check `candidates`, put the record ids in `relevant`
  (empty for `absent`), write `basis` (why, with a source), set
  `decision` = `accept`. `reviewer` defaults to "Malik (author)", `date` to
  today.
- **New case** (meaning queries, absent texts, conflict cases): add a row with
  an empty `id`, your `category` and `query`. The tool never writes these; the
  meaning queries and the absent list are written by the author. Run `fill`
  to see candidate records (verbatim short quotes, to look at, not an
  answer), then fill `relevant`, `basis`, `decision` = `accept` and import.
  New rows get the id `human-<category>-<hash>`, `origin.kind` = `human` and
  split `test` unless you write `dev`. `decision` = `remove` deletes a case
  you added.
- The import is all or nothing and refuses, among others: an `absent` text
  that a record contains word for word, `exists` without records, unknown
  record ids, an empty `basis`, a v0 case in `test`, a changed query on a
  generated case.
- `build_cases.py` keeps every reviewed case and every case you added.

Target for the held-out `test` split: 100 reviewed cases — at least 30
`meaning`, 40 `not_in_six_books`, 15 `variation`, the rest
exact / partial / spelling / conflict. `python evaluation/run_eval.py --split test`
shows them alone. Training data for a learned model (plan T12) goes in the
paths listed in `harness.TRAINING_FILE_GLOBS`; a test fails if a test case or
one of its expected records appears there.

## What the numbers mean

| metric | meaning |
|---|---|
| recall@k | the expected record is among the first k results |
| MRR | mean of 1 / rank of the first expected record (0 if not in the top 10) |
| verdict precision | of the texts Sanad said exist, the share that do |
| verdict recall | of the texts that exist, the share Sanad said exist |
| top-1 precision | of ranked cases Sanad said exist, the share whose first result is expected |
| false "exists" | absent texts Sanad said exist. **Must be 0**: tests and `run_eval.py` fail otherwise |

Ranking metrics use only `auto` and `reviewed` cases. Because `auto` cases count
only word-for-word records as expected, a result that is the same hadith in
other words counts as a miss, so the ranking numbers are a lower bound.
