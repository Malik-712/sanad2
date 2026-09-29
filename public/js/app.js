/* Sanad front end: router and pages (no build step, ES modules). */
import { esc, $, $$, api, newPage, Aborted, ICON, CHEV, provBox, safeUrl, isnadHtml, chainHtml, chainRow, diffHtml, DIFF_LEGEND, datasetGrade, missing, fmtPct, countAr, skeleton, errorBox } from "./ui.js";

const app = document.getElementById("app");
const MAX_CHARS = 1500;
const NARRATIONS = ["رواية واحدة", "روايتان", "روايات", "رواية"];

// ------------------------------------------------------------------ router
export function go(url, { replace = false } = {}) {
  if (replace) history.replaceState(null, "", url);
  else history.pushState(null, "", url);
  render();
}
document.addEventListener("click", (e) => {
  const a = e.target.closest("a[data-link]");
  if (!a || e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
  e.preventDefault();
  go(a.getAttribute("href"));
});
window.addEventListener("popstate", render);

const ROUTES = [
  [/^\/$/, () => home()],
  [/^\/search$/, (m, q) => searchPage(q.get("q") || "", q.get("mode") || "verify")],
  [/^\/h\/([a-z]+-\d+(?:-\d+)?)$/, (m, q) => hadithPage(m[1], q.get("q"))],
  [/^\/tree\/([a-z]+-\d+(?:-\d+)?)$/, (m) => import("./tree.js").then((t) => t.treePage(app, m[1]))],
  [/^\/about$/, () => about()],
  [/^\/about\/sources$/, () => import("./sources.js").then((s) => s.sourcesPage(app)).catch((e) => { if (!(e instanceof Aborted)) notFound(); })],
];

function render() {
  newPage();
  // links from v0 used hash routes (#/h/bukhari-1): keep them working
  if (location.hash.startsWith("#/")) return go(location.hash.slice(1), { replace: true });
  const q = new URLSearchParams(location.search);
  app.className = "";
  const path = location.pathname.replace(/\/+$/, "") || "/";
  const hit = ROUTES.find(([re]) => re.test(path));
  $$("[data-nav]").forEach((a) => a.removeAttribute("aria-current"));
  const nav = path === "/" ? "home" : path === "/about" ? "about" : path === "/about/sources" ? "sources" : null;
  if (nav) $(`[data-nav="${nav}"]`)?.setAttribute("aria-current", "page");
  window.scrollTo(0, 0);
  const p = hit ? hit[1](path.match(hit[0]), q) : notFound();
  Promise.resolve(p).catch((e) => { if (!(e instanceof Aborted)) showError(e); });
}
function setTitle(t) { document.title = t ? `${t} | سند` : "سند | تحقّق من الحديث قبل أن تنشره"; }
function focusMain() { app.focus({ preventScroll: true }); }
function showError(e) {
  setTitle("تعذّر عرض الصفحة");
  app.className = "";
  app.innerHTML = `<div class="prose">${errorBox(e.message || e)}<p><a href="/" data-link>العودة إلى الصفحة الرئيسة</a></p></div>`;
}
function notFound() {
  setTitle("الصفحة غير موجودة");
  app.innerHTML = `<div class="prose"><h1>لا توجد صفحة بهذا العنوان</h1><p>قد يكون الرابط ناقصًا. ابدأ من <a href="/" data-link>صفحة التحقّق</a>.</p></div>`;
}

// ------------------------------------------------------------------ theme menu
const themeBtn = $("#theme");
const themeMenu = $("#theme-menu");
const THEMES = [["light", "فاتح", ICON.sun], ["dark", "داكن", ICON.moon], ["auto", "حسب النظام", ICON.auto]];
const TICK = ICON.check.replace('class="i"', 'class="i tick"');
themeMenu.innerHTML = THEMES.map(([k, name, ic]) =>
  `<button type="button" role="menuitemradio" data-theme-opt="${k}" aria-checked="false">${ic}<span>${name}</span>${TICK}</button>`).join("");
let theme = document.documentElement.getAttribute("data-theme") || "light";
function applyTheme(t) {
  const [, name, ic] = THEMES.find(([k]) => k === t) || THEMES[0];
  document.documentElement.setAttribute("data-theme", t);
  themeBtn.innerHTML = ic;
  themeBtn.setAttribute("aria-label", `المظهر: ${name}`);
  themeBtn.title = `المظهر: ${name}`;
  $$("[data-theme-opt]", themeMenu).forEach((b) => b.setAttribute("aria-checked", String(b.dataset.themeOpt === t)));
  const meta = $('meta[name="theme-color"]');
  if (meta) meta.content = getComputedStyle(document.documentElement).getPropertyValue("--surface").trim();
  document.dispatchEvent(new CustomEvent("themechange"));
}
applyTheme(THEMES.some(([k]) => k === theme) ? theme : "light");
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if (theme === "auto") applyTheme("auto"); });

function openMenu() {
  themeMenu.hidden = false;
  themeBtn.setAttribute("aria-expanded", "true");
  ($('[aria-checked="true"]', themeMenu) || $("button", themeMenu)).focus();
}
function closeMenu(returnFocus = false) {
  if (themeMenu.hidden) return;
  themeMenu.hidden = true;
  themeBtn.setAttribute("aria-expanded", "false");
  if (returnFocus) themeBtn.focus();
}
themeBtn.addEventListener("click", () => (themeMenu.hidden ? openMenu() : closeMenu()));
themeBtn.addEventListener("keydown", (e) => { if (e.key === "ArrowDown" && themeMenu.hidden) { e.preventDefault(); openMenu(); } });
themeMenu.addEventListener("click", (e) => {
  const b = e.target.closest("[data-theme-opt]");
  if (!b) return;
  theme = b.dataset.themeOpt;
  try { localStorage.setItem("sanad-theme", theme); } catch { /* no storage */ }
  applyTheme(theme);
  closeMenu(true);
});
themeMenu.addEventListener("keydown", (e) => {
  const items = $$("button", themeMenu);
  const i = items.indexOf(document.activeElement);
  const to = { ArrowDown: (i + 1) % items.length, ArrowUp: (i - 1 + items.length) % items.length, Home: 0, End: items.length - 1 }[e.key];
  if (to !== undefined) { e.preventDefault(); items[to].focus(); }
  else if (e.key === "Escape") { e.preventDefault(); closeMenu(true); }
  else if (e.key === "Tab") closeMenu();
});
document.addEventListener("click", (e) => { if (!e.target.closest(".theme")) closeMenu(); });

// ------------------------------------------------------------------ ask box
const PLACEHOLDER = {
  verify: "الصق هنا النص الذي وصلك منسوبًا إلى النبي ﷺ",
  topic: "اكتب كلمات من موضوع، مثل: فضل طلب العلم",
};
const LABEL = { verify: "النص الذي تريد التحقق منه", topic: "كلمات الموضوع" };
function askBox(value = "", mode = "verify") {
  return `
  <form class="ask" id="ask" role="search" novalidate>
    <div class="seg" role="group" aria-label="نوع البحث">
      <button type="button" data-mode="verify" aria-pressed="${mode === "verify"}">تحقّق من نص</button>
      <button type="button" data-mode="topic" aria-pressed="${mode === "topic"}">ابحث بموضوع</button>
    </div>
    <div class="ask-box">
      <label for="q" class="sr-only" id="q-label">${LABEL[mode]}</label>
      <textarea id="q" name="q" maxlength="${MAX_CHARS}" placeholder="${PLACEHOLDER[mode]}" aria-describedby="q-count">${esc(value)}</textarea>
      <div class="ask-bar">
        <span class="ask-count num" id="q-count" aria-live="polite"></span>
        <button class="btn btn-primary" id="ask-submit" type="submit">${mode === "topic" ? "ابحث" : "تحقّق"}</button>
      </div>
    </div>
  </form>`;
}
function bindAsk() {
  const form = $("#ask");
  const ta = $("#q");
  const count = $("#q-count");
  let mode = $('[aria-pressed="true"]', form).dataset.mode;
  const upd = () => { count.textContent = ta.value.length > MAX_CHARS * 0.8 ? `${ta.value.length} من ${MAX_CHARS} حرف` : ""; };
  upd();
  ta.addEventListener("input", upd);
  $$(".seg button", form).forEach((b) => b.addEventListener("click", () => {
    mode = b.dataset.mode;
    $$(".seg button", form).forEach((x) => x.setAttribute("aria-pressed", x === b));
    $("#ask-submit").textContent = mode === "topic" ? "ابحث" : "تحقّق";
    $("#q-label").textContent = LABEL[mode];
    ta.placeholder = PLACEHOLDER[mode];
    ta.focus();
  }));
  ta.addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) form.requestSubmit(); });
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = ta.value.trim().slice(0, MAX_CHARS);
    if (!q) { ta.focus(); return; }
    go(`/search?${new URLSearchParams({ q, mode })}`);
  });
}

// ------------------------------------------------------------------ home
// Texts that circulate online, to try the tool with. They are inputs, not
// hadith: the result page shows what the sources say about each.
const TRIES = [
  "إنما الأعمال بالنية ولكل امرئ ما نوى",
  "تبسمك في وجه اخيك صدقة",
  "اطلبوا العلم ولو في الصين",
  "من سلك طريق يلتمس فيه علم سهل الله له طريق الى الجنة",
];
const SPECIMEN = "bukhari-1";

async function home() {
  setTitle("");
  app.innerHTML = `
    <div class="home">
      <section aria-labelledby="h-title">
        <h1 id="h-title">تحقّق من الحديث قبل أن تنشره</h1>
        <p class="lede">الصق نصًا يُنسب إلى النبي ﷺ. يخبرك سند هل هو في الكتب الستة، وأين، وبأي لفظ، ثم يعرض طرقه كلها في شجرة واحدة.</p>
        ${askBox()}
        <div class="tries">
          <h2 id="tries-t">أو جرّب نصًا متداولًا</h2>
          <ul aria-labelledby="tries-t">${TRIES.map((t) => `<li><button type="button" data-try="${esc(t)}"><span>${esc(t)}</span>${ICON.forward}</button></li>`).join("")}</ul>
        </div>
      </section>
      <aside class="panel specimen" id="specimen" aria-labelledby="s-title">
        <h2 id="s-title">سند يقرأ الإسناد كلمة كلمة</h2>
        ${skeleton("جارٍ تحميل مثال من صحيح البخاري…", [100, 96, 90, 55])}
      </aside>
    </div>`;
  bindAsk();
  $$("[data-try]").forEach((b) => b.addEventListener("click", () => go(`/search?${new URLSearchParams({ q: b.dataset.try, mode: "verify" })}`)));
  const sp = $("#specimen");
  try {
    const h = await api({ action: "hadith", id: SPECIMEN });
    const route = h.routes[0];
    sp.innerHTML = `
      <h2 id="s-title">سند يقرأ الإسناد كلمة كلمة</h2>
      <p class="cap">بالأحمر ألفاظ التحديث كما في المخطوطات، وتحتها الرواة كما استخرجهم سند من النص نفسه.</p>
      <p class="text" lang="ar">${isnadHtml(h.isnad_words)}</p>
      ${route ? chainHtml(route.names, h.compiler) : ""}
      <p class="cite"><a href="/h/${esc(h.id)}" data-link>${esc(h.book_title)}، رقم ${esc(h.number)}</a></p>
      ${provBox(h.isnad_prov, "الإسناد")}`;
  } catch (e) {
    if (e instanceof Aborted) return;
    sp.innerHTML = `<h2 id="s-title">سند يقرأ الإسناد كلمة كلمة</h2><p class="meta">تعذّر تحميل المثال الآن.</p>`;
  }
}

// ------------------------------------------------------------------ search
const VERDICT = {
  found: ["found", "موجود في الكتب الستة", "وجدنا هذا النص في المصادر. هذا نصه كما ورد، ومعه مصدره."],
  near: ["near", "يوجد حديث قريب بلفظ مختلف", "لم نجد اللفظ نفسه. هذا أقرب نص في المصادر، والفروق بين النصين ملوّنة."],
  not_found: ["none", "غير موجود في مصادر سند", "لم نجد هذا النص في الكتب الستة. هذا ليس حكمًا على النص؛ فقد يكون في كتب أخرى لم يشملها سند."],
  topic: ["topic", "أحاديث فيها كلمات بحثك", "مرتبة حسب قرب الكلمات من بحثك. هذا بحث بالألفاظ، وليس بالمعنى."],
  empty: ["none", "النص قصير جدًا للبحث", "لم تبقَ كلمات يمكن البحث بها بعد حذف الكلمات الشائعة. أضف كلمات أخرى من النص."],
};
const ICON_OF = { found: ICON.found, near: ICON.near, none: ICON.none, topic: ICON.topic };

const searchSkeleton = () => `
  <div class="skel-wrap" role="status" style="margin-top:24px"><span class="sr-only">جارٍ البحث في الكتب الستة…</span>
    <span class="skel tall" style="--w:48%"></span>
    <div class="skel-box"><span class="skel" style="--w:32%"></span><span class="skel"></span><span class="skel"></span><span class="skel" style="--w:68%"></span></div>
  </div>`;

function resultCard(r, q, { lead = false, diff = false } = {}) {
  const showDiff = diff && r.diff;
  const hq = q ? `?q=${encodeURIComponent(q)}` : "";
  const match = typeof r.match === "number"
    ? `<span class="tag match num" title="نسبة كلمات نصك التي وردت بالترتيب نفسه في هذا المتن. حساب آلي، وليس حكمًا.">التطابق مع نصك ${fmtPct(r.match)}</span>` : "";
  return `
  <article class="result${lead ? " lead" : ""}">
    <div class="result-head"><b>${esc(r.book_title)}</b><span class="num">رقم ${esc(r.number)}</span><span>${esc(r.chapter)}</span>${match}</div>
    ${showDiff
      ? `<div class="diff" lang="ar">${diffHtml(r.diff)}</div>${DIFF_LEGEND}`
      : r.matn ? `<p class="text${lead ? "" : " clamp"}" lang="ar">${esc(r.matn)}</p>` : `<p>${missing()}</p>`}
    ${provBox(r.matn_prov, "المتن")}
    ${datasetGrade(r)}
    <div class="result-foot">
      <a class="btn btn-secondary btn-sm" href="/h/${encodeURIComponent(r.id)}${hq}" data-link><span>النص كاملًا والإسناد</span>${ICON.forward}</a>
      <a class="btn btn-quiet btn-sm" href="/tree/${encodeURIComponent(r.id)}" data-link>${ICON.tree}<span>شجرة الطرق</span></a>
    </div>
  </article>`;
}

async function searchPage(q, mode) {
  mode = mode === "topic" ? "topic" : "verify";
  setTitle(q ? `«${q.slice(0, 40)}»` : "بحث");
  app.innerHTML = `<div class="search-page"><div class="search-top">${askBox(q, mode)}</div><div id="res" aria-live="polite">${q.trim() ? searchSkeleton() : ""}</div></div>`;
  bindAsk();
  const res = $("#res");
  if (!q.trim()) return;
  const r = await api({ action: "search", q, mode });
  const [cls, title, body] = VERDICT[r.state] || VERDICT.not_found;
  const fixes = Object.entries(r.corrections || {});
  let html = `<section class="verdict ${esc(r.state)}" aria-labelledby="v-title">
      <span class="glyph">${ICON_OF[cls]}</span>
      <div><h2 id="v-title">${title}</h2><p>${body}</p>
      ${r.state === "not_found" ? `<p class="fix">للتحقق الأوسع: <a href="https://dorar.net/hadith/search?q=${encodeURIComponent(q)}" target="_blank" rel="noopener">ابحث عن النص نفسه في الموسوعة الحديثية (الدرر السنية)</a>، أو اسأل مختصًا.</p>` : ""}
      ${fixes.length ? `<p class="fix">كلمات لم ترد في المتون، فبحثنا بأقرب كلمة إليها في الكتابة: ${fixes.map(([a, b]) => `${esc(a)} ← ${esc(b)}`).join("، ")}</p>` : ""}</div>
    </section>`;
  const items = r.results || [];
  if ((r.state === "found" || r.state === "near") && items.length) {
    html += resultCard(items[0], q, { lead: true, diff: true });
    const others = items.slice(1).filter((x) => x.match >= 0.5).slice(0, 5);
    if (others.length) html += `<h2 class="more-title">روايات أخرى تحتوي نصك</h2>` + others.map((x) => resultCard(x, q)).join("");
  } else if (r.state === "topic") {
    html += items.length ? items.map((x) => resultCard(x, q)).join("") : `<p class="note">لا توجد نتائج. جرّب كلمات أخرى.</p>`;
  } else if (items.length) {
    html += `<details class="more"><summary><span>عرض أقرب النتائج رغم ضعف التطابق</span>${CHEV}</summary><div class="routes" style="margin-top:12px">${items.slice(0, 5).map((x) => resultCard(x, q)).join("")}</div></details>`;
  }
  res.innerHTML = html;
  $("#v-title")?.setAttribute("tabindex", "-1");
}

// ------------------------------------------------------------------ hadith page
const JOIN_LABEL = {
  direct: "طريق متصل في النص",
  co_narrator: "رواة معطوفون في طبقة واحدة",
  convergence: "طريق تحويل موصول",
  shared_name: "طريق تحويل موصول باسم مشترك",
  complete_segment: "طريق تحويل كامل",
  shared_name_taliq: "موصول بما بعد «وقال لي»",
  prior_isnad: "أُكمل من سند الحديث السابق",
};
const joinLabel = (j) => (j || "direct").split("+").map((p) => JOIN_LABEL[p] || p).join("، ");

const hadithSkeleton = () => `
  <div class="skel-wrap" role="status" style="padding-top:32px"><span class="sr-only">جارٍ تحميل الحديث…</span>
    <span class="skel tall" style="--w:36%"></span><span class="skel" style="--w:52%"></span>
    <div class="skel-box" style="margin-top:16px"><span class="skel"></span><span class="skel"></span><span class="skel" style="--w:80%"></span></div>
  </div>`;

async function hadithPage(id, q) {
  app.innerHTML = hadithSkeleton();
  const h = await api({ action: "hadith", id });
  const diff = q ? (await api({ action: "diff", id, q })).diff : null;
  setTitle(`${h.book_title}، رقم ${h.number}`);
  const notes = [];
  if (!h.gold_segmentation) notes.push("فصل الإسناد عن المتن في هذا الكتاب آلي في مصدر البيانات (دقته نحو 92%)، فقد يقع خطأ في آخر الإسناد أو أول المتن.");
  if (h.repaired) notes.push("نقل سند كلمات من أول المتن إلى آخر الإسناد لأن الفصل الآلي قطع اسم الراوي.");
  if (h.fragments.length) notes.push("في الإسناد أجزاء لم يذكر النص كيف تتصل بغيرها (تحويل غير موصول أو تعليق)؛ تُعرض منفصلة ولا تدخل الشجرة.");
  if (h.same_isnad) notes.push("الإسناد يقول «بهذا الإسناد»، فأكمل سند باقيه من الحديث السابق عند اسم مشترك، ووضعه بإطار متقطع.");
  const gradesHtml = h.grade || h.grade_withheld ? datasetGrade(h) : `<p>${missing()}</p>`;
  const back = q ? `/search?${new URLSearchParams({ q, mode: "verify" })}` : "/";
  app.innerHTML = `
    <a class="crumb" href="${esc(back)}" data-link>${ICON.back}<span>${q ? "رجوع إلى النتائج" : "الصفحة الرئيسة"}</span></a>
    <header class="h-head">
      <div><h1>${esc(h.book_title)}، رقم ${esc(h.number)}</h1>
        <p class="sub">${esc(h.chapter)}${h.section ? `، ${esc(h.section)}` : ""}</p></div>
      <div class="h-actions">
        <span class="meta">${h.family.length ? `${countAr(h.family.length + 1, NARRATIONS)} لهذا الحديث في الكتب الستة` : "طرق هذا الحديث في رسم واحد"}</span>
        <a class="btn btn-primary" href="/tree/${encodeURIComponent(h.id)}" data-link>${ICON.tree}<span>اعرض شجرة الطرق</span></a>
      </div>
    </header>
    <div class="h-grid">
      <div class="h-main">
        <section aria-labelledby="t-matn"><h2 id="t-matn">المتن</h2>
          ${h.matn ? `<p class="text" lang="ar">${esc(h.matn)}</p>${provBox(h.matn_prov, "المتن")}` : `<p>${missing()}</p>`}
          ${h.comment ? `<p class="note">${esc(h.comment)}</p>${provBox(h.comment_prov, "التعليق")}` : ""}</section>
        ${diff ? `<section aria-labelledby="t-diff"><h2 id="t-diff">مقارنة بالنص الذي أدخلته</h2><div class="diff" lang="ar">${diffHtml(diff)}</div>${DIFF_LEGEND}</section>` : ""}
        <section aria-labelledby="t-grades"><h2 id="t-grades">الحكم منسوبًا إلى قائله</h2>
          <div id="grades">${skeleton("جارٍ جلب الأحكام من الدرر السنية…", [30, 100, 72])}</div></section>
        <section aria-labelledby="t-isnad"><h2 id="t-isnad">الإسناد كما ورد</h2>
          <p class="text isnad-text" lang="ar">${h.isnad_words.length ? isnadHtml(h.isnad_words) : missing()}</p>${provBox(h.isnad_prov, "الإسناد")}</section>
        <section aria-labelledby="t-routes"><h2 id="t-routes">${h.routes.length > 1 ? `الطرق في هذا الإسناد <span class="count num">(${h.routes.length})</span>` : "سلسلة الرواة"}</h2>
          <div class="routes">${h.routes.length ? h.routes.map((r, i) => routeBlock(r, i, h)).join("") : `<p>${missing()}</p>`}</div>
          ${h.fragments.length ? `<h3 class="more-title">أجزاء غير موصولة</h3><div class="routes">${h.fragments.map((f) => `<div class="route">${chainHtml(f, "", { prophet: false })}</div>`).join("")}</div>` : ""}
          ${notes.map((n) => `<p class="note">${n}</p>`).join("")}
          <p class="note">الأسماء مستخرجة آليًا من نص الإسناد. الخط المتقطع تحت الاسم يعني أن الاسم قصير أو مشترك أو مبني من إحالة، فتحديد صاحبه غير مؤكد. سند لا يعرض ترجمة للراوي ولا حكمًا عليه.</p>
        </section>
      </div>
      <aside class="side" aria-label="المصدر">
        <div class="panel"><h3>المصدر</h3>
          <dl class="facts"><dt>الكتاب</dt><dd>${esc(h.book_title)}</dd><dt>الرقم</dt><dd class="num">${esc(h.number)}</dd>
            <dt>الكتاب/الباب</dt><dd>${esc(h.chapter) || missing()}</dd></dl>
          ${provBox(h.source_prov)}
        </div>
        ${h.family.length ? `<div class="panel"><h3>روايات أخرى لهذا الحديث</h3><ul class="family">${h.family.slice(0, 8).map((x) =>
          `<li><a href="/h/${esc(x.id)}" data-link>${esc(x.book_title)}، رقم ${esc(x.number)}</a><span class="meta num" title="تشابه المتن: حساب آلي">${fmtPct(x.similarity)}</span></li>`).join("")}</ul>
          <p class="meta" style="margin-top:8px">النسبة: تشابه المتن، حساب آلي.</p></div>` : ""}
      </aside>
    </div>`;
  focusMain();
  loadGrades(h, gradesHtml);
}

const MATCH_LABEL = { same_source: "المصدر نفسه والرقم نفسه", same_text: "لفظ مطابق", candidate: "لفظ قريب" };
const SHOW_GRADES = 4;
function gradeItem(g) {
  return `<div class="grade">
    <dl class="grade-facts">
      <div><dt>المحدث</dt><dd>${esc(g.muhaddith)}</dd></div>
      <div><dt>المصدر</dt><dd>${esc(g.book) || missing()}</dd></div>
      <div><dt>الصفحة أو الرقم</dt><dd class="num">${esc(g.ref) || missing()}</dd></div>
    </dl>
    <dl class="grade-verdict"><dt>خلاصة حكم المحدث</dt><dd><q lang="ar">${esc(g.verdict)}</q></dd></dl>
    <div class="grade-meta">${MATCH_LABEL[g.match] ? `<span class="tag">${MATCH_LABEL[g.match]}</span>` : ""}${g.prov.confidence === "uncertain" ? `<span class="tag unc">غير مؤكد</span>` : ""}
      ${provBox(g.prov, "الحكم")}</div>
  </div>`;
}
async function loadGrades(h, datasetHtml) {
  const box = $("#grades");
  let g;
  try { g = await api({ action: "grades", id: h.id }); } catch (e) { if (e instanceof Aborted) return; g = { status: "unavailable", items: [] }; }
  if (!document.body.contains(box)) return;
  const sure = g.items.filter((x) => x.prov.confidence === "high");
  const unsure = g.items.filter((x) => x.prov.confidence !== "high");
  const dorarLink = g.search_url ? `<a href="${esc(safeUrl(g.search_url))}" target="_blank" rel="noopener">افتح البحث نفسه في الدرر السنية</a>` : "";
  let html = "";
  if (sure.length) {
    html += `<div class="grades">${sure.slice(0, SHOW_GRADES).map(gradeItem).join("")}</div>`;
    if (sure.length > SHOW_GRADES) {
      html += `<details class="more"><summary><span>عرض بقية الأحكام (${sure.length - SHOW_GRADES})</span>${CHEV}</summary>
        <div class="grades grades-more">${sure.slice(SHOW_GRADES).map(gradeItem).join("")}</div></details>`;
    }
  } else {
    const why = {
      ok: "", no_match: "لم نجد في نتائج الدرر نصًا يطابق لفظ هذا الحديث بثقة.",
      not_fetched: "لم نجلب أحكام الدرر لهذا الحديث بعد.", unavailable: "تعذّر الوصول إلى الدرر السنية الآن.",
      no_text: "لا يوجد متن في المصدر نبحث به.",
    }[g.status] || "";
    html += `<p>${missing()}</p>${why ? `<p class="meta">${why} ${dorarLink}</p>` : ""}`;
  }
  if (unsure.length) {
    html += `<details class="more"><summary><span>نتائج غير مؤكدة (${unsure.length})</span>${CHEV}</summary>
      <div class="grades grades-more">${unsure.map(gradeItem).join("")}</div></details>`;
  }
  if (g.items.length) html += `<p class="meta grades-note">الأحكام منقولة بنصها من واجهة الدرر السنية الرسمية، ومنسوبة إلى قائليها كما وردت. سند لا يحكم على الحديث. ${dorarLink}</p>`;
  if (h.grade || h.grade_withheld) {
    html += sure.length
      ? `<details class="more"><summary><span>حكم مجموعة البيانات (غير منسوب)</span>${CHEV}</summary>${datasetHtml}</details>`
      : `<div class="grades-note">${datasetHtml}</div>`;
  }
  box.innerHTML = html;
}

function routeBlock(r, i, h) {
  return `<div class="route">
    <div class="route-head"><b>الطريق ${i + 1}</b><span>${esc(joinLabel(r.join))}</span>${r.to_prophet ? "" : `<span class="tag unc">لم يُذكر النبي ﷺ بعد آخر راوٍ في النص</span>`}</div>
    ${h.routes.length > 1 ? chainRow(r.names, h.compiler, { prophet: r.to_prophet }) : chainHtml(r.names, h.compiler, { prophet: r.to_prophet })}
    <details class="prov"><summary>${ICON.prov}<span>كيف استخرجنا أسماء هذا الطريق؟</span></summary>
      <dl>${r.names.map((n) => `<dt>${esc(n.name)}</dt><dd>${n.prov.quote ? `<q>${esc(n.prov.quote)}</q>` : missing()} ${n.uncertain ? `<span class="tag unc">غير مؤكد</span>` : ""}</dd>`).join("")}
      <dt>الطريقة</dt><dd>${esc(r.names[0]?.prov.method || "")}</dd>
      <dt>المصدر</dt><dd><a href="${esc(safeUrl(h.isnad_prov.url))}" target="_blank" rel="noopener">${esc(h.isnad_prov.source)}</a>، تاريخ الأخذ ${esc(h.isnad_prov.retrieved)}</dd></dl>
    </details>
  </div>`;
}

// ------------------------------------------------------------------ about
function about() {
  setTitle("كيف يعمل سند؟");
  app.innerHTML = `
  <article class="prose">
    <h1>كيف يعمل سند؟</h1>
    <p>سند أداة تحقق. تلصق نصًا يُنسب إلى النبي ﷺ، فيبحث عنه في الكتب الستة، ثم يعرض النص كما ورد في مصدره، مع كتابه ورقمه وإسناده، وشجرة كل طرقه.</p>
    <p>كل معلومة دينية يعرضها سند معها صندوق «كيف حصلنا على هذه المعلومة؟»: المصدر ورابطه، والنص الذي أُخذت منه حرفيًا، وتاريخ الأخذ، وطريقة الاستخراج، ودرجة الثقة.</p>

    <h2>ثلاث نتائج فقط</h2>
    <div class="states">
      <div class="verdict found"><span class="glyph">${ICON.found}</span><div><h3>موجود في الكتب الستة</h3><p>وجدنا النص بلفظه أو بفروق يسيرة.</p></div></div>
      <div class="verdict near"><span class="glyph">${ICON.near}</span><div><h3>يوجد حديث قريب بلفظ مختلف</h3><p>نعرض أقرب نص، ونلوّن الفروق بين النصين.</p></div></div>
      <div class="verdict not_found"><span class="glyph">${ICON.none}</span><div><h3>غير موجود في مصادر سند</h3><p>لم نجده في الكتب الستة. هذا ليس حكمًا على النص.</p></div></div>
    </div>

    <h2>ما الذي لا يفعله سند؟</h2>
    <ul>
      <li>لا يؤلّف نصًا دينيًا، ولا يعيد صياغته، ولا يلخّصه.</li>
      <li>لا يحكم على حديث ولا على راوٍ. الحكم الذي يظهر منقول من مصدره، ومنسوب إلى قائله إن عُرف، وإلا كُتب عليه «حكم غير منسوب».</li>
      <li>إن لم يجد معلومة كتب «غير متوفر في المصدر»، ولا يملأ الفراغ من عنده.</li>
    </ul>

    <h2>كيف يبحث؟</h2>
    <ul>
      <li><b>البحث:</b> بحث نصي (BM25) في المتون بعد توحيد الكتابة العربية، مع تصحيح الأخطاء الإملائية بمقارنة أجزاء الكلمات.</li>
      <li><b>النتيجة:</b> يقيس سند كم من كلمات نصك وردت بالترتيب نفسه في المتن، مع وزن أكبر للكلمات النادرة.</li>
    </ul>

    <h2>كيف يبني شجرة الطرق؟</h2>
    <ul>
      <li>يجمع روايات الحديث الواحد في الكتب الستة بتشابه المتون.</li>
      <li>يقرأ كل إسناد بقواعد مكتوبة: يقسمه عند ألفاظ التحديث، ويفصل الرواة المعطوفين بالواو، ويصل طرق التحويل (ح) حيث يقول النص «كلاهما عن» أو «كلهم عن» أو يتكرر اسم في الطريقين. وما لا يذكر النص كيف يتصل يبقى منفصلًا.</li>
      <li>يدمج الأسانيد من النبي ﷺ نزولًا. لا يُدمج اسمان إلا إذا كانا تحت الشيخ نفسه، والدمج غير المؤكد يُرسم بإطار متقطع.</li>
      <li>نقطة تفرّع الطرق (المدار) حساب: الراوي الذي يمر به أكبر عدد من الطرق مضروبًا في عدد الفروع التي تخرج منه. ليست حكمًا علميًا.</li>
    </ul>

    <h2>حدود هذه النسخة</h2>
    <ul>
      <li>المصادر هي الكتب الستة فقط.</li>
      <li>فصل الإسناد عن المتن آلي في غير البخاري، فقد يقع خطأ في آخر الإسناد.</li>
      <li>لا توجد تراجم للرواة: لا يتيح أي مصدر موثوق وصولًا آليًا مسموحًا به إلى التراجم حتى الآن. التفاصيل في <a href="/about/sources" data-link>صفحة المصادر</a>.</li>
    </ul>
  </article>`;
  focusMain();
}

render();
