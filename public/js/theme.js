/* Applies the saved theme before first paint (no inline scripts: CSP). */
(function () {
  try {
    var t = localStorage.getItem("sanad-theme");
    if (t === "light" || t === "dark") document.documentElement.setAttribute("data-theme", t);
  } catch (e) { /* storage unavailable: follow the system */ }
})();
