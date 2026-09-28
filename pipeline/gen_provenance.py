"""Generate docs/PROVENANCE.md from sanad_core/sources.py. Run:

    python pipeline/gen_provenance.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sanad_core.sources import catalog  # noqa: E402

STATUS = {"used": "مستخدم", "not_used": "غير مستخدم", "derived": "مشتق"}


def main():
    c = catalog()
    names = {s["id"]: s["name"] for s in c["sources"]}
    out = ["# مصادر البيانات وطريقة أخذها — Provenance", "",
           "> مولّد تلقائيًا من `sanad_core/sources.py` بالأمر `python pipeline/gen_provenance.py`. لا تعدّله يدويًا.", "",
           "كل معلومة دينية يعرضها سند معها: المصدر، والرابط، والنص الذي أُخذت منه حرفيًا، وتاريخ الأخذ، وطريقة الاستخراج، "
           "ودرجة الثقة حين توجد مطابقة أو قراءة آلية. تظهر في الواجهة في صندوق «كيف حصلنا على هذه المعلومة؟».", "",
           "القواعد التي تحكم ذلك: `.claude/skills/religious-sourcing/SKILL.md`.", "", "## المصادر", ""]
    for s in c["sources"]:
        out += [f"### {s['name']}", "",
                f"- **الحالة:** {STATUS.get(s['status'], s['status'])}",
                f"- **الرابط:** {s['url']}",
                f"- **ما أخذنا:** {s['taken']}",
                f"- **كيف استخرجناه:** {s['how']}",
                f"- **تاريخ الأخذ:** {s['retrieved']}",
                f"- **الترخيص:** {s['license']}"]
        if s.get("notes"):
            out.append(f"- **ملاحظات:** {s['notes']}")
        out.append("")
    out += ["## كل حقل يُعرض ومن أين جاء", "", "| الحقل | المصدر | الطريقة | في الـ API |", "|---|---|---|---|"]
    for field, src, how, key in c["fields"]:
        out.append(f"| {field} | {names[src]} | {how} | `{key}` |")
    a = c["dorar_access"]
    out += ["", "## فحص الوصول إلى الدرر السنية", "",
            f"- تاريخ الفحص: {a['checked']}",
            f"- robots.txt: `{a['robots']}`",
            f"- الواجهة الرسمية: `{a['api']}` (التوثيق: {a['api_doc']})",
            f"- التراجم: {a['tarajem']}",
            "- الطلبات تعرّف نفسها باسم سند، ولا تنتحل متصفحًا، ولا تتجاوز أي حماية.", "",
            "## المخاطر المفتوحة", ""]
    out += [f"- {r}" for r in c["risks"]]
    path = os.path.join(ROOT, "docs", "PROVENANCE.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print("wrote", path)


if __name__ == "__main__":
    main()
