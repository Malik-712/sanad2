"""Isnad-parser quality metrics over the whole corpus (data/hadiths.json.gz).

Works on both data formats: v0 (one `chain` per hadith) and v1 (`routes`).
The noise list below is fixed and independent of the parser, so the numbers
are comparable before and after a parser change. Run:

    python evaluation/parser_metrics.py
"""
import collections
import gzip
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sanad_core import engine  # noqa: E402

# Words that are never a narrator's name on their own. Collected from the v0
# output on 2026-09-28 (verbs, particles, wording notes); kept fixed on purpose.
NOISE_FIRST_WORDS = set("""
كان كانت كنا كنت لما اذا ثم جاء جاءنا ذكر زاد دخل دخلنا خرج خرجنا سال سالت سالنا سالني سالوا
بعث بعثني امر انت فينا بينا عندنا علينا اصحابنا بلغني يحدثنا حدثت حدثتني حدثتنا اخبرتني
فاخبرتني قلت فقلت قلنا اتينا اتانا خطبنا صلينا نهينا نهاني علمني راني ارسلني استعملني انزلت
حفظت فسالت حضرنا غزونا لقيني فذكرنا فلقيت فحدثت درست الاخران الاخرون ابا اباه
""".split())
TRAILING_NOISE = {"او", "شك", "باسناد", "مثل", "معناه", "رده", "كل", "هولاء", "بمعني"}


def routes_of(h):
    if "routes" in h:
        return [r["names"] for r in h["routes"]]
    return [h["chain"]] if h["chain"] else []


def main():
    d = engine.data()
    hs = d["hadiths"]
    m = collections.Counter()
    for h in hs:
        rs = routes_of(h)
        m["hadiths"] += 1
        m["hadiths_without_route"] += not rs
        m["hadiths_with_nothing_parsed"] += not rs and not h.get("fragments")
        m["hadiths_taliq_or_fragment_only"] += not rs and bool(h.get("fragments"))
        m["routes_total"] += len(rs)
        m["hadiths_with_several_routes"] += len(rs) > 1
        tahwil = h.get("chain_partial") or h.get("tahwil")
        if tahwil:
            m["tahwil_hadiths"] += 1
            m["tahwil_routes"] += len(rs)
        for names in rs:
            seen = []
            for n in names:
                m["names"] += 1
                ws = n["name"].split()
                if ws[0] in NOISE_FIRST_WORDS:
                    m["noise_names"] += 1
                if ws[-1] in TRAILING_NOISE or any(w in TRAILING_NOISE for w in ws[1:]):
                    m["names_with_trailing_noise"] += 1
                if n["name"] in seen:
                    m["same_name_twice_in_route"] += 1
                seen.append(n["name"])
    out = dict(m)
    out["noise_rate_per_1000_names"] = round(1000 * m["noise_names"] / max(1, m["names"]), 2)
    out["tahwil_routes_per_hadith"] = round(m["tahwil_routes"] / max(1, m["tahwil_hadiths"]), 2)
    t = engine.tree("bukhari-1")
    nodes = {n["key"]: n for n in t["nodes"]}
    out["bukhari-1_tree_routes"] = t["summary"]["routes"]
    out["bukhari-1_tree_companions"] = t["summary"]["companions"]
    out["bukhari-1_mudar"] = nodes[t["mudar"]]["label"] if t["mudar"] else None
    return out


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    print(json.dumps(main(), ensure_ascii=False, indent=2))
