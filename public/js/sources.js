/* /about/sources: every data source, what was taken, how, and its licence. */
import { esc, api, safeUrl, skeleton } from "./ui.js";

const STATUS = { used: "مستخدم", not_used: "غير مستخدم", derived: "مشتق من غيره" };
const known = (s) => s && s.trim() && s.trim() !== "—";

export async function sourcesPage(app) {
  document.title = "المصادر والتراخيص | سند";
  app.innerHTML = `<div class="sources">${skeleton("جارٍ التحميل…", [40, 100, 90, 100, 70])}</div>`;
  const c = await api({ action: "sources" });
  const names = Object.fromEntries(c.sources.map((s) => [s.id, s.name]));
  app.innerHTML = `
  <article class="sources">
    <h1>المصادر والتراخيص</h1>
    <p>هذه كل المصادر التي يأخذ منها سند، وما أخذه من كل مصدر، وكيف أخذه، وترخيصه. وكل معلومة دينية في الصفحات معها صندوق «كيف حصلنا على هذه المعلومة؟» يذكر مصدرها بالتفصيل.</p>

    <h2>المصادر</h2>
    <div class="src-list">${c.sources.map((s) => `
      <section class="src" aria-label="${esc(s.name)}">
        <div class="src-head">
          <a href="${esc(safeUrl(s.url))}" target="_blank" rel="noopener">${esc(s.name)}</a>
          <span class="tag${s.status === "used" ? " ok" : ""}">${esc(STATUS[s.status] || s.status)}</span>
          ${known(s.retrieved) ? `<span class="meta">تاريخ الأخذ: ${esc(s.retrieved)}</span>` : ""}
        </div>
        <dl class="src-grid">
          <div><dt>ما أخذنا</dt><dd>${esc(s.taken)}</dd></div>
          <div><dt>كيف استخرجناه</dt><dd>${esc(s.how)}</dd></div>
          <div><dt>الترخيص</dt><dd>${esc(s.license)}</dd></div>
        </dl>
        ${s.notes ? `<p class="meta notes">${esc(s.notes)}</p>` : ""}
      </section>`).join("")}
    </div>

    <h2>كل حقل يُعرض ومن أين جاء</h2>
    <table class="src-table">
      <thead><tr><th>الحقل</th><th>المصدر</th><th>الطريقة</th></tr></thead>
      <tbody>${c.fields.map(([f, s, how]) => `<tr><td data-h="الحقل">${esc(f)}</td><td data-h="المصدر">${esc(names[s])}</td><td data-h="الطريقة">${esc(how)}</td></tr>`).join("")}</tbody>
    </table>

    <h2>الوصول إلى الدرر السنية</h2>
    <ul>
      <li>فُحص في ${esc(c.dorar_access.checked)}: ملف robots.txt لا يمنع أي مسار.</li>
      <li>تنشر الدرر واجهة رسمية للبحث في الموسوعة الحديثية (<a href="${esc(safeUrl(c.dorar_access.api_doc))}" target="_blank" rel="noopener">صفحة الواجهة</a>). يستعملها سند وحدها لجلب الأحكام منسوبةً إلى قائليها.</li>
      <li>لا توجد واجهة لتراجم الرواة، وصفحاتها محفوظة الحقوق ومحمية من الوصول الآلي؛ فلم يجلبها سند، وتظهر حقولها «غير متوفر في المصدر».</li>
    </ul>

    <h2>المخاطر المفتوحة</h2>
    <ul>${c.risks.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>

    <p class="note">التفاصيل نفسها في ملف <code>docs/PROVENANCE.md</code> في المستودع، مولّدة من المصدر نفسه.</p>
  </article>`;
  app.focus({ preventScroll: true });
}
