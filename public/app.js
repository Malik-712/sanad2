/* Sanad v0 — front end (no build step). */
(() => {
  "use strict";
  const app = document.getElementById("app");
  const API = "/api/sanad";

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const api = async (params) => {
    const r = await fetch(API + "?" + new URLSearchParams(params));
    const j = await r.json().catch(() => ({ error: "تعذّر قراءة الرد." }));
    if (!r.ok) throw new Error(j.error || "حدث خطأ.");
    return j;
  };
  const parseHash = () => {
    const h = location.hash.replace(/^#/, "") || "/";
    const [path, qs] = h.split("?");
    return { parts: path.split("/").filter(Boolean), q: new URLSearchParams(qs || "") };
  };
  const go = (path) => { location.hash = path; };

  const EXAMPLES = [
    "إنما الأعمال بالنية ولكل امرئ ما نوى",
    "من سلك طريق يلتمس فيه علم سهل الله له طريق الى الجنة",
    "اطلبوا العلم ولو في الصين",
    "تبسمك في وجه اخيك صدقة",
  ];

  // --------------------------------------------------------------- ask box
  function askBox(value = "", mode = "verify") {
    return `
    <form class="ask" id="ask" role="search">
      <label for="q" class="sr-only">نص الحديث أو موضوعه</label>
      <textarea id="q" name="q" placeholder="${mode === "topic" ? "اكتب موضوعًا، مثل: فضل طلب العلم" : "الصق هنا النص الذي وصلك منسوبًا إلى النبي ﷺ"}">${esc(value)}</textarea>
      <div class="ask-bar">
        <div class="modes" role="group" aria-label="نوع البحث">
          <button type="button" data-mode="verify" aria-pressed="${mode === "verify"}">تحقّق من نص</button>
          <button type="button" data-mode="topic" aria-pressed="${mode === "topic"}">ابحث بموضوع</button>
        </div>
        <button class="btn" type="submit">${mode === "topic" ? "ابحث" : "تحقّق"}</button>
      </div>
    </form>`;
  }
  function bindAsk() {
    const form = document.getElementById("ask");
    const ta = document.getElementById("q");
    let mode = form.querySelector('[aria-pressed="true"]').dataset.mode;
    form.querySelectorAll(".modes button").forEach((b) => b.addEventListener("click", () => {
      mode = b.dataset.mode;
      form.querySelectorAll(".modes button").forEach((x) => x.setAttribute("aria-pressed", x === b));
      form.querySelector(".btn").textContent = mode === "topic" ? "ابحث" : "تحقّق";
      ta.placeholder = mode === "topic" ? "اكتب موضوعًا، مثل: فضل طلب العلم" : "الصق هنا النص الذي وصلك منسوبًا إلى النبي ﷺ";
      ta.focus();
    }));
    ta.addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) form.requestSubmit(); });
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const q = ta.value.trim();
      if (q) go(`/search?${new URLSearchParams({ q, mode })}`);
    });
  }

  // --------------------------------------------------------------- pages
  function home() {
    app.className = "";
    app.innerHTML = `
      <section class="hero">
        <h1>تحقّق من الحديث قبل أن تنشره</h1>
        <p>الصق نصًا يُنسب إلى النبي ﷺ، فيخبرك سند هل هو موجود في الكتب الستة، وأين، وبأي لفظ. ثم اعرض كل طرقه في شجرة واحدة.</p>
        ${askBox()}
        <div class="examples">جرّب:
          ${EXAMPLES.map((e) => `<button type="button" data-ex="${esc(e)}">${esc(e)}</button>`).join("")}
        </div>
      </section>`;
    bindAsk();
    app.querySelectorAll("[data-ex]").forEach((b) => b.addEventListener("click", () => go(`/search?${new URLSearchParams({ q: b.dataset.ex, mode: "verify" })}`)));
    document.getElementById("q").focus();
  }

  const VERDICT = {
    found: ["موجود في المصادر", "وجدنا هذا النص في الكتب الستة. هذا هو نصه كما ورد في المصدر."],
    near: ["يوجد حديث قريب بلفظ مختلف", "لم نجد هذا اللفظ بعينه. هذا أقرب ما في المصادر، والفروق بين النصين ملوّنة."],
    not_found: ["غير موجود في مصادر سند", "لم نجد هذا النص في الكتب الستة. هذا لا يعني أنه موضوع؛ فقد يكون في كتب أخرى. للتحقق الأوسع اسأل مختصًا، أو ابحث في <a href=\"https://dorar.net/hadith\" target=\"_blank\" rel=\"noopener\">الموسوعة الحديثية</a>."],
    topic: ["أحاديث مرتبطة بما كتبت", "مرتبة حسب الصلة بالكلمات. البحث بالمعنى يُضاف في النسخة القادمة."],
    empty: ["اكتب نصًا أطول", "لم يبق من النص كلمات يمكن البحث بها."],
  };

  const gradeTag = (g) => g ? `<span class="grade" title="الحكم كما ورد في مجموعة البيانات. نسبته إلى قائله تُضاف بعد مراجعة المتخصص.">الحكم في البيانات: ${esc(g)}</span>` : `<span class="meter">لا يتوفر حكم في البيانات</span>`;

  function diffHtml(ops) {
    return ops.map((o) => {
      if (o.t === "same") return `<span class="same">${esc(o.src)}</span>`;
      if (o.t === "gap" || o.t === "ctx") return `<span class="gap">${esc(o.src)}</span>`;
      let s = "";
      if (o.src) s += `<span class="ins" title="في المصدر">${esc(o.src)}</span>`;
      if (o.user) s += ` <span class="del" title="في النص الذي أدخلته">${esc(o.user)}</span>`;
      return s;
    }).join(" ");
  }

  function resultCard(r, q, opts = {}) {
    const showDiff = opts.diff && r.diff;
    return `
    <article class="card">
      <div class="src"><b>${esc(r.book_title)}</b><span>رقم ${esc(r.number)}</span><span>${esc(r.chapter)}</span>${gradeTag(r.grade)}</div>
      ${showDiff
        ? `<div class="diff">${diffHtml(r.diff)}</div>
           <div class="legend"><span><span class="ins">أخضر</span> في المصدر وليس في نصك</span><span><span class="del">مشطوب</span> في نصك وليس في المصدر</span></div>`
        : `<div class="matn clamp">${esc(r.matn)}</div>`}
      <div class="acts">
        <a href="#/h/${encodeURIComponent(r.id)}${q ? "?q=" + encodeURIComponent(q) : ""}">النص كاملًا والسند</a>
        <a href="#/tree/${encodeURIComponent(r.id)}">شجرة الطرق</a>
        ${typeof r.match === "number" ? `<span class="meter">التطابق مع نصك: ${Math.round(r.match * 100)}%</span>` : ""}
      </div>
    </article>`;
  }

  async function searchPage(q, mode) {
    app.className = "";
    app.innerHTML = `${askBox(q, mode === "topic" ? "topic" : "verify")}<div id="res" class="loading" aria-live="polite">جارٍ البحث في الكتب الستة…</div>`;
    bindAsk();
    const res = document.getElementById("res");
    try {
      const r = await api({ action: "search", q, mode });
      const [title, body] = VERDICT[r.state] || VERDICT.not_found;
      const fixes = Object.entries(r.corrections || {});
      let html = `<section class="verdict ${r.state}"><h2>${title}</h2><p>${body}</p>
        ${fixes.length ? `<p class="fix">صحّحنا الإملاء للبحث: ${fixes.map(([a, b]) => `${esc(a)} ← ${esc(b)}`).join("، ")}</p>` : ""}</section>`;
      const items = r.results || [];
      if (r.state === "found" || r.state === "near") {
        html += resultCard(items[0], q, { diff: true });
        const others = items.slice(1).filter((x) => x.match >= 0.5).slice(0, 5);
        if (others.length) html += `<h3 class="more-title">روايات أخرى تحتوي نصك</h3>` + others.map((x) => resultCard(x, q)).join("");
      } else if (r.state === "topic") {
        html += items.map((x) => resultCard(x, q)).join("");
      } else if (items.length) {
        html += `<details><summary class="more-title" style="cursor:pointer">عرض أقرب النتائج رغم ضعف التطابق</summary>${items.slice(0, 5).map((x) => resultCard(x, q)).join("")}</details>`;
      }
      res.className = "";
      res.innerHTML = html;
    } catch (e) {
      res.className = "err";
      res.textContent = e.message;
    }
  }

  async function hadithPage(id, q) {
    app.className = "";
    app.innerHTML = `<div class="loading">جارٍ التحميل…</div>`;
    try {
      const h = await api({ action: "hadith", id });
      let diff = null;
      if (q) diff = (await api({ action: "diff", id, q })).diff;
      const chain = [...h.chain].reverse();
      app.innerHTML = `
        <a class="back" href="javascript:history.back()">رجوع</a>
        <div class="h-head"><h1>${esc(h.book_title)}، رقم ${esc(h.number)}</h1><div class="sub">${esc(h.chapter)}${h.section ? " — " + esc(h.section) : ""}</div></div>
        <article class="card">
          <div class="isnad">${esc(h.isnad)}</div>
          <div class="matn">${esc(h.matn)}</div>
          ${h.comment ? `<div class="note">${esc(h.comment)}</div>` : ""}
          <div>${gradeTag(h.grade)}</div>
        </article>
        ${diff ? `<article class="card"><div class="src"><b>مقارنة بنصك</b></div><div class="diff">${diffHtml(diff)}</div>
          <div class="legend"><span><span class="ins">أخضر</span> في المصدر وليس في نصك</span><span><span class="del">مشطوب</span> في نصك وليس في المصدر</span></div></article>` : ""}
        <article class="card">
          <div class="src"><b>سلسلة السند</b><span>من النبي ﷺ إلى المصنف</span></div>
          <div class="chain"><span>النبي ﷺ</span>${chain.map((n) => `<i>←</i><span class="${n.uncertain ? "unc" : ""}" title="${n.uncertain ? "اسم قصير أو مشترك؛ تحديد صاحبه غير مؤكد" : ""}">${esc(n.name)}</span>`).join("")}<i>←</i><span>${esc(h.compiler)}</span></div>
          ${h.chain_partial ? `<div class="note">في هذا السند تحويل (ح)، أي أكثر من طريق. تعرض النسخة الحالية الطريق الأخير فقط.</div>` : ""}
          ${!h.gold_segmentation ? `<div class="note">فصل السند عن المتن في هذا الكتاب آلي في مصدر البيانات (دقته نحو 92%)، فقد يقع خطأ في أول المتن أو آخر السند.</div>` : ""}
          <div class="note">الأسماء مستخرجة آليًا من نص السند. الإطار المتقطع يعني أن الاسم قصير أو مشترك بين أكثر من راوٍ.</div>
        </article>
        <a class="tree-cta" href="#/tree/${encodeURIComponent(h.id)}"><div><b>اعرض شجرة الطرق</b><span>${h.family.length ? `هذا الحديث له ${h.family.length + 1} رواية في الكتب الستة` : "كل الطرق في رسم واحد"}</span></div><span aria-hidden="true">←</span></a>
        ${h.family.length ? `<h3 class="more-title">روايات أخرى لهذا الحديث</h3>${h.family.slice(0, 8).map((x) => resultCard(x)).join("")}` : ""}`;
    } catch (e) {
      app.innerHTML = `<p class="err">${esc(e.message)}</p>`;
    }
  }

  // --------------------------------------------------------------- tree
  const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

  async function treePage(id) {
    app.className = "wide";
    app.innerHTML = `<div class="loading">جارٍ بناء الشجرة…</div>`;
    let T;
    try { T = await api({ action: "tree", id }); } catch (e) { app.innerHTML = `<p class="err">${esc(e.message)}</p>`; return; }
    const nodeBy = Object.fromEntries(T.nodes.map((n) => [n.key, n]));
    const mudar = T.mudar ? nodeBy[T.mudar] : null;
    const books = [...new Set(T.chains.map((c) => c.book))];
    const bookTitle = Object.fromEntries(T.chains.map((c) => [c.book, c.book_title]));
    const companions = [...new Set(T.chains.map((c) => c.companion))].filter(Boolean);

    app.innerHTML = `
      <a class="back" href="#/h/${encodeURIComponent(id)}">رجوع إلى الحديث</a>
      <div class="h-head"><h1>شجرة الطرق</h1><div class="sub">كل روايات هذا الحديث في الكتب الستة، من النبي ﷺ إلى المصنفين.</div></div>
      <div class="tree-wrap">
        <aside class="panel">
          <div class="stats">
            <div><b id="s-routes">${T.summary.routes}</b><span>طريقًا</span></div>
            <div><b id="s-comp">${T.summary.companions}</b><span>صحابيًا</span></div>
            <div><b id="s-books">${T.summary.books.length}</b><span>كتب</span></div>
          </div>
          ${mudar ? `<p class="node-info" style="margin:12px 0 0"><b>نقطة تفرّع الطرق:</b> ${esc(mudar.label)}<br><span class="meter">يحسبها سند من عدد الطرق والفروع، وليست حكمًا علميًا.</span></p>` : ""}
          <h3>الصحابي</h3>
          <select id="f-comp"><option value="">كل الصحابة</option>${companions.map((c) => `<option>${esc(c)}</option>`).join("")}</select>
          <h3>الكتب</h3>
          ${books.map((b) => `<label><input type="checkbox" class="f-book" value="${b}" checked> ${esc(bookTitle[b])}</label>`).join("")}
          <label style="margin-top:6px"><input type="checkbox" id="f-sahih"> الصحيحان فقط</label>
          <h3>قرب الرواية من الحديث المختار</h3>
          <input type="range" id="f-sim" min="45" max="100" value="45" aria-label="أقل نسبة تشابه">
          <div class="meter" id="f-sim-v">كل الروايات (تشابه 45% فأكثر)</div>
          <label style="margin-top:10px"><input type="checkbox" id="f-mudar" checked> إبراز نقطة التفرّع</label>
          <h3>الرموز</h3>
          <div class="keys"><span><i></i>راوٍ</span><span><i class="d"></i>اسم قصير أو مشترك: الدمج غير مؤكد</span><span><i class="m"></i>نقطة تفرّع الطرق</span><span>سُمك الخط = عدد الطرق</span></div>
          <h3>تفاصيل</h3>
          <div class="node-info" id="info">اضغط على أي اسم لتظهر طرقه وحده.</div>
        </aside>
        <div id="cy" role="img" aria-label="رسم شجرة الإسناد"></div>
      </div>`;

    if (typeof cytoscape === "undefined") { document.getElementById("cy").innerHTML = `<p class="err" style="padding:20px">تعذّر تحميل مكتبة الرسم. تحقق من الاتصال.</p>`; return; }
    if (typeof cytoscapeDagre !== "undefined") cytoscape.use(cytoscapeDagre);

    const C = { brand: cssVar("--brand"), soft: cssVar("--brand-soft"), ink: cssVar("--ink"), muted: cssVar("--muted"), surface: cssVar("--surface"), line: cssVar("--line"), mudar: cssVar("--mudar"), paper: cssVar("--paper") };
    const cy = cytoscape({
      container: document.getElementById("cy"),
      elements: [
        ...T.nodes.map((n) => ({ data: { id: n.key, label: n.label, kind: n.kind, routes: n.chains.length, unc: n.uncertain ? 1 : 0 } })),
        ...T.edges.map((e) => ({ data: { id: e.source + ">" + e.target, source: e.source, target: e.target, routes: e.chains.length } })),
      ],
      wheelSensitivity: 0.25,
      minZoom: 0.15, maxZoom: 2.5,
      style: [
        { selector: "node", style: { label: "data(label)", "font-family": "IBM Plex Sans Arabic, sans-serif", "font-size": 13, color: C.ink, "text-valign": "center", "text-halign": "center",
          shape: "round-rectangle", width: "label", height: 30, padding: "10px", "background-color": C.surface, "border-width": 1.5, "border-color": C.muted, "text-wrap": "wrap", "text-max-width": 150 } },
        { selector: "node[kind='prophet']", style: { "background-color": C.brand, color: C.surface, "border-width": 0, "font-size": 16, "font-weight": 700, height: 38 } },
        { selector: "node[kind='companion']", style: { "background-color": C.soft, "border-color": C.brand, "font-weight": 600 } },
        { selector: "node[kind='book']", style: { shape: "round-rectangle", "background-color": C.ink, color: C.surface, "border-width": 0, "font-weight": 600 } },
        { selector: "node[unc=1]", style: { "border-style": "dashed" } },
        { selector: "node.mudar", style: { "border-color": C.mudar, "border-width": 4 } },
        { selector: "edge", style: { width: "mapData(routes, 1, 12, 1.5, 7)", "line-color": C.line, "curve-style": "taxi", "taxi-direction": "downward", "target-arrow-shape": "none" } },
        { selector: ".dim", style: { opacity: 0.12 } },
        { selector: "node.hl", style: { "border-color": C.brand, "border-width": 3 } },
        { selector: "edge.hl", style: { "line-color": C.brand } },
      ],
    });
    const layout = () => cy.elements(":visible").layout({ name: typeof cytoscapeDagre !== "undefined" ? "dagre" : "breadthfirst", rankDir: "TB", nodeSep: 14, rankSep: 46, directed: true, roots: "#prophet", animate: false, fit: true, padding: 20 }).run();

    const chainsById = Object.fromEntries(T.chains.map((c) => [c.id, c]));
    function apply() {
      const comp = document.getElementById("f-comp").value;
      const bset = new Set([...document.querySelectorAll(".f-book:checked")].map((x) => x.value));
      const sahih = document.getElementById("f-sahih").checked;
      const sim = +document.getElementById("f-sim").value / 100;
      document.getElementById("f-sim-v").textContent = sim <= 0.45 ? "كل الروايات (تشابه 45% فأكثر)" : `الروايات التي يشبه متنها الحديث المختار بنسبة ${Math.round(sim * 100)}% فأكثر`;
      const vis = T.chains.filter((c) => (!comp || c.companion === comp) && bset.has(c.book) && (!sahih || ["bukhari", "muslim"].includes(c.book)) && (c.similarity >= sim || c.id === id));
      const vn = new Set(vis.flatMap((c) => c.nodes));
      cy.batch(() => {
        cy.nodes().forEach((n) => n.style("display", vn.has(n.id()) ? "element" : "none"));
        cy.edges().forEach((e) => e.style("display", vn.has(e.source().id()) && vn.has(e.target().id()) && vis.some((c) => { const i = c.nodes.indexOf(e.source().id()); return i >= 0 && c.nodes[i + 1] === e.target().id(); }) ? "element" : "none"));
        cy.nodes().removeClass("mudar");
        if (T.mudar && document.getElementById("f-mudar").checked) cy.getElementById(T.mudar).addClass("mudar");
        cy.elements().removeClass("dim hl");
      });
      document.getElementById("s-routes").textContent = vis.length;
      document.getElementById("s-comp").textContent = new Set(vis.map((c) => c.companion)).size;
      document.getElementById("s-books").textContent = new Set(vis.map((c) => c.book)).size;
      layout();
    }
    ["f-comp", "f-sahih", "f-mudar"].forEach((i) => document.getElementById(i).addEventListener("change", apply));
    document.getElementById("f-sim").addEventListener("change", apply);
    document.getElementById("f-sim").addEventListener("input", () => { const v = +document.getElementById("f-sim").value; document.getElementById("f-sim-v").textContent = `تشابه ${v}% فأكثر`; });
    document.querySelectorAll(".f-book").forEach((x) => x.addEventListener("change", apply));

    const info = document.getElementById("info");
    cy.on("tap", "node", (ev) => {
      const n = nodeBy[ev.target.id()];
      const through = n.chains.map((c) => chainsById[c]).filter(Boolean);
      const keys = new Set(through.flatMap((c) => c.nodes));
      cy.batch(() => {
        cy.elements().addClass("dim").removeClass("hl");
        cy.nodes().filter((x) => keys.has(x.id())).removeClass("dim").addClass("hl");
        cy.edges().filter((e) => keys.has(e.source().id()) && keys.has(e.target().id())).removeClass("dim").addClass("hl");
      });
      const kindName = { prophet: "", companion: "صحابي", narrator: "راوٍ", book: "المصنف" }[n.kind];
      info.innerHTML = `<h4>${esc(n.label)}</h4>
        <div class="meter">${kindName}${n.uncertain ? " — اسم قصير أو مشترك؛ تحديد صاحبه غير مؤكد" : ""}</div>
        ${n.variants.length ? `<div class="meter">ورد أيضًا باسم: ${n.variants.map(esc).join("، ")}</div>` : ""}
        <p style="margin:8px 0 2px">يمر به ${through.length} ${through.length === 1 ? "طريق" : "طرق"}:</p>
        <ul>${through.slice(0, 30).map((c) => `<li><a href="#/h/${encodeURIComponent(c.id)}">${esc(c.book_title)}، رقم ${esc(c.number)}</a>${c.partial ? " <span class=\"meter\">(سند فيه تحويل)</span>" : ""}</li>`).join("")}</ul>`;
    });
    cy.on("tap", (ev) => { if (ev.target === cy) { cy.elements().removeClass("dim hl"); info.textContent = "اضغط على أي اسم لتظهر طرقه وحده."; } });
    apply();
  }

  // --------------------------------------------------------------- about
  function about() {
    app.className = "prose";
    app.innerHTML = `
      <h1>كيف يعمل سند؟</h1>
      <p>سند أداة تحقق. تلصق نصًا يُنسب إلى النبي ﷺ، فيبحث سند عنه في الكتب الستة، ثم يعرض النص كما ورد في مصدره، مع رقمه وكتابه وسنده، وشجرة كل طرقه.</p>
      <h2>ثلاث حالات فقط</h2>
      <div class="states">
        <div class="verdict found" style="margin:0"><b>موجود في المصادر:</b> وجدنا النص بلفظه أو بفروق يسيرة.</div>
        <div class="verdict near" style="margin:0"><b>يوجد حديث قريب بلفظ مختلف:</b> نعرض أقرب نص، ونلوّن الفروق.</div>
        <div class="verdict not_found" style="margin:0"><b>غير موجود في مصادر سند:</b> لم نجده في الكتب الستة. هذا ليس حكمًا بأنه موضوع.</div>
      </div>
      <h2>ما دور الذكاء الاصطناعي؟</h2>
      <p>يبحث ويرتّب ويقارن فقط. لا يؤلّف نصًا دينيًا، ولا يصدر حكمًا على حديث أو راوٍ. كل ما يظهر منقول من مصدره.</p>
      <ul>
        <li><b>البحث:</b> بحث نصي (BM25) على المتن بعد توحيد الكتابة العربية، مع تصحيح الأخطاء الإملائية بمقارنة أجزاء الكلمات.</li>
        <li><b>قرار الحالة:</b> يقيس سند كم من كلمات نصك وردت بالترتيب نفسه في المتن، مع وزن أكبر للكلمات النادرة.</li>
        <li><b>شجرة الطرق:</b> يجمع روايات الحديث الواحد بتشابه المتون، ثم يدمج الأسانيد من النبي ﷺ نزولًا. لا يُدمج اسمان إلا إذا كانا تحت الشيخ نفسه.</li>
      </ul>
      <h2>المصادر</h2>
      <p>الكتب الستة من <a href="https://github.com/ShathaTm/LK-Hadith-Corpus" target="_blank" rel="noopener">مدونة LK للحديث</a> (جامعة ليدز وجامعة الملك سعود): ${"34,088"} حديثًا، السند فيها مفصول عن المتن. فصل صحيح البخاري فيها مراجَع يدويًا، وبقية الكتب مفصولة آليًا بدقة نحو 92%.</p>
      <h2>حدود هذه النسخة</h2>
      <ul>
        <li>المصادر هي الكتب الستة فقط.</li>
        <li>الحكم يُعرض كما ورد في مجموعة البيانات، ونسبته إلى قائله تُضاف بعد مراجعة المتخصص.</li>
        <li>أسماء الرواة مستخرجة آليًا، ولا توجد صفحات تراجم بعد.</li>
        <li>البحث بالمعنى (Embeddings) ونموذج القرار المدرَّب يُضافان في أيام التحدي.</li>
      </ul>`;
  }

  // --------------------------------------------------------------- router
  function render() {
    const { parts, q } = parseHash();
    window.scrollTo(0, 0);
    if (parts[0] === "search") return searchPage(q.get("q") || "", q.get("mode") || "verify");
    if (parts[0] === "h" && parts[1]) return hadithPage(decodeURIComponent(parts[1]), q.get("q"));
    if (parts[0] === "tree" && parts[1]) return treePage(decodeURIComponent(parts[1]));
    if (parts[0] === "about") return about();
    return home();
  }
  window.addEventListener("hashchange", render);
  render();
})();
