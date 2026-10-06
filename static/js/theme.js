// Runs in <head> before the page paints, so the saved colour theme is applied
// without a flash. Kept as a file (not inline) to satisfy the CSP.
(function () {
  "use strict";
  var root = document.documentElement;
  var saved = null;
  try {
    saved = window.localStorage.getItem("spendwise-theme");
  } catch (error) {
    saved = null;
  }
  var prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  var theme = saved === "dark" || saved === "light" ? saved : prefersDark ? "dark" : "light";
  root.setAttribute("data-bs-theme", theme);
})();
