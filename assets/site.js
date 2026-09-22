// Theme toggle and copy-email. The inline pre-paint script in <head> has already applied a
// saved theme. The toggle stays hidden until this file adds "theme-ready", so it never shows dead.
(function () {
  var root = document.documentElement;
  var mq = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  var reduce = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;

  var btn = document.getElementById("theme-toggle");
  if (btn) {
    root.classList.add("theme-ready");
    var current = function () {
      var t = root.getAttribute("data-theme");
      if (t === "dark" || t === "light") return t;
      return mq && mq.matches ? "dark" : "light";
    };
    var sync = function () {
      btn.setAttribute("aria-pressed", current() === "dark" ? "true" : "false");
    };
    var apply = function (next) {
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
      var scheme = document.querySelector('meta[name="color-scheme"]');
      if (scheme) scheme.setAttribute("content", next);
      var color = next === "dark" ? "#0e1311" : "#f4f5f1";
      var metas = document.querySelectorAll('meta[name="theme-color"]');
      for (var i = 0; i < metas.length; i++) metas[i].setAttribute("content", color);
      sync();
    };
    btn.addEventListener("click", function () {
      var next = current() === "dark" ? "light" : "dark";
      if (document.startViewTransition && !(reduce && reduce.matches)) {
        document.startViewTransition(function () { apply(next); });
      } else {
        apply(next);
      }
    });
    if (mq && mq.addEventListener) mq.addEventListener("change", sync);
    sync();
  }

  // The mailto link works without JavaScript; the copy button only appears when this runs.
  var copy = document.getElementById("copy-email");
  var status = document.getElementById("copy-status");
  if (copy && status && navigator.clipboard && navigator.clipboard.writeText) {
    copy.hidden = false;
    var timer = null;
    var show = function (text, ms) {
      clearTimeout(timer);
      status.textContent = text;
      timer = setTimeout(function () { status.textContent = ""; }, ms);
    };
    copy.addEventListener("click", function () {
      status.textContent = "";
      navigator.clipboard.writeText(copy.getAttribute("data-email")).then(function () {
        show("Copied", 2000);
      }, function () {
        show("Copy failed, use the link", 6000);
      });
    });
  }
})();
