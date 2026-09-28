/* Isnad tree page. Cytoscape + dagre, vendored in /vendor (MIT).

   State lives in the URL (?comp=&books=&sahih=1&short=1&sim=&mudar=0&focus=&cmp=),
   so every view of the tree can be shared as a link. */
import { esc, $, $$, api, ICON, fmtPct, chainRow, toast, provBox, missing, MISSING } from "./ui.js";

const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const SAHIHAYN = ["bukhari", "muslim"];
const READABLE_ZOOM = 0.85;        // below this, 13px labels are too small to read
const TOP_COMPANION = "__top__";   // "the companion with the most routes"

/** Arabic search normalization, same idea as the server's (no diacritics, letter variants). */
const norm = (s) => String(s || "").replace(/[ؐ-ًؚ-ٰٟۖ-ۭـ]/g, "")
  .replace(/[أإآٱ]/g, "ا").replace(/ى/g, "ي").replace(/ة/g, "ه").replace(/ؤ/g, "و").replace(/ئ/g, "ي").trim();

const LEGEND = [
  ["prophet", "النبي ﷺ", "أعلى الشجرة. كل الطرق تنتهي إليه."],
  ["companion", "الصحابي", "أعلى راوٍ في الطريق، الذي يروي عن النبي ﷺ مباشرة بحسب نص الإسناد."],
  ["narrator", "راوٍ", "اسم كما استُخرج من نص الإسناد."],
  ["book", "المصنّف", "صاحب الكتاب الذي ورد فيه الطريق."],
  ["dashed", "إطار متقطع", "دمج غير مؤكد: اسم قصير أو مشترك، أو كُتب بصيغتين، أو مبني من إحالة مثل «عن أبيه»."],
  ["mudar", "إطار ذهبي: نقطة تفرّع الطرق (المدار)", "حساب آلي: الراوي الذي يمر به أكبر عدد من الطرق مضروبًا في عدد فروعه. ليست حكمًا علميًا."],
  ["hl", "إطار أحمر", "الاسم الذي اخترته والطرق التي تمر به؛ تخفت بقية الشجرة."],
  ["found", "إطار أزرق", "نتيجة البحث عن اسم في الشجرة."],
  ["cmp", "خط أحمر وخط أخضر", "الطريقان اللذان اخترتهما للمقارنة: الأول بالأحمر، والثاني بالأخضر."],
  ["unlinked", "خط متقطع من النبي ﷺ", "لم يُذكر النبي ﷺ بعد آخر راوٍ في نص هذا الطريق؛ قد يكون القول قول الراوي، أو قطع الفصلُ الآلي الإسناد."],
  ["width", "سُمك الخط", "عدد الطرق التي تمر به."],
];
function keySvg(kind) {
  const box = (fill, stroke, dash = "", w = 1.5) => `<svg viewBox="0 0 34 18" aria-hidden="true"><rect x="1.5" y="2" width="31" height="14" rx="4" fill="${fill}" stroke="${stroke}" stroke-width="${w}" ${dash ? `stroke-dasharray="${dash}"` : ""}/></svg>`;
  switch (kind) {
    case "prophet": return box("var(--ink)", "var(--ink)");
    case "companion": return box("var(--rubric-soft)", "var(--rubric)");
    case "narrator": return box("var(--surface)", "var(--ink-2)");
    case "book": return box("var(--sunk)", "var(--ink)", "", 2);
    case "dashed": return box("var(--surface)", "var(--ink-2)", "4 3");
    case "mudar": return box("var(--surface)", "var(--mudar)", "", 3.5);
    case "hl": return box("var(--surface)", "var(--rubric)", "", 3);
    case "found": return box("var(--surface)", "var(--focus)", "", 3.5);
    case "cmp": return `<svg viewBox="0 0 34 18" aria-hidden="true"><path d="M2 5h30" stroke="var(--rubric)" stroke-width="3"/><path d="M2 13h30" stroke="var(--found)" stroke-width="3"/></svg>`;
    case "unlinked": return `<svg viewBox="0 0 34 18" aria-hidden="true"><path d="M2 9h30" stroke="var(--ink-2)" stroke-width="2" stroke-dasharray="4 3"/></svg>`;
    default: return `<svg viewBox="0 0 34 18" aria-hidden="true"><path d="M2 5h30" stroke="var(--rule-strong)" stroke-width="1.5"/><path d="M2 13h30" stroke="var(--rule-strong)" stroke-width="5"/></svg>`;
  }
}

function readState() {
  const q = new URLSearchParams(location.search);
  return {
    comp: q.get("comp") || "",
    books: q.get("books") ? q.get("books").split(",") : null,
    sahih: q.get("sahih") === "1",
    short: q.get("short") === "1",
    sim: Math.min(100, Math.max(45, +q.get("sim") || 45)),
    mudar: q.get("mudar") !== "0",
    focus: q.get("focus") || "",
    cmp: q.get("cmp") ? q.get("cmp").split(",").slice(0, 2) : [],
  };
}

export async function treePage(app, id) {
  app.className = "full";
  app.innerHTML = `<div class="loading" style="padding:48px">جارٍ بناء الشجرة…</div>`;
  const T = await api({ action: "tree", id });
  document.title = "شجرة الطرق — سند";
  const nodeBy = Object.fromEntries(T.nodes.map((n) => [n.key, n]));
  const chainBy = Object.fromEntries(T.chains.map((c) => [c.id, c]));
  const books = [...new Set(T.chains.map((c) => c.book))];
  const bookTitle = Object.fromEntries(T.chains.map((c) => [c.book, c.book_title]));
  const companions = T.summary.companion_names;
  const routesOf = (comp) => T.chains.filter((c) => c.to_prophet && c.companion === comp).length;
  const topComp = [...companions].sort((a, b) => routesOf(b) - routesOf(a))[0] || "";
  const mudar = T.mudar ? nodeBy[T.mudar] : null;
  const self = T.chains.find((c) => c.hid === id);
  const routeName = (c) => `${c.book_title}، رقم ${c.number}${T.chains.filter((x) => x.hid === c.hid).length > 1 ? `، الطريق ${+c.id.split("#")[1] + 1}` : ""}`;
  const S = readState();
  if (S.books) S.books = S.books.filter((b) => books.includes(b));

  app.innerHTML = `
  <div class="tree-app" id="tree-app">
    <div class="canvas-wrap" id="canvas-wrap">
      <div id="cy" role="img" aria-label="رسم شجرة الإسناد. قائمة «الطرق نصًا» في الجانب تعرض الطرق نفسها."></div>
      <div class="toolbar" role="toolbar" aria-label="أدوات الرسم">
        <button class="icon-btn" type="button" id="z-in" title="تكبير (+)" aria-label="تكبير">${ICON.plus}</button>
        <button class="icon-btn" type="button" id="z-out" title="تصغير (−)" aria-label="تصغير">${ICON.minus}</button>
        <button class="icon-btn" type="button" id="z-fit" title="ملاءمة الشجرة كلها (0)" aria-label="ملاءمة الشجرة كلها">${ICON.fit}</button>
        <span class="sep" aria-hidden="true"></span>
        <button class="icon-btn" type="button" id="fs" title="ملء الشاشة (F)" aria-label="ملء الشاشة" aria-pressed="false">${ICON.full}</button>
        <button class="icon-btn" type="button" id="png" title="حفظ الشجرة صورة PNG" aria-label="حفظ الشجرة صورة PNG">${ICON.image}</button>
        <button class="icon-btn" type="button" id="share" title="نسخ رابط هذا العرض" aria-label="نسخ رابط هذا العرض بالتصفية الحالية">${ICON.link}</button>
      </div>
      <div class="findbox">
        <label for="find" class="sr-only">ابحث عن راوٍ في الشجرة</label>
        <input id="find" type="search" placeholder="ابحث عن راوٍ في الشجرة" autocomplete="off" role="combobox" aria-expanded="false" aria-controls="find-list" aria-autocomplete="list">
        <ul id="find-list" role="listbox" hidden></ul>
      </div>
      <div class="minimap" id="minimap" title="خريطة مصغّرة: اضغط لتنتقل إلى أي جزء" aria-hidden="true"><canvas></canvas></div>
    </div>

    <aside class="tree-side" aria-label="أدوات الشجرة">
      <a class="crumb" href="/h/${esc(id)}" data-link>${ICON.back}<span>رجوع إلى الحديث</span></a>
      <h1>شجرة الطرق</h1>
      <p class="sub">كل طرق هذا الحديث في الكتب الستة، من النبي ﷺ إلى المصنّفين${self ? `. الحديث المختار: ${esc(self.book_title)}، رقم ${esc(self.number)}` : ""}.</p>
      <div class="stats" aria-live="polite">
        <div><b id="s-routes">${T.summary.routes}</b><span>طريقًا</span></div>
        <div><b id="s-comp">${T.summary.companions}</b><span>صحابيًا</span></div>
        <div><b id="s-books">${T.summary.books.length}</b><span>كتب</span></div>
      </div>
      ${mudar ? `<p class="note">نقطة تفرّع الطرق: <b>${esc(mudar.label)}</b>. حساب آلي من عدد الطرق والفروع، وليست حكمًا علميًا.</p>` : ""}
      ${T.incomplete.length ? `<p class="note">${T.incomplete.length === 1 ? "طريق مقطوع لا يذكر نصه" : `${T.incomplete.length} طرق مقطوعة لا يذكر نصها`} إلا اسمًا واحدًا، فلم يُرسم: ${T.incomplete.map((c) => `<a href="/h/${esc(c.hid)}" data-link>${esc(c.book_title)} ${esc(c.number)}</a>`).join("، ")}.</p>` : ""}

      <div class="node-panel" id="info" aria-live="polite"></div>

      <h2>تصفية الطرق</h2>
      <label class="field">الصحابي
        <select id="f-comp">
          <option value="">كل الصحابة</option>
          ${companions.length > 1 ? `<option value="${TOP_COMPANION}">الأكثر طرقًا: ${esc(topComp)} (${routesOf(topComp)})</option>` : ""}
          ${companions.map((c) => `<option value="${esc(c)}">${esc(c)} (${routesOf(c)})</option>`).join("")}
        </select></label>
      <div class="field" role="group" aria-labelledby="g-books"><span id="g-books">الكتب</span>
        ${books.map((b) => `<label class="check"><input type="checkbox" class="f-book" value="${esc(b)}"> ${esc(bookTitle[b])}</label>`).join("")}
        <label class="check"><input type="checkbox" id="f-sahih"> الصحيحان فقط</label>
      </div>
      <label class="check"><input type="checkbox" id="f-short"> أقصر إسناد فقط (أقل عدد من الرواة)</label>
      <label class="field">أقل تشابه بين متن الرواية والحديث المختار: <b id="f-sim-v"></b>
        <input type="range" id="f-sim" min="45" max="100" step="5" aria-describedby="f-sim-help"></label>
      <p class="meter" id="f-sim-help">نسبة تشابه الحروف بين المتنين، حساب آلي. الحديث المختار يبقى ظاهرًا دائمًا.</p>
      <label class="check"><input type="checkbox" id="f-mudar"> إبراز نقطة التفرّع</label>
      <button class="btn ghost small" type="button" id="f-reset" style="margin-top:8px">إعادة كل التصفيات</button>

      <h2>قارن لفظ طريقين</h2>
      <label class="field">الطريق الأول<select id="c-a"></select></label>
      <label class="field">الطريق الثاني<select id="c-b"></select></label>
      <div class="compare" id="compare" aria-live="polite"></div>

      <h2>ماذا تعني الرموز؟</h2>
      <ul class="keys">${LEGEND.map(([k, t, d]) => `<li>${keySvg(k)}<span><b>${t}:</b> ${d}</span></li>`).join("")}</ul>

      <details class="more"><summary>الطرق نصًا (${T.chains.length})</summary><div id="as-text" class="routes"></div></details>
    </aside>
  </div>`;

  const wrap = $("#canvas-wrap");
  if (typeof cytoscape === "undefined") {
    wrap.insertAdjacentHTML("beforeend", `<p class="canvas-msg">تعذّر تحميل مكتبة الرسم. حدّث الصفحة. الطرق نفسها معروضة نصًا في القائمة الجانبية.</p>`);
  }

  // ---------------------------------------------------------------- controls from state
  $("#f-comp").value = S.comp === TOP_COMPANION || companions.includes(S.comp) ? S.comp : "";
  $$(".f-book").forEach((x) => { x.checked = !S.books || S.books.includes(x.value); });
  $("#f-sahih").checked = S.sahih;
  $("#f-short").checked = S.short;
  $("#f-sim").value = S.sim;
  $("#f-mudar").checked = S.mudar;

  function visibleChains() {
    let comp = $("#f-comp").value;
    if (comp === TOP_COMPANION) comp = topComp;
    const bset = new Set($$(".f-book:checked").map((x) => x.value));
    const sahih = $("#f-sahih").checked;
    const sim = +$("#f-sim").value / 100;
    let vis = T.chains.filter((c) => (!comp || (c.companion === comp && c.to_prophet)) && bset.has(c.book)
      && (!sahih || SAHIHAYN.includes(c.book)) && (c.similarity >= sim || c.hid === id));
    if ($("#f-short").checked && vis.length) {
      const linked = vis.filter((c) => c.to_prophet);
      const pool = linked.length ? linked : vis;
      const min = Math.min(...pool.map((c) => c.length));
      vis = pool.filter((c) => c.length === min);
    }
    return vis;
  }

  function writeState(extra = {}) {
    const q = new URLSearchParams();
    const comp = $("#f-comp").value;
    if (comp) q.set("comp", comp);
    const checked = $$(".f-book:checked").map((x) => x.value);
    if (checked.length !== books.length) q.set("books", checked.join(","));
    if ($("#f-sahih").checked) q.set("sahih", "1");
    if ($("#f-short").checked) q.set("short", "1");
    if (+$("#f-sim").value !== 45) q.set("sim", $("#f-sim").value);
    if (!$("#f-mudar").checked) q.set("mudar", "0");
    const st = { focus: focused, cmp: [$("#c-a").value, $("#c-b").value].filter(Boolean), ...extra };
    if (st.focus) q.set("focus", st.focus);
    if (st.cmp.length === 2) q.set("cmp", st.cmp.join(","));
    const qs = q.toString();
    history.replaceState(null, "", location.pathname + (qs ? `?${qs}` : ""));
  }

  // ---------------------------------------------------------------- compare selects
  function fillCompare(vis) {
    const opts = vis.map((c) => `<option value="${esc(c.id)}">${esc(routeName(c))}</option>`).join("");
    const keep = [$("#c-a").value || S.cmp[0], $("#c-b").value || S.cmp[1]];
    $("#c-a").innerHTML = `<option value="">اختر طريقًا</option>${opts}`;
    $("#c-b").innerHTML = `<option value="">اختر طريقًا</option>${opts}`;
    if (keep[0] && vis.some((c) => c.id === keep[0])) $("#c-a").value = keep[0];
    if (keep[1] && vis.some((c) => c.id === keep[1])) $("#c-b").value = keep[1];
  }
  async function runCompare() {
    const a = chainBy[$("#c-a").value], b = chainBy[$("#c-b").value];
    const box = $("#compare");
    writeState();
    cy?.elements().removeClass("cmp-a cmp-b");
    if (!a || !b) { box.innerHTML = `<p class="meter">اختر طريقين لترى الفرق بين لفظ متنيهما، كلمةً كلمة.</p>`; return; }
    if (cy) {
      const mark = (c, cls) => { c.nodes.forEach((k, i) => { cy.getElementById(k).addClass(cls); if (i) cy.getElementById(`${c.nodes[i - 1]}>${k}`).addClass(cls); }); };
      mark(a, "cmp-a"); mark(b, "cmp-b");
    }
    if (a.hid === b.hid) { box.innerHTML = `<p class="meter">الطريقان من رواية واحدة (${esc(a.book_title)} ${esc(a.number)})، فالمتن واحد. الفرق بينهما في الرواة فقط.</p>`; return; }
    box.innerHTML = `<div class="loading">جارٍ المقارنة…</div>`;
    try {
      const r = await api({ action: "compare", a: a.hid, b: b.hid });
      const ops = r.diff.ops.map((o) => o.t === "equal" ? `<span>${esc(o.a)}</span>`
        : `${o.a ? `<del class="del" title="في الطريق الأول">${esc(o.a)}</del>` : ""} ${o.b ? `<ins class="ins" title="في الطريق الثاني">${esc(o.b)}</ins>` : ""}`).join(" ");
      box.innerHTML = `
        <p class="meter">${esc(a.book_title)} ${esc(a.number)} مقابل ${esc(b.book_title)} ${esc(b.number)}: ${r.diff.shared_words} كلمة مشتركة من ${r.diff.a_words} و${r.diff.b_words}.</p>
        <div class="diff" lang="ar">${ops}</div>
        <div class="legend"><span><del class="del">مشطوب</del> في لفظ الطريق الأول وحده</span><span><ins class="ins">بخلفية خضراء</ins> في لفظ الطريق الثاني وحده</span></div>
        <p class="meter">المقارنة آلية بعد حذف التشكيل وتوحيد الحروف. النصان منقولان كما هما من <a href="/h/${esc(a.hid)}" data-link>${esc(a.book_title)} ${esc(a.number)}</a> و<a href="/h/${esc(b.hid)}" data-link>${esc(b.book_title)} ${esc(b.number)}</a>.</p>`;
    } catch (e) {
      box.innerHTML = `<p class="err">${esc(e.message)}</p>`;
    }
  }
  $("#c-a").addEventListener("change", runCompare);
  $("#c-b").addEventListener("change", runCompare);

  // ---------------------------------------------------------------- routes as text
  function renderText(vis) {
    $("#as-text").innerHTML = vis.map((c) => {
      const names = c.nodes.slice(1, -1).reverse().map((k) => ({ name: nodeBy[k].label, uncertain: nodeBy[k].uncertain || nodeBy[k].merge === "prefix" }));
      return `<div class="route"><div class="route-head"><b><a href="/h/${esc(c.hid)}" data-link>${esc(routeName(c))}</a></b><span>تشابه المتن ${fmtPct(c.similarity)}</span></div>${chainRow(names, nodeBy[c.nodes[c.nodes.length - 1]].label, { prophet: c.to_prophet })}</div>`;
    }).join("");
  }

  // ---------------------------------------------------------------- graph
  let cy = null;
  let focused = "";
  // Cytoscape's automatic label width mis-measures Arabic (and measures before
  // the web font is loaded), which clips names. Measure every label ourselves.
  await Promise.race([
    Promise.all(["400 13px", "600 13px", "700 16px"].map((f) => document.fonts.load(`${f} "Readex Pro"`))).catch(() => {}),
    new Promise((r) => setTimeout(r, 1500)),
  ]);
  const meas = document.createElement("canvas").getContext("2d");
  const MAX_W = 180;
  function box(label, kind) {
    const size = kind === "prophet" ? 16 : 13, weight = kind === "narrator" ? 400 : kind === "prophet" ? 700 : 600;
    meas.font = `${weight} ${size}px "Readex Pro", sans-serif`;
    const w = meas.measureText(label).width;
    const lines = Math.ceil(w / MAX_W);
    return { w: Math.ceil(Math.min(w, MAX_W)) + 26, h: (kind === "prophet" ? 40 : 32) + (lines - 1) * 17 };
  }
  if (typeof cytoscape !== "undefined") {
    if (typeof cytoscapeDagre !== "undefined" && !cytoscape.__dagre) { cytoscape.use(cytoscapeDagre); cytoscape.__dagre = true; }
    cy = cytoscape({
      container: $("#cy"),
      elements: [
        ...T.nodes.map((n) => ({ data: { id: n.key, label: n.label, kind: n.kind, routes: n.chains.length, unc: n.uncertain || n.merge === "prefix" ? 1 : 0, ...box(n.label, n.kind) } })),
        ...T.edges.map((e) => ({ data: { id: `${e.source}>${e.target}`, source: e.source, target: e.target, routes: e.chains.length, unlinked: e.unlinked ? 1 : 0 } })),
      ],
      minZoom: 0.08, maxZoom: 3,
      style: styles(),
    });
    const onTheme = () => { cy.style(styles()); drawMinimap(); };
    document.addEventListener("themechange", onTheme);
    // the page may be left: stop listening once the canvas is gone
    new MutationObserver((_, obs) => {
      if (!document.getElementById("cy")) { document.removeEventListener("themechange", onTheme); obs.disconnect(); }
    }).observe(app, { childList: true });
  }

  /** Fit if the whole tree is readable; otherwise open at a readable zoom at the top (the Prophet). */
  function openLarge() {
    if (!cy) return;
    const vis = cy.elements(":visible");
    cy.fit(vis, 40);
    if (cy.zoom() < READABLE_ZOOM) {
      cy.zoom({ level: READABLE_ZOOM, renderedPosition: { x: cy.width() / 2, y: 0 } });
      // the Prophet at the top; horizontally, the branching point (المدار) if
      // it is shown, since that is where the routes fan out
      const p = cy.getElementById("prophet").renderedPosition();
      const m = T.mudar && cy.getElementById(T.mudar);
      const x = m && m.visible() && $("#f-mudar").checked ? m.renderedPosition().x : p.x;
      cy.panBy({ x: cy.width() / 2 - x, y: 56 - p.y });
    }
    drawMinimap();
  }
  function layout() {
    if (!cy) return;
    cy.elements(":visible").layout({ name: typeof cytoscapeDagre !== "undefined" ? "dagre" : "breadthfirst", rankDir: "TB",
      nodeSep: 18, rankSep: 60, directed: true, roots: "#prophet", animate: false, fit: false }).run();
    openLarge();
  }

  function apply() {
    $("#f-sim-v").textContent = `${$("#f-sim").value}%`;
    const vis = visibleChains();
    const vn = new Set(vis.flatMap((c) => c.nodes));
    const ve = new Set(vis.flatMap((c) => c.nodes.slice(1).map((k, i) => `${c.nodes[i]}>${k}`)));
    if (cy) {
      cy.batch(() => {
        cy.nodes().forEach((n) => n.style("display", vn.has(n.id()) ? "element" : "none"));
        cy.edges().forEach((e) => e.style("display", ve.has(e.id()) ? "element" : "none"));
      });
    }
    $("#s-routes").textContent = vis.length;
    $("#s-comp").textContent = new Set(vis.filter((c) => c.to_prophet).map((c) => c.companion)).size;
    $("#s-books").textContent = new Set(vis.map((c) => c.book)).size;
    fillCompare(vis);
    renderText(vis);
    layout();
    // after layout and outside the batch: a class set in the same batch that
    // un-hides nodes can be drawn from a stale texture at low zoom
    if (cy) {
      cy.nodes().removeClass("mudar");
      if (T.mudar && $("#f-mudar").checked && vn.has(T.mudar)) cy.getElementById(T.mudar).addClass("mudar");
    }
    if (focused && vn.has(focused)) focusNode(focused, { center: false });
    else clearFocus();
    runCompare();
    writeState();
  }
  ["#f-comp", "#f-sahih", "#f-short", "#f-mudar", "#f-sim"].forEach((s) => $(s).addEventListener("change", apply));
  $("#f-sim").addEventListener("input", () => { $("#f-sim-v").textContent = `${$("#f-sim").value}%`; });
  $$(".f-book").forEach((x) => x.addEventListener("change", apply));
  $("#f-reset").addEventListener("click", () => {
    $("#f-comp").value = ""; $$(".f-book").forEach((x) => { x.checked = true; });
    $("#f-sahih").checked = false; $("#f-short").checked = false; $("#f-sim").value = 45; $("#f-mudar").checked = true;
    focused = ""; $("#c-a").value = ""; $("#c-b").value = "";
    apply();
  });

  // ---------------------------------------------------------------- focus mode
  const info = $("#info");
  function clearFocus() {
    focused = "";
    cy?.elements().removeClass("dim hl found");
    info.innerHTML = `<p class="meter">اضغط على اسم في الشجرة، أو ابحث عنه، لتظهر طرقه وحده.</p>`;
  }
  function focusNode(key, { center = true } = {}) {
    const n = nodeBy[key];
    if (!n) return;
    focused = key;
    const visIds = new Set(visibleChains().map((c) => c.id));
    const through = n.chains.map((c) => chainBy[c]).filter((c) => c && visIds.has(c.id));
    const keys = new Set(through.flatMap((c) => c.nodes));
    if (cy) {
      cy.batch(() => {
        cy.elements().addClass("dim").removeClass("hl found");
        cy.nodes().filter((x) => keys.has(x.id())).removeClass("dim").addClass("hl");
        cy.edges().filter((e) => keys.has(e.source().id()) && keys.has(e.target().id())).removeClass("dim").addClass("hl");
      });
      if (center) cy.animate({ center: { eles: cy.getElementById(key) }, zoom: Math.max(cy.zoom(), READABLE_ZOOM) }, { duration: matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 250 });
    }
    const kind = { prophet: "", companion: "الصحابي في هذا الطريق", narrator: "راوٍ", book: "المصنّف" }[n.kind];
    info.innerHTML = `<h3>${esc(n.label)}</h3>
      <p class="meter">${kind}${n.uncertain ? "، والاسم قصير أو مشترك فتحديد صاحبه غير مؤكد" : ""}${n.merge === "prefix" ? "، ودُمج من صيغتين للاسم" : ""}</p>
      ${n.variants.length ? `<p class="meter">ورد أيضًا بصيغة: ${n.variants.map(esc).join("، ")}</p>` : ""}
      <p style="margin-top:8px">${through.length === 1 ? "يمر به طريق واحد ظاهر" : `يمر به ${through.length} طرق ظاهرة`}:</p>
      <ul>${through.slice(0, 40).map((c) => `<li><a href="/h/${esc(c.hid)}" data-link>${esc(routeName(c))}</a> <span class="meter">تشابه ${fmtPct(c.similarity)}</span></li>`).join("")}</ul>
      ${n.kind === "narrator" || n.kind === "companion" ? profile(n) : ""}
      <div class="row"><button class="btn ghost small" type="button" id="unfocus">إظهار كل الطرق</button></div>`;
    $("#unfocus").addEventListener("click", () => { clearFocus(); writeState(); });
    writeState();
  }
  /** What Sanad can say about a narrator: only what the isnad texts show. */
  function profile(n) {
    const list = (xs) => (xs.length ? xs.map(esc).join("، ") : missing());
    const BIO = ["الاسم الكامل", "الكنية", "النسبة", "المولد (هجري)", "الوفاة (هجري)", "الطبقة", "أقوال العلماء فيه"];
    return `<div class="profile">
      <h4>ما نعرفه عن هذا الراوي</h4>
      <dl class="facts">
        <dt>الاسم كما ورد</dt><dd>${esc(n.label)}${n.variants.length ? ` <span class="meter">(ويرد: ${n.variants.map(esc).join("، ")})</span>` : ""}</dd>
      </dl>${provBox(n.prov)}
      <dl class="facts">
        <dt>شيوخه في هذه الشجرة</dt><dd>${n.kind === "companion" ? "النبي ﷺ" : list(n.teachers)}</dd>
        <dt>تلاميذه في هذه الشجرة</dt><dd>${list(n.students)}</dd>
        ${n.compilers.length ? `<dt>روى عنه من المصنّفين</dt><dd>${list(n.compilers)}</dd>` : ""}
      </dl>${provBox(n.relations_prov)}
      <dl class="facts">${BIO.map((f) => `<dt>${f}</dt><dd>${missing()}</dd>`).join("")}</dl>
      <details class="prov"><summary>كيف حصلنا على هذه المعلومة؟</summary><dl>
        <dt>المصدر</dt><dd>${MISSING}</dd>
        <dt>السبب</dt><dd>تراجم الرواة في الدرر السنية لا تُتاح عبر واجهتها الرسمية، وصفحاتها محفوظة الحقوق ومحمية من الوصول الآلي، فلم نجلبها. ولا يملأ سند هذه الحقول من عنده.</dd>
        <dt>التفاصيل</dt><dd><a href="/about/sources" data-link>صفحة المصادر</a></dd></dl></details>
    </div>`;
  }

  if (cy) {
    cy.on("tap", "node", (ev) => focusNode(ev.target.id(), { center: false }));
    cy.on("tap", (ev) => { if (ev.target === cy) { clearFocus(); writeState(); } });
  }

  // ---------------------------------------------------------------- find a narrator
  const find = $("#find"), list = $("#find-list");
  let hits = [], active = -1;
  function renderHits() {
    list.hidden = !hits.length;
    find.setAttribute("aria-expanded", String(!!hits.length));
    list.innerHTML = hits.map((n, i) => `<li role="option" id="hit-${i}" aria-selected="${i === active}"><button type="button" tabindex="-1" data-key="${esc(n.key)}">${esc(n.label)} <span class="meter">${n.chains.length} ${n.chains.length === 1 ? "طريق" : "طرق"}</span></button></li>`).join("");
    if (active >= 0) find.setAttribute("aria-activedescendant", `hit-${active}`); else find.removeAttribute("aria-activedescendant");
  }
  find.addEventListener("input", () => {
    const q = norm(find.value);
    const vn = cy ? new Set(cy.nodes(":visible").map((n) => n.id())) : null;
    hits = q ? T.nodes.filter((n) => n.kind !== "prophet" && (!vn || vn.has(n.key)) && [n.label, ...n.variants].some((l) => norm(l).includes(q))).slice(0, 12) : [];
    active = -1;
    renderHits();
  });
  function pick(key) {
    hits = []; renderHits();
    const n = nodeBy[key];
    find.value = n.label;
    focusNode(key);
    cy?.getElementById(key).addClass("found");
  }
  find.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" && hits.length) { active = (active + 1) % hits.length; renderHits(); e.preventDefault(); }
    else if (e.key === "ArrowUp" && hits.length) { active = (active - 1 + hits.length) % hits.length; renderHits(); e.preventDefault(); }
    else if (e.key === "Enter" && hits.length) { pick(hits[Math.max(0, active)].key); e.preventDefault(); }
    else if (e.key === "Escape") { hits = []; renderHits(); }
  });
  list.addEventListener("mousedown", (e) => { const b = e.target.closest("button[data-key]"); if (b) { e.preventDefault(); pick(b.dataset.key); } });
  find.addEventListener("blur", () => setTimeout(() => { hits = []; renderHits(); }, 150));

  // ---------------------------------------------------------------- zoom, fit, fullscreen
  const zoomBy = (f) => cy && cy.zoom({ level: cy.zoom() * f, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  $("#z-in").addEventListener("click", () => zoomBy(1.25));
  $("#z-out").addEventListener("click", () => zoomBy(0.8));
  $("#z-fit").addEventListener("click", () => { cy?.fit(cy.elements(":visible"), 30); drawMinimap(); });
  const treeApp = $("#tree-app");
  function setFull(on) {
    treeApp.classList.toggle("fs", on);
    $("#fs").setAttribute("aria-pressed", String(on));
    $("#fs").innerHTML = on ? ICON.exitFull : ICON.full;
    $("#fs").setAttribute("aria-label", on ? "الخروج من ملء الشاشة" : "ملء الشاشة");
    document.body.style.overflow = on ? "hidden" : "";
    requestAnimationFrame(() => { cy?.resize(); openLarge(); });
  }
  $("#fs").addEventListener("click", () => {
    const on = !treeApp.classList.contains("fs");
    if (on && treeApp.requestFullscreen) treeApp.requestFullscreen().catch(() => {});
    else if (!on && document.fullscreenElement) document.exitFullscreen().catch(() => {});
    setFull(on);
  });
  document.addEventListener("fullscreenchange", () => { if (!document.fullscreenElement && treeApp.classList.contains("fs")) setFull(false); });
  treeApp.addEventListener("keydown", (e) => {
    if (e.target.matches("input, select, textarea")) return;
    if (e.key === "+" || e.key === "=") zoomBy(1.25);
    else if (e.key === "-") zoomBy(0.8);
    else if (e.key === "0") $("#z-fit").click();
    else if (e.key.toLowerCase() === "f") $("#fs").click();
    else if (e.key === "Escape" && treeApp.classList.contains("fs")) setFull(false);
  });
  treeApp.tabIndex = -1;

  // ---------------------------------------------------------------- export and share
  $("#png").addEventListener("click", () => {
    if (!cy) return;
    const png = cy.png({ full: true, scale: 2, bg: cssVar("--paper"), maxWidth: 8000, maxHeight: 8000 });
    const a = document.createElement("a");
    a.href = png;
    a.download = `sanad-tree-${id}.png`;
    document.body.append(a); a.click(); a.remove();
    toast("حُفظت الشجرة صورةً");
  });
  $("#share").addEventListener("click", async () => {
    writeState();
    try { await navigator.clipboard.writeText(location.href); toast("نُسخ رابط هذا العرض"); }
    catch { toast("انسخ الرابط من شريط العنوان"); }
  });

  // ---------------------------------------------------------------- minimap
  const mm = $("#minimap"), mmc = $("canvas", mm);
  let mmBox = null;
  function drawMinimap() {
    if (!cy) { mm.hidden = true; return; }
    const W = mm.clientWidth, H = mm.clientHeight, dpr = window.devicePixelRatio || 1;
    mmc.width = W * dpr; mmc.height = H * dpr;
    const g = mmc.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, W, H);
    const vis = cy.elements(":visible");
    if (!vis.length) return;
    const bb = vis.boundingBox();
    const s = Math.min((W - 12) / bb.w, (H - 12) / bb.h);
    const ox = (W - bb.w * s) / 2 - bb.x1 * s, oy = (H - bb.h * s) / 2 - bb.y1 * s;
    mmBox = { s, ox, oy };
    g.strokeStyle = cssVar("--rule-strong"); g.lineWidth = 1;
    cy.edges(":visible").forEach((e) => { const a = e.source().position(), b = e.target().position(); g.beginPath(); g.moveTo(a.x * s + ox, a.y * s + oy); g.lineTo(b.x * s + ox, b.y * s + oy); g.stroke(); });
    cy.nodes(":visible").forEach((n) => {
      const p = n.position();
      g.fillStyle = n.hasClass("hl") ? cssVar("--rubric") : n.data("kind") === "prophet" ? cssVar("--ink") : cssVar("--ink-2");
      g.fillRect(p.x * s + ox - 2, p.y * s + oy - 1.5, 4, 3);
    });
    const ext = cy.extent();
    g.strokeStyle = cssVar("--focus"); g.lineWidth = 1.5;
    g.strokeRect(ext.x1 * s + ox, ext.y1 * s + oy, ext.w * s, ext.h * s);
  }
  let mmPending = false;
  cy?.on("viewport", () => { if (!mmPending) { mmPending = true; requestAnimationFrame(() => { mmPending = false; drawMinimap(); }); } });
  mm.addEventListener("click", (e) => {
    if (!cy || !mmBox) return;
    const r = mm.getBoundingClientRect();
    const x = (e.clientX - r.left - mmBox.ox) / mmBox.s, y = (e.clientY - r.top - mmBox.oy) / mmBox.s;
    cy.pan({ x: cy.width() / 2 - x * cy.zoom(), y: cy.height() / 2 - y * cy.zoom() });
  });
  window.addEventListener("resize", () => { if (cy && document.body.contains(mm)) { cy.resize(); drawMinimap(); } });

  // ---------------------------------------------------------------- go
  if (cy) window.__sanadTree = { cy, T };   // for automated checks
  focused = S.focus && nodeBy[S.focus] ? S.focus : "";
  apply();
  if (focused) { focusNode(focused); }

  function styles() {
    const C = { ink: cssVar("--ink"), ink2: cssVar("--ink-2"), surface: cssVar("--surface"), sunk: cssVar("--sunk"), rule: cssVar("--rule-strong"),
      rubric: cssVar("--rubric"), rubricSoft: cssVar("--rubric-soft"), mudar: cssVar("--mudar"), onInk: cssVar("--on-ink"), focus: cssVar("--focus"),
      found: cssVar("--found") };
    return [
      { selector: "node", style: { label: "data(label)", "font-family": "Readex Pro, sans-serif", "font-size": 13, color: C.ink, "text-valign": "center", "text-halign": "center",
        shape: "round-rectangle", width: "data(w)", height: "data(h)", "background-color": C.surface, "border-width": 1.5, "border-color": C.ink2,
        "text-wrap": "wrap", "text-max-width": MAX_W } },
      { selector: "node[kind='prophet']", style: { "background-color": C.ink, color: C.onInk, "border-width": 0, "font-size": 16, "font-weight": 700 } },
      { selector: "node[kind='companion']", style: { "background-color": C.rubricSoft, "border-color": C.rubric, "font-weight": 600 } },
      { selector: "node[kind='book']", style: { "background-color": C.sunk, "border-color": C.ink, "border-width": 2, "font-weight": 600 } },
      { selector: "node[unc=1]", style: { "border-style": "dashed" } },
      { selector: "edge", style: { width: "mapData(routes, 1, 12, 1.5, 7)", "line-color": C.rule, "curve-style": "taxi", "taxi-direction": "downward", "target-arrow-shape": "none" } },
      { selector: "edge[unlinked=1]", style: { "line-style": "dashed" } },
      { selector: "node.mudar", style: { "border-color": C.mudar, "border-width": 4, "border-style": "solid" } },
      { selector: ".dim", style: { opacity: 0.12 } },
      { selector: "node.hl", style: { "border-color": C.rubric, "border-width": 3 } },
      { selector: "edge.hl", style: { "line-color": C.rubric } },
      { selector: "edge.cmp-a", style: { "line-color": C.rubric, "line-style": "solid" } },
      { selector: "edge.cmp-b", style: { "line-color": C.found, "line-style": "solid" } },
      { selector: "node.cmp-a", style: { "border-color": C.rubric, "border-width": 3 } },
      { selector: "node.cmp-b", style: { "border-color": C.found, "border-width": 3 } },
      { selector: "node.found", style: { "border-color": C.focus, "border-width": 4, "border-style": "solid" } },
    ];
  }
}
