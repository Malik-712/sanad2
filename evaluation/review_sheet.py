"""Review sheet: check case labels in Excel and bring the decisions back.

    python evaluation/review_sheet.py export [--force]       # cases.json -> review_sheet.csv
    python evaluation/review_sheet.py fill review_sheet.csv   # candidates for new rows
    python evaluation/review_sheet.py import review_sheet.csv # decisions -> cases.json

The sheet is UTF-8 with BOM, so Excel opens the Arabic text correctly. Save it
from Excel as "CSV UTF-8". Commas or semicolons both work as separators.

This tool never writes a query, a label or a record choice. Every value it
imports was typed by a person in the sheet; the only things it adds are
mechanical: ids, dates, candidate lists (records that share words with the
query, copied verbatim from the corpus, to look at, not an answer) and the
word-for-word corpus check.

Labels are checked by the author against the source text; they are not
reviewed by a Sharia specialist (harness.REVIEW_SCOPE). Nothing here claims
otherwise.

Columns
  id          empty for a new row written by you; filled for existing cases
  category    exact, partial, variation, meaning, conflict, spelling,
              not_in_six_books (or "absent")
  split       dev (may be used for tuning) or test (held out). Empty on a new
              row means test. v0 cases stay dev (they set the thresholds).
  status      current status (read only)
  query       the text to search. For a new row: written by you.
  expect      exists or absent. Empty means: absent for not_in_six_books,
              exists for everything else.
  relevant    expected record ids (e.g. bukhari-1), separated by spaces
  candidates  read only: records to look at, with a short verbatim quote
  reviewer    empty means "Malik (author)"
  date        YYYY-MM-DD; empty means today
  basis       why this label, with a source (required to accept)
  decision    accept = apply this row; remove = delete a case you added;
              empty or skip = no change
  author      new rows: who wrote the query (empty means the reviewer)

Import is all or nothing: if one row has an error, nothing is written.
"""
import argparse
import csv
import datetime
import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness  # noqa: E402
from build_cases import CASES_FILE, reviewed_evidence  # noqa: E402
from corpus_check import words  # noqa: E402

SHEET_FILE = os.path.join(HERE, "review_sheet.csv")
COLUMNS = ["id", "category", "split", "status", "query", "expect", "relevant", "candidates",
           "reviewer", "date", "basis", "decision", "author"]
DEFAULT_REVIEWER = "Malik (author)"
QUOTE_WORDS = 12
V0_KIND = "v0_smoke"


class SheetError(Exception):
    pass


# ------------------------------------------------------------------ helpers
def short_quote(corpus, hid):
    """The first words of a record's matn, verbatim (not normalized)."""
    return " ".join(corpus.by_id[hid]["matn"].split()[:QUOTE_WORDS])


def fmt_records(corpus, ids):
    return " | ".join(f"{hid} «{short_quote(corpus, hid)}»" for hid in ids if hid in corpus.by_id)


def candidates_for_case(c, corpus):
    if c["relevant"]:
        quotes = {e["id"]: " ".join(e["quote"].split()[:QUOTE_WORDS]) for e in c.get("evidence", [])}
        return "expected: " + " | ".join(f"{hid} «{quotes.get(hid) or short_quote(corpus, hid)}»"
                                         for hid in c["relevant"] if hid in corpus.by_id)
    ids = [x["id"] for x in c.get("review", {}).get("candidates", [])]
    ids += [x["id"] for x in c.get("check", {}).get("closest_records", []) if x["id"] not in ids]
    return ("closest by shared words (not an answer): " + fmt_records(corpus, ids)) if ids else ""


def candidates_for_query(query, corpus):
    qw = words(query)
    if not qw:
        return "no Arabic words"
    cont = corpus.containing(qw)
    if cont:
        return "contains the words in order: " + fmt_records(corpus, cont[:8])
    ids = [x["id"] for x in corpus.closest(qw)]
    return ("no record has these words in order; closest by shared words (not an answer): "
            + fmt_records(corpus, ids)) if ids else "no record has these words in order"


def split_ids(s):
    return [x for x in re.split(r"[\s,;،؛|]+", s or "") if x]


def parse_date(s, today):
    s = (s or "").strip()
    if not s:
        return today
    m = re.fullmatch(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if not m:
        raise SheetError(f"date {s!r}: write it as YYYY-MM-DD (format the column as Text in Excel)")
    return datetime.date(*map(int, m.groups())).isoformat()


def human_id(category, query):
    key = " ".join(words(query)) or query.strip()
    return f"human-{category}-{hashlib.sha1(key.encode('utf-8')).hexdigest()[:8]}"


def expect_for(category):
    return "absent" if category == "not_in_six_books" else "exists"


# ------------------------------------------------------------------ read / write
def read_sheet(path):
    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            text = fh.read()
    except UnicodeDecodeError:
        raise SheetError(f"{path} is not UTF-8. In Excel use Save As -> 'CSV UTF-8 (Comma delimited)'.")
    head = text.split("\n", 1)[0]
    delim = ";" if head.count(";") > head.count(",") else ","
    rows = list(csv.DictReader(io.StringIO(text), delimiter=delim))
    missing = [c for c in ("id", "category", "query", "decision") if c not in (rows[0].keys() if rows else COLUMNS)]
    if missing:
        raise SheetError(f"{path}: missing columns {missing}")
    return [{k: (v or "").strip() for k, v in r.items() if k} for r in rows]


def write_sheet(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLUMNS})


def load_doc(path=CASES_FILE):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_doc(doc, path=CASES_FILE):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


# ------------------------------------------------------------------ commands
def export_rows(cases, corpus):
    rows = []
    for c in cases:
        rv = c.get("review", {})
        rows.append({"id": c["id"], "category": c["category"], "split": c.get("split", "dev"),
                     "status": c["status"], "query": c["query"], "expect": c["expect"],
                     "relevant": " ".join(c["relevant"]), "candidates": candidates_for_case(c, corpus),
                     "reviewer": rv.get("reviewer", ""), "date": rv.get("date", ""),
                     "basis": rv.get("basis", ""), "decision": "",
                     "author": c.get("origin", {}).get("author", "")})
    return rows


def fill_rows(rows, corpus):
    """Candidates for new rows (empty id, a query, no candidates yet)."""
    n = 0
    for r in rows:
        if not r.get("id") and r.get("query") and not r.get("candidates"):
            r["candidates"] = candidates_for_query(r["query"], corpus)
            n += 1
    return n


def apply_rows(cases, rows, corpus, today=None):
    """Apply accepted rows to a copy of cases. Returns (new cases, summary).
    Raises SheetError listing every bad row; nothing is applied then."""
    today = today or datetime.date.today().isoformat()
    cases = [json.loads(json.dumps(c)) for c in cases]
    by_id = {c["id"]: c for c in cases}
    errors, summary = [], {"accepted": 0, "added": 0, "removed": 0, "ignored": 0}
    remove = set()

    for line, r in enumerate(rows, 2):
        decision = r.get("decision", "").lower()
        if decision in ("", "skip"):
            summary["ignored"] += 1
            continue
        where = f"row {line} ({r.get('id') or 'new'})"
        try:
            if decision not in ("accept", "remove"):
                raise SheetError(f"decision {decision!r}: use accept, remove or leave it empty")
            cid = r.get("id", "")
            old = by_id.get(cid)
            if cid and old is None:
                raise SheetError(f"id {cid!r} is not in cases.json (leave id empty for a new row)")
            if decision == "remove":
                if not old or old.get("origin", {}).get("kind") != "human":
                    raise SheetError("only cases you added (origin human) can be removed")
                remove.add(cid)
                summary["removed"] += 1
                continue
            added = _accept(r, old, cases, by_id, corpus, today)
            summary["accepted"] += 1
            summary["added"] += added
        except SheetError as e:
            errors.append(f"{where}: {e}")
    if errors:
        raise SheetError("\n".join(errors))
    return [c for c in cases if c["id"] not in remove], summary


def _accept(r, old, cases, by_id, corpus, today):
    cat = r.get("category", "").lower()
    cat = harness.CATEGORY_ALIASES.get(cat, cat)
    if cat not in harness.CATEGORIES:
        raise SheetError(f"category {cat!r}: use one of {', '.join(harness.CATEGORIES)} (or absent)")
    query = r.get("query", "")
    if not query:
        raise SheetError("query is empty")
    if old is None and human_id(cat, query) in by_id:
        old = by_id[human_id(cat, query)]   # a new row imported before: update it
    human = old is None or old.get("origin", {}).get("kind") == "human"
    if old and not human and " ".join(query.split()) != " ".join(old["query"].split()):
        raise SheetError("the query of a generated case cannot be changed; add a new row instead")

    expect = r.get("expect", "").lower() or expect_for(cat)
    if expect != expect_for(cat):
        raise SheetError(f"expect {expect!r} does not fit category {cat!r} "
                         f"(not_in_six_books is absent, every other category exists)")
    relevant = split_ids(r.get("relevant"))
    unknown = [h for h in relevant if h not in corpus.by_id]
    if unknown:
        raise SheetError(f"unknown record ids {unknown}")
    if expect == "exists" and not relevant:
        raise SheetError("expect exists needs at least one record id in relevant")
    if expect == "absent":
        if relevant:
            raise SheetError("expect absent must have an empty relevant")
        cont = corpus.containing(words(query))
        if cont:
            raise SheetError(f"labelled absent, but these records contain the words in order: {cont[:5]}")
    if old and old["status"] == "auto" and sorted(relevant) != sorted(old["relevant"]):
        raise SheetError("relevant of an auto case is computed from the corpus; accept it as it is")

    basis = r.get("basis", "")
    if not basis:
        raise SheetError("basis is empty: say why, with a source")
    split = r.get("split", "").lower() or ("test" if human else old.get("split", "dev"))
    if split not in harness.SPLITS:
        raise SheetError(f"split {split!r}: use dev or test")
    if split == "test" and old and old.get("origin", {}).get("kind") == V0_KIND:
        raise SheetError("v0 cases were used to set the thresholds; they must stay in dev")
    reviewer = r.get("reviewer", "") or DEFAULT_REVIEWER
    review = {"reviewer": reviewer, "date": parse_date(r.get("date"), today), "basis": basis,
              "scope": harness.REVIEW_SCOPE}

    if old is None:
        cid = human_id(cat, query)
        c = {"id": cid, "origin": {"kind": "human", "author": r.get("author", "") or reviewer, "added": today}}
        cases.append(c)
        by_id[cid] = c
    else:
        c = old
        c.pop("check", None)
    c.update({"category": cat, "query": query, "expect": expect, "status": "reviewed", "split": split,
              "relevant": relevant, "review": review})
    reviewed_evidence(c, corpus)
    return old is None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--out", default=SHEET_FILE)
    e.add_argument("--force", action="store_true", help="overwrite an existing sheet")
    f = sub.add_parser("fill")
    f.add_argument("sheet")
    i = sub.add_parser("import")
    i.add_argument("sheet")
    a = ap.parse_args(argv)

    from corpus_check import Corpus
    try:
        if a.cmd == "export":
            if os.path.exists(a.out) and not a.force:
                raise SheetError(f"{a.out} exists and may hold rows you have not imported; use --force to overwrite")
            doc = load_doc()
            write_sheet(a.out, export_rows(doc["cases"], Corpus()))
            print(f"{len(doc['cases'])} cases written to {a.out}")
        elif a.cmd == "fill":
            rows = read_sheet(a.sheet)
            n = fill_rows(rows, Corpus())
            write_sheet(a.sheet, rows)
            print(f"candidates filled for {n} new rows in {a.sheet}")
        else:
            doc = load_doc()
            cases, s = apply_rows(doc["cases"], read_sheet(a.sheet), Corpus())
            doc["cases"] = cases
            save_doc(doc)
            print(f"accepted {s['accepted']} (new {s['added']}), removed {s['removed']}, "
                  f"unchanged {s['ignored']}. Now run: python -m unittest discover -s tests")
    except SheetError as err:
        print(f"Nothing written.\n{err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    sys.exit(main())
