/* Applies the saved theme before first paint (no inline scripts: CSP).
   Light by default; "auto" follows the system. */
(function () {
  var t = "light";
  try {
    var s = localStorage.getItem("sanad-theme");
    if (s === "light" || s === "dark" || s === "auto") t = s;
  } catch (e) { /* storage unavailable: stay light */ }
  document.documentElement.setAttribute("data-theme", t);
})();
