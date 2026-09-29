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
  `variation` (different wording), `spelling` (typos), `not_in_six_books`.
- `expect`: `exists` or `absent`.
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

## Reviewing a case

1. Open the case in `cases.json`. Check its `review.candidates` and search the
   corpus yourself.
2. Set `"status": "reviewed"`, put the chosen record ids in `relevant` (or leave
   it empty for a confirmed `absent`), and fill
   `"review": {"reviewer": "<name>", "date": "YYYY-MM-DD", "basis": "<why, with a source>"}`.
3. Run `python evaluation/build_cases.py`. It keeps reviewed cases and fills
   their `evidence`, then run the tests.

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
