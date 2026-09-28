/* Shared UI helpers. Everything that reaches innerHTML goes through esc(). */

export const MISSING = "غير متوفر في المصدر";

export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

// ------------------------------------------------------------------ API
let controller = new AbortController();
/** Called by the router on every navigation: pending requests of the old page are dropped. */
export function newPage() {
  controller.abort();
  controller = new AbortController();
}
export class Aborted extends Error {}
export async function api(params) {
  const signal = controller.signal;
  let r;
  try {
    r = await fetch("/api/sanad?" + new URLSearchParams(params), { signal });
  } catch (e) {
    if (signal.aborted) throw new Aborted();
    throw new Error("تعذّر الاتصال بالخادم. تحقّق من الاتصال ثم أعد المحاولة.");
  }
  const j = await r.json().catch(() => ({ error: "وصل رد لا يمكن قراءته من الخادم." }));
  if (signal.aborted) throw new Aborted();
  if (!r.ok) throw new Error(j.error || "حدث خطأ في الخادم.");
  return j;
}

// ------------------------------------------------------------------ icons
const svg = (body, vb = "0 0 24 24") => `<svg viewBox="${vb}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
export const ICON = {
  back: svg('<path d="M9 6l6 6-6 6"/>'),
  found: svg('<path d="M5 12.5l4.5 4.5L19 7.5"/>'),
  near: svg('<path d="M4 9h11M4 15h7"/><path d="M17 13l3 3-3 3"/>'),
  none: svg('<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4 4"/>'),
  topic: svg('<path d="M5 6h14M5 12h10M5 18h7"/>'),
  plus: svg('<path d="M12 5v14M5 12h14"/>'),
  minus: svg('<path d="M5 12h14"/>'),
  fit: svg('<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>'),
  full: svg('<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/><rect x="9" y="9" width="6" height="6" rx="1"/>'),
  exitFull: svg('<path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5"/>'),
  image: svg('<rect x="3.5" y="5" width="17" height="14" rx="2"/><path d="M3.5 16l5-5 4 4 3-3 5 5"/><circle cx="15.5" cy="9.5" r="1.3"/>'),
  link: svg('<path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7L11.5 6.8"/><path d="M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1.5-1.5"/>'),
  sun: svg('<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/>'),
  moon: svg('<path d="M20 14.5A8 8 0 019.5 4a8 8 0 1010.5 10.5z"/>'),
  auto: svg('<circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 010 16z" fill="currentColor"/>'),
  tree: `<svg viewBox="0 0 44 44" fill="none" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M22 6v10M22 16l-12 10M22 16l12 10M22 16v10M10 26v10M22 26v10M34 26v10"/><circle cx="22" cy="6" r="3"/></svg>`,
};

// ------------------------------------------------------------------ provenance
const CONF = { high: "عالية", uncertain: "غير مؤكد" };
/** The "كيف حصلنا على هذه المعلومة؟" box for one provenance record. */
export function provBox(p, extra = "") {
  if (!p) return "";
  return `<details class="prov"><summary>كيف حصلنا على هذه المعلومة؟</summary>
    <dl>
      <dt>المصدر</dt><dd>${p.url ? `<a href="${esc(safeUrl(p.url))}" target="_blank" rel="noopener">${esc(p.source)}</a>` : esc(p.source)}</dd>
      <dt>النص كما ورد</dt><dd>${p.quote && p.quote !== MISSING ? `<q>${esc(p.quote)}</q>` : `<span class="missing">${MISSING}</span>`}</dd>
      <dt>تاريخ الأخذ</dt><dd>${esc(p.retrieved || MISSING)}</dd>
      <dt>طريقة الاستخراج</dt><dd>${esc(p.method || MISSING)}</dd>
      ${p.confidence ? `<dt>درجة الثقة</dt><dd>${esc(CONF[p.confidence] || p.confidence)}${p.score != null ? ` (${esc(p.score)})` : ""}</dd>` : ""}
      ${extra}
    </dl></details>`;
}
/** Only http(s) links from provenance records are rendered as links. */
export function safeUrl(u) {
  try { const x = new URL(u, location.origin); return ["http:", "https:"].includes(x.protocol) ? x.href : "#"; } catch { return "#"; }
}
export const missing = () => `<span class="missing">${MISSING}</span>`;

// ------------------------------------------------------------------ text
/** The isnad as it is written, with transmission words rubricated. */
export function isnadHtml(words) {
  return words.map(([w, k]) => (k === "m" ? `<span class="rub">${esc(w)}</span>` : k === "n" ? `<span class="nm">${esc(w)}</span>` : esc(w))).join(" ");
}

/** One route as a vertical chain: the Prophet at the top, the compiler at the bottom. */
export function chainHtml(names, compiler, { animate = false, prophet = true } = {}) {
  const items = [];
  if (prophet) items.push(`<li><span>النبي ﷺ</span></li>`);
  [...names].reverse().forEach((n) => {
    const notes = [];
    if (n.relative) notes.push("من إحالة في النص");
    if (n.doubt) notes.push("شكّ الراوي بينه وبين غيره");
    else if (n.uncertain) notes.push("تحديد صاحب الاسم غير مؤكد");
    if (n.from) notes.push("من سند الحديث السابق");
    items.push(`<li class="${n.uncertain ? "unc" : ""}"><span>${esc(n.name)}</span>${notes.length ? `<small>${esc(notes.join("، "))}</small>` : ""}</li>`);
  });
  if (compiler) items.push(`<li class="end"><span>${esc(compiler)}</span><small>المصنّف</small></li>`);
  return `<ol class="chain-v${animate ? " animate" : ""}">${items.map((x, i) => x.replace("<li", `<li style="--i:${i}"`)).join("")}</ol>`;
}

/** Compact one-line chain for pages that list several routes. */
export function chainRow(names, compiler, { prophet = true } = {}) {
  const items = [];
  if (prophet) items.push(`<li class="top"><span>النبي ﷺ</span></li>`);
  [...names].reverse().forEach((n) => {
    const t = [n.relative && "من إحالة في النص", n.doubt ? "شكّ الراوي بينه وبين غيره" : n.uncertain && "تحديد صاحب الاسم غير مؤكد", n.from && "من سند الحديث السابق"].filter(Boolean).join("، ");
    items.push(`<li class="${n.uncertain ? "unc" : ""}"><span${t ? ` title="${esc(t)}"` : ""}>${esc(n.name)}</span>${t ? `<span class="sr-only">(${esc(t)})</span>` : ""}</li>`);
  });
  if (compiler) items.push(`<li class="end"><span>${esc(compiler)}</span></li>`);
  return `<ol class="chain-h">${items.join("")}</ol>`;
}

export function diffHtml(ops) {
  return ops.map((o) => {
    if (o.t === "same") return `<span class="same">${esc(o.src)}</span>`;
    if (o.t === "gap" || o.t === "ctx") return `<span class="gap">${esc(o.src)}</span>`;
    let s = "";
    if (o.src) s += `<ins class="ins" title="في المصدر">${esc(o.src)}</ins>`;
    if (o.user) s += ` <del class="del" title="في النص الذي أدخلته">${esc(o.user)}</del>`;
    return s;
  }).join(" ");
}
export const DIFF_LEGEND = `<div class="legend"><span><ins class="ins">بخلفية خضراء</ins> في المصدر، وليس في نصك</span><span><del class="del">مشطوب</del> في نصك، وليس في المصدر</span></div>`;

/** The unattributed grade from the dataset, labelled as such. */
export function datasetGrade(r) {
  if (r.grade_withheld) return `<p class="note">في مجموعة البيانات حكم على هذا الحديث لا يذكر قائله، وفيه وصف لا يعرضه سند إلا منسوبًا إلى عالم بعينه، فلم نعرضه.</p>`;
  if (!r.grade) return "";
  return `<div class="grade-line"><span class="tag">حكم غير منسوب في مجموعة البيانات</span> <q>${esc(r.grade)}</q>${provBox(r.grade_prov)}</div>`;
}

export function toast(msg) {
  const t = document.createElement("div");
  t.className = "toast";
  t.setAttribute("role", "status");
  t.textContent = msg;
  document.body.append(t);
  setTimeout(() => t.remove(), 2400);
}

export const fmtPct = (x) => `${Math.round(x * 100)}%`;
export const arNum = (n) => Number(n).toLocaleString("ar-EG");
