# المصادر والأدوات والتراخيص

## البيانات

| المصدر | ماذا أخذنا | الترخيص / الشرط |
|---|---|---|
| [LK Hadith Corpus](https://github.com/ShathaTm/LK-Hadith-Corpus) — جامعة ليدز وجامعة الملك سعود | نص الكتب الستة بالعربية، والسند مفصولًا عن المتن، والكتاب والباب والرقم، والحكم كما ورد في المدونة | لا يوجد ملف ترخيص في المستودع؛ يطلب المؤلفون الاستشهاد بالورقتين أدناه. **يلزم التأكد من الإذن بإعادة النشر قبل التسليم** (راسلنا المؤلفة: shatha.tammami@gmail.com). |

الاستشهاد المطلوب:

- Altammami, S., Atwell, E., & Alsalka, A. (2019). *The Arabic–English Parallel Corpus of Authentic Hadith.* IJASAT, IMAN 2019.
- Altammami, S., Atwell, E., & Alsalka, A. (2020). *Constructing a Bilingual Hadith Corpus Using a Segmentation Tool.* LREC 2020, pp. 3383–3391.

ملاحظات على البيانات:
- فصل السند عن المتن في صحيح البخاري مراجَع يدويًا في المدونة، وفي بقية الكتب آلي بدقة نحو 92%.
- عمود الحكم لا يذكر قائل الحكم؛ لذلك يعرضه سند بعبارة «الحكم في البيانات».

## مكتبات الواجهة (مضمّنة في `public/vendor/`)

| المكتبة | الإصدار | الترخيص |
|---|---|---|
| [Cytoscape.js](https://js.cytoscape.org/) | 3.30.2 | MIT |
| [dagre](https://github.com/dagrejs/dagre) | 0.8.5 | MIT |
| [cytoscape-dagre](https://github.com/cytoscape/cytoscape.js-dagre) | 2.5.0 | MIT |

## خطوط

- Amiri و IBM Plex Sans Arabic من Google Fonts (SIL Open Font License).

## أدوات بناء البيانات

- numpy، scikit-learn (BSD-3-Clause) — تُستخدم في `pipeline/` فقط، لا في الخادم.
