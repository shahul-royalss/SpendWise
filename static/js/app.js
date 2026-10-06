// Progressive enhancements: every page works without this file.
(function () {
  "use strict";

  var root = document.documentElement;
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Light / dark theme switch, remembered per browser.
  document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
    var sync = function () {
      var dark = root.getAttribute("data-bs-theme") === "dark";
      button.setAttribute("aria-pressed", String(dark));
      button.setAttribute("title", dark ? "Switch to light mode" : "Switch to dark mode");
    };
    sync();
    button.addEventListener("click", function () {
      var next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-bs-theme", next);
      try {
        window.localStorage.setItem("spendwise-theme", next);
      } catch (error) {
        // Storage can be unavailable (private mode); the switch still works for this page.
      }
      sync();
    });
  });

  // Count money and percentages up to their final value.
  var formatNumber = function (value, decimals) {
    return value.toLocaleString("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  };
  if (!reduceMotion) {
    document.querySelectorAll("[data-countup]").forEach(function (element) {
      var target = parseFloat(element.getAttribute("data-countup"));
      if (!isFinite(target)) {
        return;
      }
      var prefix = element.getAttribute("data-prefix") || "";
      var suffix = element.getAttribute("data-suffix") || "";
      var decimals = parseInt(element.getAttribute("data-decimals") || "2", 10);
      var finalText = element.textContent;
      var duration = 1200;
      var start = null;
      var step = function (timestamp) {
        if (start === null) {
          start = timestamp;
        }
        var progress = Math.min((timestamp - start) / duration, 1);
        var eased = 1 - Math.pow(1 - progress, 3);
        var current = target * eased;
        var sign = current < 0 ? "-" : "";
        element.textContent = sign + prefix + formatNumber(Math.abs(current), decimals) + suffix;
        if (progress < 1) {
          window.requestAnimationFrame(step);
        } else {
          element.textContent = finalText;
        }
      };
      window.requestAnimationFrame(step);
    });
  }

  // Toasts close themselves (warnings stay longer); the bar at the bottom shows the countdown.
  document.querySelectorAll(".toast[data-autohide]").forEach(function (toast) {
    var delay = parseInt(toast.getAttribute("data-autohide"), 10) || 6000;
    window.setTimeout(function () {
      if (window.bootstrap) {
        window.bootstrap.Toast.getOrCreateInstance(toast).hide();
      } else {
        toast.remove();
      }
    }, delay);
  });

  // Filter forms refresh as soon as a select or month changes.
  document.querySelectorAll("form[data-autosubmit]").forEach(function (form) {
    form.querySelectorAll("select, input[type=month]").forEach(function (input) {
      input.addEventListener("change", function () {
        if (form.requestSubmit) {
          form.requestSubmit();
        } else {
          form.submit();
        }
      });
    });
  });
})();
