"""Re-parse all isnads in data/hadiths.json.gz with the current parser.

The data file keeps the original isnad and matn text, so parser improvements
do not need the LK corpus or scikit-learn. Run:

    python pipeline/reparse_chains.py
"""
import gzip
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
from chains import build_chains, add_source_files, clean_fields  # noqa: E402

PATH = os.path.join(ROOT, "data", "hadiths.json.gz")


def main():
    t = time.time()
    with gzip.open(PATH, "rt", encoding="utf-8") as fh:
        recs = json.load(fh)
    print("'nan' placeholders emptied:", clean_fields(recs))
    add_source_files(recs)
    stats = build_chains(recs)
    with gzip.open(PATH, "wt", encoding="utf-8", compresslevel=9) as fh:
        json.dump(recs, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"re-parsed {len(recs)} isnads in {time.time() - t:.1f}s", stats,
          f"{os.path.getsize(PATH) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
