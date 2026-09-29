"""The catalog of every data source Sanad uses, and every field it shows.

Single source of truth for docs/PROVENANCE.md (pipeline/gen_provenance.py)
and the /about/sources page (API action=sources). Edit here, then run
`python pipeline/gen_provenance.py`.
"""
from . import provenance as prov
from . import dorar

SOURCES = [
    {
        "id": "lk",
        "name": prov.LK_NAME,
        "url": prov.LK_REPO,
        "status": "used",
        "taken": "نصوص الكتب الستة بالعربية (34,088 حديثًا): المتن، والإسناد مفصولًا عنه، والكتاب والباب والرقم، "
                 "والتعليق، والحكم كما في المدونة دون ذكر قائله.",
        "how": "نسخة من المستودع (ملفات CSV لكل كتاب وباب)، تُقرأ بـ pipeline/build_data.py كما هي. "
               "الخلايا الفارغة التي كُتبت «nan» تُعامل فراغًا. لا يُعدَّل أي نص.",
        "retrieved": prov.LK_RETRIEVED + " (آخر تحديث للمستودع 2023-05-03)",
        "license": "لا يوجد ملف ترخيص في المستودع. يطلب المؤلفون الاستشهاد بورقتي IJASAT 2019 وLREC 2020. "
                   "إذن إعادة النشر لم يُؤكَّد بعد (انظر المخاطر).",
        "notes": "فصل الإسناد عن المتن مراجَع يدويًا في صحيح البخاري، وآلي في غيره بدقة نحو 92% بحسب المدونة.",
    },
    {
        "id": "dorar-api",
        "name": dorar.SOURCE_NAME,
        "url": "https://dorar.net/article/389",
        "status": "used",
        "taken": "لكل نتيجة بحث: نص الحديث كما في الموسوعة، والراوي، والمحدث، والمصدر، والصفحة أو الرقم، "
                 "وخلاصة حكم المحدث. تُعرض أحكامًا منسوبة إلى قائليها.",
        "how": f"الواجهة الرسمية {dorar.API} فقط، بكلمات من أول المتن. الطلبات تعرّف نفسها ({dorar.USER_AGENT})، "
               f"ويفصل بينها {dorar.MIN_INTERVAL} ثانية على الأقل، والنتائج مخزنة مع تاريخ أخذها. "
               "مطابقة النتيجة بالرواية: المصدر نفسه والرقم نفسه، أو تشابه اللفظ 80% فأكثر مع تقارب الطول؛ وما دون ذلك «غير مؤكد».",
        "retrieved": "2026-09-28 (يُسجَّل لكل استعلام)",
        "license": "«جميع الحقوق محفوظة لمؤسسة الدرر السنية». الواجهة منشورة لأصحاب المواقع لعرض نتائج البحث في مواقعهم؛ "
                   "يعرضها سند منسوبة ومع رابط إلى الدرر. لم نجد صفحة شروط استخدام.",
        "notes": "robots.txt يسمح بكل المسارات (فُحص 2026-09-28).",
    },
    {
        "id": "dorar-tarajem",
        "name": "الدرر السنية — تراجم الرواة والمحدثين",
        "url": "https://dorar.net/hadith/tarajem",
        "status": "not_used",
        "taken": "لا شيء.",
        "how": "لم يُجلب شيء. لا توجد واجهة رسمية للتراجم، والصفحات محفوظة الحقوق ومحمية بنظام Cloudflare لمكافحة الروبوتات. "
               "لذلك تظهر حقول الترجمة في سند «غير متوفر في المصدر».",
        "retrieved": "فُحص 2026-09-28",
        "license": "«جميع الحقوق محفوظة».",
        "notes": "يلزم إذن مكتوب من مؤسسة الدرر السنية قبل أي استخدام آلي.",
    },
    {
        "id": "sanad-parser",
        "name": "قراءة سند للأسانيد (بيانات مشتقة)",
        "url": "https://github.com/ShathaTm/LK-Hadith-Corpus",
        "status": "derived",
        "taken": "أسماء الرواة وترتيبهم، وطرق التحويل، والشيوخ والتلاميذ داخل الشجرة، ونقطة تفرّع الطرق.",
        "how": "قواعد مكتوبة في sanad_core/isnad.py تقرأ نص الإسناد من المدونة. كل اسم يحفظ الكلمات التي قُرئ منها، "
               "فيُعرض النص الأصلي معه. لا يُضاف اسم غير مكتوب في النص؛ الإحالات («عن أبيه») تُكتب «والد فلان» ما لم يذكر الاسمُ الأبَ.",
        "retrieved": "يُحسب عند بناء البيانات",
        "license": "كود سند (انظر LICENSE). البيانات تابعة لترخيص المدونة.",
        "notes": "حساب آلي، وليس حكمًا علميًا على راوٍ أو حديث.",
    },
    {
        "id": "libs",
        "name": "مكتبات الواجهة: Cytoscape.js 3.30.2، dagre 0.8.5، cytoscape-dagre 2.5.0، أيقونات Tabler Icons 3.48.0",
        "url": "https://js.cytoscape.org/",
        "status": "used",
        "taken": "رسم الشجرة والأيقونات فقط (لا محتوى).",
        "how": "مضمّنة في public/vendor، والأيقونات في public/js/icons.js.",
        "retrieved": "—",
        "license": "MIT",
        "notes": "",
    },
    {
        "id": "fonts",
        "name": "الخطوط: Amiri وReadex Pro وJost",
        "url": "https://fontsource.org/",
        "status": "used",
        "taken": "الخطوط فقط.",
        "how": "ملفات woff2 من حزم Fontsource 5.3.0، مضمّنة في public/vendor/fonts مع ترخيص كل خط؛ لا طلب إلى خادم خارجي.",
        "retrieved": "—",
        "license": "SIL Open Font License 1.1",
        "notes": "",
    },
]

# Every religious field shown in the UI and where it comes from.
FIELDS = [
    ("المتن", "lk", "عمود Arabic_Matn، كما هو.", "matn_prov"),
    ("الإسناد", "lk", "عمود Arabic_Isnad، كما هو؛ ألفاظ التحديث ملوّنة للعرض فقط.", "isnad_prov"),
    ("الكتاب والباب والرقم", "lk", "أعمدة Chapter_Arabic وSection_Arabic وHadith_number.", "source_prov"),
    ("التعليق", "lk", "عمود Arabic_Comment، كما هو.", "comment_prov"),
    ("الحكم غير المنسوب", "lk", "عمود Arabic_Grade، مع وسم «حكم غير منسوب». يُحجب إن تضمّن «موضوع» أو «متواتر».", "grade_prov"),
    ("الحكم المنسوب", "dorar-api", "حقول المحدث والمصدر والرقم وخلاصة الحكم من الواجهة الرسمية، بنصها.", "grades[].prov"),
    ("أسماء الرواة والطرق", "sanad-parser", "قراءة آلية؛ مع كل اسم نصه الأصلي ودرجة الثقة.", "routes[].names[].prov"),
    ("شيوخ الراوي وتلاميذه في الشجرة", "sanad-parser", "من قبله ومن بعده في أسانيد الشجرة فقط.", "nodes[].relations_prov"),
    ("ترجمة الراوي (الاسم الكامل، الكنية، النسبة، المولد، الوفاة، الطبقة، أقوال العلماء)", "dorar-tarajem",
     "غير متوفر في المصدر: لا وصول آلي مسموح به.", "—"),
]

RISKS = [
    "ترخيص مدونة LK: لا يوجد ملف ترخيص؛ يلزم إذن المؤلفين بإعادة النشر قبل التسليم.",
    "الدرر السنية: الواجهة منشورة للعرض، لكن لا توجد شروط مكتوبة للتخزين المؤقت؛ يُستحسن مراسلة المؤسسة.",
    "فصل الإسناد عن المتن آلي في غير البخاري؛ قد تُقطع أسماء أو تدخل كلمات من المتن.",
    "مطابقة نتيجة الدرر بالرواية تقوم على تشابه اللفظ؛ قد يختلف ترقيم الطبعات.",
    "دمج الرواة في الشجرة يقوم على تطابق الاسم تحت الشيخ نفسه؛ الاسم الواحد قد يدل على أكثر من راوٍ.",
]


def catalog():
    return {"sources": SOURCES, "fields": FIELDS, "risks": RISKS,
            "dorar_access": {"robots": "User-agent: * / Disallow: (no path disallowed)", "checked": "2026-09-28",
                             "api": dorar.API, "api_doc": "https://dorar.net/article/389",
                             "tarajem": "no API; all rights reserved; Cloudflare bot management; not fetched"}}
