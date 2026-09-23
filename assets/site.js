// Theme toggle, copy-email and click-to-play videos. The inline pre-paint script in <head> has already applied a
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

  // Videos: each thumbnail is a plain link to YouTube. A plain click swaps it for the
  // youtube-nocookie player in place, so nothing loads from YouTube until someone asks.
  // Modified and middle clicks still open YouTube as a normal link would.
  document.addEventListener("click", function (e) {
    var link = e.target && e.target.closest ? e.target.closest("a.yt") : null;
    if (!link || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var id = link.getAttribute("data-yt") || "";
    if (!/^[A-Za-z0-9_-]{11}$/.test(id)) return;
    e.preventDefault();
    var frame = document.createElement("iframe");
    frame.setAttribute("src", "https://www.youtube-nocookie.com/embed/" + id + "?autoplay=1&rel=0");
    frame.setAttribute("title", link.getAttribute("data-title") || "YouTube video");
    frame.setAttribute("allow", "autoplay; encrypted-media; picture-in-picture; fullscreen");
    // The embed refuses to play without a referrer (error 153).
    frame.setAttribute("referrerpolicy", "strict-origin-when-cross-origin");
    link.parentNode.replaceChild(frame, link);
    frame.focus();
  });
})();
