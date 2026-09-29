/* Shared UI helpers. Everything that reaches innerHTML goes through esc(). */
import { ICON } from "./icons.js";

export { ICON };
/** Disclosure chevron (rotates when its <details> opens). */
export const CHEV = ICON.chevron.replace('class="i"', 'class="i chev"');
export const MISSING = "غير متوفر في المصدر";

/** Arabic number agreement: 1 رواية واحدة، 2 روايتان، 3-10 روايات، 11+ رواية. */
export function countAr(n, [one, two, few, many]) {
  if (n === 1) return one;
  if (n === 2) return two;
  return `${n} ${n % 100 >= 3 && n % 100 <= 10 ? few : many}`;
}

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

// ------------------------------------------------------------------ provenance
const CONF = { high: "عالية", uncertain: "غير مؤكد" };
/** The "كيف حصلنا على هذه المعلومة؟" box for one provenance record.
    `subject` names the fact it documents (المتن، الإسناد، الحكم…) when a block shows several. */
export function provBox(p, subject = "") {
  if (!p) return "";
  return `<details class="prov"><summary>${ICON.prov}<span>كيف حصلنا على هذه المعلومة؟</span>${subject ? `<span class="subj">${esc(subject)}</span>` : ""}</summary>
    <dl>
      <dt>المصدر</dt><dd>${p.url ? `<a href="${esc(safeUrl(p.url))}" target="_blank" rel="noopener">${esc(p.source)}</a>` : esc(p.source)}</dd>
      <dt>النص كما ورد</dt><dd>${p.quote && p.quote !== MISSING ? `<q>${esc(p.quote)}</q>` : `<span class="missing">${MISSING}</span>`}</dd>
      <dt>تاريخ الأخذ</dt><dd>${esc(p.retrieved || MISSING)}</dd>
      <dt>طريقة الاستخراج</dt><dd>${esc(p.method || MISSING)}</dd>
      ${p.confidence ? `<dt>درجة الثقة</dt><dd>${esc(CONF[p.confidence] || p.confidence)}${p.score != null ? ` (${esc(p.score)})` : ""}</dd>` : ""}
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

const nameNotes = (n) => [
  n.relative && "من إحالة في النص",
  n.doubt ? "شكّ الراوي بينه وبين غيره" : n.uncertain && "تحديد صاحب الاسم غير مؤكد",
  n.from && "من سند الحديث السابق",
].filter(Boolean).join("، ");

/** One route as a vertical chain: the Prophet at the top, the compiler at the bottom. */
export function chainHtml(names, compiler, { prophet = true } = {}) {
  const items = [];
  if (prophet) items.push(`<li class="top"><span>النبي ﷺ</span></li>`);
  [...names].reverse().forEach((n) => {
    const t = nameNotes(n);
    items.push(`<li class="${n.uncertain ? "unc" : ""}"><span>${esc(n.name)}</span>${t ? `<small>${esc(t)}</small>` : ""}</li>`);
  });
  if (compiler) items.push(`<li class="end"><span>${esc(compiler)}</span><small>المصنّف</small></li>`);
  return `<ol class="chain-v">${items.join("")}</ol>`;
}

/** Compact one-line chain for pages that list several routes. */
export function chainRow(names, compiler, { prophet = true } = {}) {
  const items = [];
  if (prophet) items.push(`<li class="top"><span>النبي ﷺ</span></li>`);
  [...names].reverse().forEach((n) => {
    const t = nameNotes(n);
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
  return `<div class="grade-line"><span class="tag unc">حكم غير منسوب في مجموعة البيانات</span> <q>${esc(r.grade)}</q>${provBox(r.grade_prov, "الحكم")}</div>`;
}

// ------------------------------------------------------------------ states
/** Loading placeholder: blank bars (never placeholder text that could pass for a source). */
export function skeleton(label, widths = [100, 92, 64]) {
  return `<div class="skel-wrap" role="status"><span class="sr-only">${esc(label)}</span>${widths.map((w) => `<span class="skel" style="--w:${w}%"></span>`).join("")}</div>`;
}
export function errorBox(msg) {
  return `<div class="err" role="alert">${ICON.alert}<p>${esc(msg)}</p></div>`;
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
