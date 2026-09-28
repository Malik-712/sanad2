"""Build Sanad's data files from the LK Hadith Corpus.

Usage:
    git clone --depth 1 https://github.com/ShathaTm/LK-Hadith-Corpus /tmp/lk
    python pipeline/build_data.py /tmp/lk

Outputs (in data/):
    hadiths.json.gz       one record per hadith (original text kept for display)
    search_index.json.gz  BM25 inverted index over the normalized matn
    families.json.gz      for each hadith, the most similar matns (same hadith
                          in other books / other routes), with a similarity score
"""
import collections
import csv
import glob
import gzip
import json
import os
import re
import sys

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sanad_core.arabic import normalize, tokens, char_ngrams  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
from chains import build_chains  # noqa: E402

BOOKS = {
    "Bukhari": ("bukhari", "صحيح البخاري", "البخاري"),
    "Muslim": ("muslim", "صحيح مسلم", "مسلم"),
    "AbuDaud": ("abudawud", "سنن أبي داود", "أبو داود"),
    "Tirmizi": ("tirmidhi", "جامع الترمذي", "الترمذي"),
    "Nesai": ("nasai", "سنن النسائي", "النسائي"),
    "IbnMaja": ("ibnmajah", "سنن ابن ماجه", "ابن ماجه"),
}
BOOK_ORDER = list(BOOKS)

# A matn that only refers back to a previous one ("بمثله", "نحوه", "بهذا الإسناد").
REFERS_BACK = re.compile(r"(بمثله|مثله|بنحوه|نحوه|بمعناه|بهذا الاسناد|بهذا الحديث|بمثل حديث|نحو حديث|مثل حديث)")


def chapter_num(path):
    m = re.search(r"Chapter(\d+)\.csv$", path)
    return int(m.group(1)) if m else 0


def load(lk_dir):
    records = []
    for book in BOOK_ORDER:
        files = sorted(glob.glob(os.path.join(lk_dir, book, "*.csv")), key=chapter_num)
        seen = collections.Counter()
        for f in files:
            with open(f, encoding="utf-8-sig") as fh:
                for r in csv.DictReader(fh):
                    code, title, compiler = BOOKS[book]
                    num = re.sub(r"\.0$", "", (r.get("Hadith_number") or "").strip())
                    seen[num] += 1
                    hid = f"{code}-{num}" + (f"-{seen[num]}" if seen[num] > 1 else "")
                    records.append({
                        "id": hid,
                        "book": code,
                        "book_title": title,
                        "compiler": compiler,
                        "number": num,
                        "chapter": (r.get("Chapter_Arabic") or "").strip(),
                        "section": (r.get("Section_Arabic") or "").strip(),
                        "isnad": (r.get("Arabic_Isnad") or "").strip(),
                        "matn": (r.get("Arabic_Matn") or "").strip(),
                        "comment": (r.get("Arabic_Comment") or "").strip(),
                        "grade": (r.get("Arabic_Grade") or "").strip(),
                        "gold_segmentation": book == "Bukhari",
                        "src": f"{book}/{os.path.basename(f)}",
                    })
    return records


def build(lk_dir, out_dir):
    recs = load(lk_dir)
    print("hadiths:", len(recs))

    # --- chains (see pipeline/chains.py) -------------------------------------
    for r in recs:
        nm = normalize(r["matn"])
        r["nm"] = nm
        r["refers_back"] = bool(REFERS_BACK.search(nm)) and len(nm.split()) < 25
    print("chains:", build_chains(recs))

    # --- search index (BM25 postings over matn tokens) ----------------------
    postings = collections.defaultdict(list)
    dl = []
    for i, r in enumerate(recs):
        toks = tokens(r["matn"])
        dl.append(len(toks))
        for t, c in collections.Counter(toks).items():
            postings[t].extend([i, c])
    index = {"N": len(recs), "avgdl": float(np.mean(dl)), "dl": dl, "post": postings}
    print("vocab:", len(postings))

    # --- families: similar matns (char 3-gram TF-IDF cosine) -----------------
    vec = TfidfVectorizer(analyzer=char_ngrams, sublinear_tf=True, min_df=2)
    X = vec.fit_transform([r["matn"] for r in recs])
    families = []
    K, MIN = 40, 0.30
    for s in range(0, X.shape[0], 1500):
        sims = (X[s:s + 1500] @ X.T).toarray()
        for row_i, row in enumerate(sims):
            i = s + row_i
            row[i] = 0
            top = np.argpartition(-row, K)[:K]
            top = top[np.argsort(-row[top])]
            families.append([[int(j), round(float(row[j]), 3)] for j in top if row[j] >= MIN])
        print("families", min(s + 1500, X.shape[0]), "/", X.shape[0], flush=True)

    # hadiths that only say "بمثله" inherit the previous hadith in the same book
    for i, r in enumerate(recs):
        if r["refers_back"] and i > 0 and recs[i - 1]["book"] == r["book"]:
            r["refers_to"] = recs[i - 1]["id"]

    os.makedirs(out_dir, exist_ok=True)
    keep = ["id", "book", "book_title", "compiler", "number", "chapter", "section", "isnad", "matn",
            "comment", "grade", "gold_segmentation", "src", "chain", "chain_partial", "chain_repaired",
            "routes", "fragments", "tahwil", "same_isnad", "to_prophet", "nm", "refers_to"]
    slim = [{k: r[k] for k in keep if k in r} for r in recs]

    def dump(name, obj):
        path = os.path.join(out_dir, name)
        with gzip.open(path, "wt", encoding="utf-8", compresslevel=9) as fh:
            json.dump(obj, fh, ensure_ascii=False, separators=(",", ":"))
        print(name, round(os.path.getsize(path) / 1e6, 1), "MB")

    dump("hadiths.json.gz", slim)
    dump("search_index.json.gz", index)
    dump("families.json.gz", families)


if __name__ == "__main__":
    build(sys.argv[1], os.path.join(ROOT, "data"))
