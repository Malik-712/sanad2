/* Isnad tree page. Cytoscape + dagre, vendored in /vendor (MIT). */
import { esc, $, $$, api, ICON, fmtPct } from "./ui.js";

const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const SAHIHAYN = ["bukhari", "muslim"];

const LEGEND = [
  ["prophet", "النبي ﷺ", "أعلى الشجرة. كل الطرق تنتهي إليه."],
  ["companion", "الصحابي", "أعلى راوٍ في الطريق، الذي يروي عن النبي ﷺ مباشرة بحسب نص الإسناد."],
  ["narrator", "راوٍ", "اسم كما استُخرج من نص الإسناد."],
  ["book", "المصنّف", "صاحب الكتاب الذي ورد فيه الطريق."],
  ["dashed", "إطار متقطع", "دمج غير مؤكد: اسم قصير أو مشترك، أو كُتب بصيغتين، أو مبني من إحالة مثل «عن أبيه»."],
  ["mudar", "نقطة تفرّع الطرق (المدار)", "حساب آلي: الراوي الذي يمر به أكبر عدد من الطرق مضروبًا في عدد فروعه. ليست حكمًا علميًا."],
  ["unlinked", "خط متقطع من النبي ﷺ", "لم يُذكر النبي ﷺ بعد آخر راوٍ في نص هذا الطريق؛ قد يكون القول قول الراوي، أو قطع الفصلُ الآلي الإسناد."],
  ["width", "سُمك الخط", "عدد الطرق التي تمر به."],
];
function keySvg(kind) {
  const box = (fill, stroke, dash = "", w = 1.5) => `<svg viewBox="0 0 34 18" aria-hidden="true"><rect x="1" y="2" width="32" height="14" rx="4" fill="${fill}" stroke="${stroke}" stroke-width="${w}" ${dash ? `stroke-dasharray="${dash}"` : ""}/></svg>`;
  switch (kind) {
    case "prophet": return box("var(--ink)", "var(--ink)");
    case "companion": return box("var(--rubric-soft)", "var(--rubric)");
    case "narrator": return box("var(--surface)", "var(--ink-2)");
    case "book": return box("var(--sunk)", "var(--ink)", "", 2);
    case "dashed": return box("var(--surface)", "var(--ink-2)", "4 3");
    case "mudar": return box("var(--surface)", "var(--mudar)", "", 3.5);
    case "unlinked": return `<svg viewBox="0 0 34 18" aria-hidden="true"><path d="M2 9h30" stroke="var(--ink-2)" stroke-width="2" stroke-dasharray="4 3"/></svg>`;
    default: return `<svg viewBox="0 0 34 18" aria-hidden="true"><path d="M2 5h30" stroke="var(--rule-strong)" stroke-width="1.5"/><path d="M2 13h30" stroke="var(--rule-strong)" stroke-width="5"/></svg>`;
  }
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
  const mudar = T.mudar ? nodeBy[T.mudar] : null;
  const self = T.chains.find((c) => c.hid === id);

  app.innerHTML = `
  <div class="tree-app" id="tree-app">
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
      ${T.incomplete.length ? `<p class="note">${T.incomplete.length} ${T.incomplete.length === 1 ? "طريق مقطوع" : "طرق مقطوعة"} لا يذكر نصها إلا اسمًا واحدًا، فلم تُرسم.</p>` : ""}

      <h2>تصفية الطرق</h2>
      <label class="field">الصحابي
        <select id="f-comp"><option value="">كل الصحابة</option>${companions.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("")}</select></label>
      <div class="field" role="group" aria-label="الكتب">الكتب
        ${books.map((b) => `<label class="check"><input type="checkbox" class="f-book" value="${esc(b)}" checked> ${esc(bookTitle[b])}</label>`).join("")}
        <label class="check"><input type="checkbox" id="f-sahih"> الصحيحان فقط</label>
      </div>
      <label class="field">أقل تشابه بين متن الرواية والحديث المختار: <b id="f-sim-v">45%</b>
        <input type="range" id="f-sim" min="45" max="100" step="5" value="45"></label>
      <label class="check"><input type="checkbox" id="f-mudar" checked> إبراز نقطة التفرّع</label>

      <div class="node-panel" id="info" aria-live="polite"><p class="meter">اضغط على اسم في الشجرة لتظهر طرقه وحده.</p></div>

      <h2>ماذا تعني الرموز؟</h2>
      <ul class="keys">${LEGEND.map(([k, t, d]) => `<li>${keySvg(k)}<span><b>${t}:</b> ${d}</span></li>`).join("")}</ul>
    </aside>
    <div class="canvas-wrap"><div id="cy" role="img" aria-label="رسم شجرة الإسناد. القائمة الجانبية تعرض الأرقام نفسها نصًا."></div></div>
  </div>`;

  if (typeof cytoscape === "undefined") {
    $(".canvas-wrap").insertAdjacentHTML("beforeend", `<p class="canvas-msg">تعذّر تحميل مكتبة الرسم. حدّث الصفحة.</p>`);
    return;
  }
  if (typeof cytoscapeDagre !== "undefined" && !cytoscape.__dagre) { cytoscape.use(cytoscapeDagre); cytoscape.__dagre = true; }

  const cy = cytoscape({
    container: $("#cy"),
    elements: [
      ...T.nodes.map((n) => ({ data: { id: n.key, label: n.label, kind: n.kind, routes: n.chains.length, unc: n.uncertain || n.merge === "prefix" ? 1 : 0 } })),
      ...T.edges.map((e) => ({ data: { id: `${e.source}>${e.target}`, source: e.source, target: e.target, routes: e.chains.length, unlinked: e.unlinked ? 1 : 0 } })),
    ],
    wheelSensitivity: 0.25, minZoom: 0.1, maxZoom: 3,
    style: styles(),
  });
  document.addEventListener("themechange", () => cy.style(styles()), { once: false });
  const layout = () => cy.elements(":visible").layout({ name: typeof cytoscapeDagre !== "undefined" ? "dagre" : "breadthfirst", rankDir: "TB",
    nodeSep: 18, rankSep: 56, directed: true, roots: "#prophet", animate: false, fit: true, padding: 30 }).run();

  function visibleChains() {
    const comp = $("#f-comp").value;
    const bset = new Set($$(".f-book:checked").map((x) => x.value));
    const sahih = $("#f-sahih").checked;
    const sim = +$("#f-sim").value / 100;
    return T.chains.filter((c) => (!comp || c.companion === comp) && bset.has(c.book) && (!sahih || SAHIHAYN.includes(c.book)) && (c.similarity >= sim || c.hid === id));
  }
  function apply() {
    $("#f-sim-v").textContent = `${$("#f-sim").value}%`;
    const vis = visibleChains();
    const vn = new Set(vis.flatMap((c) => c.nodes));
    const ve = new Set(vis.flatMap((c) => c.nodes.slice(1).map((k, i) => `${c.nodes[i]}>${k}`)));
    cy.batch(() => {
      cy.nodes().forEach((n) => n.style("display", vn.has(n.id()) ? "element" : "none"));
      cy.edges().forEach((e) => e.style("display", ve.has(e.id()) ? "element" : "none"));
      cy.nodes().removeClass("mudar");
      if (T.mudar && $("#f-mudar").checked) cy.getElementById(T.mudar).addClass("mudar");
      cy.elements().removeClass("dim hl");
    });
    $("#s-routes").textContent = vis.length;
    $("#s-comp").textContent = new Set(vis.filter((c) => c.to_prophet).map((c) => c.companion)).size;
    $("#s-books").textContent = new Set(vis.map((c) => c.book)).size;
    layout();
  }
  ["#f-comp", "#f-sahih", "#f-mudar", "#f-sim"].forEach((s) => $(s).addEventListener("change", apply));
  $("#f-sim").addEventListener("input", () => { $("#f-sim-v").textContent = `${$("#f-sim").value}%`; });
  $$(".f-book").forEach((x) => x.addEventListener("change", apply));

  const info = $("#info");
  cy.on("tap", "node", (ev) => focusNode(ev.target.id()));
  cy.on("tap", (ev) => { if (ev.target === cy) clearFocus(); });
  function clearFocus() {
    cy.elements().removeClass("dim hl");
    info.innerHTML = `<p class="meter">اضغط على اسم في الشجرة لتظهر طرقه وحده.</p>`;
  }
  function focusNode(key) {
    const n = nodeBy[key];
    const through = n.chains.map((c) => chainBy[c]).filter(Boolean);
    const keys = new Set(through.flatMap((c) => c.nodes));
    cy.batch(() => {
      cy.elements().addClass("dim").removeClass("hl");
      cy.nodes().filter((x) => keys.has(x.id())).removeClass("dim").addClass("hl");
      cy.edges().filter((e) => keys.has(e.source().id()) && keys.has(e.target().id())).removeClass("dim").addClass("hl");
    });
    const kind = { prophet: "", companion: "الصحابي في هذا الطريق", narrator: "راوٍ", book: "المصنّف" }[n.kind];
    info.innerHTML = `<h3>${esc(n.label)}</h3>
      <p class="meter">${kind}${n.uncertain ? "، والاسم قصير أو مشترك فتحديد صاحبه غير مؤكد" : ""}${n.merge === "prefix" ? "، ودُمج من صيغتين للاسم" : ""}</p>
      ${n.variants.length ? `<p class="meter">ورد أيضًا بصيغة: ${n.variants.map(esc).join("، ")}</p>` : ""}
      <p style="margin-top:8px">${through.length === 1 ? "يمر به طريق واحد" : `يمر به ${through.length} طرق`}:</p>
      <ul>${through.slice(0, 40).map((c) => `<li><a href="/h/${esc(c.hid)}" data-link>${esc(c.book_title)}، رقم ${esc(c.number)}</a> <span class="meter">تشابه ${fmtPct(c.similarity)}</span></li>`).join("")}</ul>`;
  }
  apply();

  function styles() {
    const C = { ink: cssVar("--ink"), ink2: cssVar("--ink-2"), surface: cssVar("--surface"), sunk: cssVar("--sunk"), rule: cssVar("--rule-strong"),
      rubric: cssVar("--rubric"), rubricSoft: cssVar("--rubric-soft"), mudar: cssVar("--mudar"), onInk: cssVar("--on-ink"), focus: cssVar("--focus") };
    return [
      { selector: "node", style: { label: "data(label)", "font-family": "Readex Pro, sans-serif", "font-size": 13, color: C.ink, "text-valign": "center", "text-halign": "center",
        shape: "round-rectangle", width: "label", height: 32, padding: "12px", "background-color": C.surface, "border-width": 1.5, "border-color": C.ink2,
        "text-wrap": "wrap", "text-max-width": 170 } },
      { selector: "node[kind='prophet']", style: { "background-color": C.ink, color: C.onInk, "border-width": 0, "font-size": 16, "font-weight": 700, height: 40 } },
      { selector: "node[kind='companion']", style: { "background-color": C.rubricSoft, "border-color": C.rubric, "font-weight": 600 } },
      { selector: "node[kind='book']", style: { "background-color": C.sunk, "border-color": C.ink, "border-width": 2, "font-weight": 600 } },
      { selector: "node[unc=1]", style: { "border-style": "dashed" } },
      { selector: "node.mudar", style: { "border-color": C.mudar, "border-width": 4 } },
      { selector: "edge", style: { width: "mapData(routes, 1, 12, 1.5, 7)", "line-color": C.rule, "curve-style": "taxi", "taxi-direction": "downward", "target-arrow-shape": "none" } },
      { selector: "edge[unlinked=1]", style: { "line-style": "dashed" } },
      { selector: ".dim", style: { opacity: 0.12 } },
      { selector: "node.hl", style: { "border-color": C.rubric, "border-width": 3 } },
      { selector: "edge.hl", style: { "line-color": C.rubric } },
      { selector: "node.found", style: { "border-color": C.focus, "border-width": 4 } },
    ];
  }
  return { cy, T, apply, focusNode };
}
