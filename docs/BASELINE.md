# نسخة الأساس السابقة للتحدي — Pre-challenge baseline

> **مسودة (30 سبتمبر 2026).** تُستكمل في **3 أكتوبر 2026** آخر شيء قبل أيام التحدي:
> تُحفظ لقطة المقاييس في `evaluation/results/`، ويُنشأ الوسم `challenge-baseline`،
> وتُملأ الخانات المعلّمة «يُملأ في 3 أكتوبر».
>
> **Draft (30 Sep 2026).** Finalised on **3 Oct 2026**, as the last step before the
> challenge days: the metric snapshot is saved in `evaluation/results/`, the tag
> `challenge-baseline` is created, and every field marked «يُملأ في 3 أكتوبر» is filled.

أيام التحدي الرسمية: **4 أكتوبر 09:00 – 6 أكتوبر 23:59 (بتوقيت الرياض)**. لا يُحكَّم إلا ما
أُنجز فيها. هذا الملف يوثّق ما كان موجودًا **قبلها**، حتى يُفصل بوضوح عمّا يُبنى في أيام التحدي.

---

## 1. الوسم — The tag

| | |
|---|---|
| الوسم (tag) | `challenge-baseline` |
| الإيداع (commit) | يُملأ في 3 أكتوبر |
| التاريخ | يُملأ في 3 أكتوبر |
| الرابط | `https://github.com/Malik-712/sanad/tree/challenge-baseline` |

كل ما في المستودع حتى هذا الوسم هو نسخة الأساس. كل إيداع بعده في أيام التحدي تبدأ رسالته بـ
`[challenge-day]`، ويُسجَّل في قسم «Challenge days» في [CHANGELOG.md](../CHANGELOG.md).

ملاحظة: رسالة الإيداع `6beec79` (28 سبتمبر) تقول "challenge-day work"، وهذا وصف خاطئ؛ ذلك
العمل جزء من نسخة الأساس. لم يُعَد كتابة سجل git.

## 2. ما كان موجودًا قبل 4 أكتوبر — What existed before 4 Oct

التفصيل الكامل في [CHANGELOG.md](../CHANGELOG.md) (الأقسام «Pre-challenge baseline»).

| التاريخ | ما أُضيف |
|---|---|
| 28 سبتمبر (v0) | بحث التحقق (BM25 مع تحمّل الأخطاء الإملائية والتطابق المرتّب)، ثلاث حالات للنتيجة، إبراز الفروق، قراءة الإسناد، شجرة الإسناد مع نقطة التفرّع، تقييم أولي |
| 28 سبتمبر (المرحلة 1) | مراجعة الكود وإصلاحه؛ قارئ أسانيد جديد (التحويل، الرواة المعطوفون)؛ موضع كل اسم في النص؛ اختبارات |
| 28 سبتمبر (المرحلة 2) | الهوية البصرية وإعادة بناء الصفحات |
| 28 سبتمبر (المرحلة 3) | شجرة الإسناد التفاعلية المطوّرة |
| 28 سبتمبر (المرحلة 4) | أحكام منسوبة من واجهة الدرر السنية الرسمية؛ التراجم لم تُجلب (الوصول الآلي غير مسموح) |
| 28 سبتمبر (المرحلة 5) | تقرير المصادر `docs/PROVENANCE.md` وصفحة `/about/sources` |
| 29 سبتمبر (المرحلة 6) | إعادة تصميم الواجهة على نظام تصميم واحد، والشعار |
| 29 سبتمبر | أداة تقييم البحث `evaluation/` واختبار «لا موجود خطأً» |
| 30 سبتمبر – 3 أكتوبر | متابعة المراجعة: شعار «لكل حديث إسناد»، تصحيح وصف الجدول الزمني، هذا الملف |

**ما لم يكن موجودًا في نسخة الأساس** (بصراحة): لا نموذج تضمين ولا بحث بالمعنى، ولا نموذج
تعلّم آلي في مسار التشغيل. البحث BM25 + توسيع إملائي بالمقاطع الحرفية + تطابق مرتّب، والحالة
تُحدَّد بعتبات مضبوطة يدويًا (`sanad_core/engine.py`).

### البيانات — Data

- `data/hadiths.json.gz`، `data/families.json.gz`، `data/search_index.json.gz`: مبنية من
  مدونة LK للحديث بـ `pipeline/build_data.py` (الكتب الستة).
- `data/dorar_grades.json.gz`: أحكام مخزنة من واجهة الدرر السنية الرسمية.
- `data/lk_files.json`: قائمة ملفات المدونة من GitHub API.

### الاختبارات — Tests

| | |
|---|---|
| عدد اختبارات الوحدة | يُملأ في 3 أكتوبر (79 في 30 سبتمبر) |
| حالات التقييم | يُملأ في 3 أكتوبر (76 في 30 سبتمبر، منها 8 «غير موجود») |
| «موجود» الخاطئ | يُملأ في 3 أكتوبر (0 من 8 في 30 سبتمبر) |

## 3. لقطة المقاييس — Metrics snapshot

تُحفظ في 3 أكتوبر بهذه الأوامر، وتُربط هنا:

```bash
python -m unittest discover -s tests
python evaluation/run_eval.py --json > evaluation/results/baseline-2026-10-03.json
python evaluation/parser_metrics.py > evaluation/results/parser-baseline-2026-10-03.json
```

- تقييم البحث: [`evaluation/results/baseline-2026-10-03.json`](../evaluation/results/baseline-2026-10-03.json) — يُملأ في 3 أكتوبر
- مقاييس قارئ الأسانيد: [`evaluation/results/parser-baseline-2026-10-03.json`](../evaluation/results/parser-baseline-2026-10-03.json) — يُملأ في 3 أكتوبر

## 4. حقوق الأطراف الثالثة — Third-party rights

التفصيل في [SOURCES.md](../SOURCES.md) و[docs/PROVENANCE.md](PROVENANCE.md).

| المكوّن | الحالة |
|---|---|
| مدونة LK للحديث (LK Hadith Corpus) | لا يوجد ملف ترخيص في مستودعها؛ يطلب المؤلفون الاستشهاد بورقتين (مذكورتان في SOURCES.md وفي `/about/sources`). **إذن إعادة النشر والعرض لم يُؤكَّد بعد:** طُلب من المؤلفة ولم يصل رد حتى الآن (تاريخ الطلب يُملأ في 3 أكتوبر؛ السجل في [`docs/permissions/lk-corpus.md`](permissions/lk-corpus.md)). |
| الدرر السنية — واجهة الموسوعة الحديثية الرسمية | واجهة منشورة لأصحاب المواقع؛ تُعرض النتائج منسوبة ومع رابط. طلبات محدودة السرعة وتعرّف نفسها. التراجم لم تُجلب. |
| مكتبات الواجهة (Cytoscape.js، dagre، cytoscape-dagre، Tabler Icons) | MIT |
| الخطوط (Amiri، Readex Pro، Jost) | SIL Open Font License 1.1 |
| أدوات البناء (numpy، scikit-learn) | BSD-3-Clause؛ في بناء البيانات فقط، لا في الخادم |
| كود سند | MIT (`LICENSE`) |

---

## English summary

Sanad's pre-challenge baseline is everything in the repository up to the git tag
`challenge-baseline` (v0 on 28 Sep 2026, phases 1–6 and the evaluation harness,
and documentation fixes up to 3 Oct). It was built **before** the official
challenge days (4–6 Oct 2026). The baseline has no embedding model, no semantic
search and no learned model at runtime: search is BM25 + trigram spelling
expansion + ordered word alignment with hand-set thresholds. Work done during
the challenge days is listed separately in the "Challenge days" section of
`CHANGELOG.md`, and every such commit starts with `[challenge-day]`. The metric
snapshot files above and the third-party rights table (LK Hadith Corpus
permission status, Dorar official API, MIT libraries, OFL fonts) complete the
disclosure.
