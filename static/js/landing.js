/* ============================================================================
   FarmConnect — cover page interactions (light theme).
   Vanilla JS, no dependencies. Everything is progressive: the page is fully
   readable if this never runs; JS only adds motion and the small demos.
   ============================================================================ */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ------------------------- reveal on scroll ------------------------- */
  function initReveal() {
    if (reduce) { $$(".reveal").forEach((el) => el.classList.add("is-in")); return; }
    const io = new IntersectionObserver((es) => {
      es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); } });
    }, { threshold: 0.14, rootMargin: "0px 0px -6% 0px" });
    $$(".reveal").forEach((el) => io.observe(el));
  }

  /* ------------------------- count-up stats ------------------------- */
  function initCounters() {
    const run = (el) => {
      const target = +el.dataset.target || 0, dur = 1500, t0 = performance.now();
      (function tick(now) {
        const p = Math.min(1, (now - t0) / dur);
        el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3))).toLocaleString();
        if (p < 1) requestAnimationFrame(tick);
      })(t0);
    };
    if (reduce) { $$(".counter").forEach((el) => (el.textContent = (+el.dataset.target || 0).toLocaleString())); return; }
    const io = new IntersectionObserver((es) => {
      es.forEach((e) => { if (e.isIntersecting) { run(e.target); io.unobserve(e.target); } });
    }, { threshold: 0.4 });
    $$(".counter").forEach((el) => io.observe(el));
  }

  /* ---------------------- nav: shrink + scrollspy + smooth scroll ---------------------- */
  function initNav() {
    const nav = $("#lpNav");
    const links = $$(".lp-navlinks a[href^='#']");
    const onScroll = () => { if (nav) nav.classList.toggle("scrolled", scrollY > 20); };
    addEventListener("scroll", onScroll, { passive: true }); onScroll();

    const map = {};
    links.forEach((l) => { const id = l.getAttribute("href").slice(1); if (id) map[id] = l; });
    const spy = new IntersectionObserver((es) => {
      es.forEach((e) => {
        if (e.isIntersecting) {
          links.forEach((l) => l.classList.remove("active"));
          if (map[e.target.id]) map[e.target.id].classList.add("active");
        }
      });
    }, { rootMargin: "-45% 0px -45% 0px" });
    ["how", "market", "farmers", "ai"].forEach((id) => { const el = document.getElementById(id); if (el) spy.observe(el); });

    $$("a[href^='#']").forEach((a) => a.addEventListener("click", (e) => {
      const href = a.getAttribute("href");
      if (href.length > 1) { const el = $(href); if (el) { e.preventDefault(); el.scrollIntoView({ behavior: reduce ? "auto" : "smooth" }); } }
    }));
  }

  /* ------------------------- marketplace cart demo ------------------------- */
  function initCart() {
    const mc = $("#miniCart"), n = $("#miniCartN"); let count = 0;
    $$("[data-cart]").forEach((btn) => btn.addEventListener("click", (e) => {
      e.preventDefault(); count++;
      if (n) n.textContent = count;
      if (mc) { mc.classList.add("show"); mc.classList.remove("bump"); void mc.offsetWidth; mc.classList.add("bump"); }
      if (!reduce && mc) {
        const b = btn.getBoundingClientRect(), t = mc.getBoundingClientRect();
        const fly = document.createElement("div"); fly.textContent = "🧺";
        Object.assign(fly.style, { position: "fixed", left: b.left + b.width / 2 + "px", top: b.top + "px",
          fontSize: "1.4rem", zIndex: 9500, pointerEvents: "none", transition: "all .7s cubic-bezier(.5,-.3,.7,1)" });
        document.body.appendChild(fly);
        requestAnimationFrame(() => { fly.style.left = t.left + "px"; fly.style.top = t.top + "px"; fly.style.transform = "scale(.3)"; fly.style.opacity = "0"; });
        setTimeout(() => fly.remove(), 720);
      }
    }));
  }

  /* ------------------------- farmer selection demo ------------------------- */
  function initFarmers() {
    const cards = $$("#farmerCards .lp-farmer-card");
    $$("#farmerCards [data-select]").forEach((btn) => btn.addEventListener("click", (e) => {
      e.preventDefault();
      const card = btn.closest(".lp-farmer-card");
      const already = card.classList.contains("chosen");
      cards.forEach((c) => c.classList.remove("chosen", "dimmed"));
      $$("#farmerCards [data-select]").forEach((b) => (b.textContent = "Select farmer"));
      if (!already) {
        card.classList.add("chosen");
        cards.forEach((c) => { if (c !== card) c.classList.add("dimmed"); });
        btn.textContent = "✓ Selected";
      }
    }));
  }

  /* ------------------------- messaging typing reveal ------------------------- */
  function initMessaging() {
    const body = $("#chatBody"); if (!body) return;
    const bubs = $$(".lp-pbub", body);
    if (reduce) { bubs.forEach((b) => b.classList.add("in")); return; }
    let played = false;
    const io = new IntersectionObserver((es) => {
      es.forEach((e) => {
        if (e.isIntersecting && !played) {
          played = true; io.disconnect();
          let d = 250;
          bubs.forEach((b) => { setTimeout(() => b.classList.add("in"), d); d += 700; });
        }
      });
    }, { threshold: 0.35 });
    io.observe(body);
  }

  /* ------------------------- offline steps reveal ------------------------- */
  function initOffline() {
    const wrap = $("#offlineSteps"); if (!wrap) return;
    const steps = $$(".lp-ostep", wrap);
    if (reduce) { steps.forEach((s) => s.classList.add("on")); return; }
    let played = false;
    const io = new IntersectionObserver((es) => {
      es.forEach((e) => {
        if (e.isIntersecting && !played) {
          played = true; io.disconnect();
          steps.forEach((s, i) => setTimeout(() => s.classList.add("on"), i * 500));
        }
      });
    }, { threshold: 0.3 });
    io.observe(wrap);
  }

  /* ------------------------- montage auto-scroll ------------------------- */
  function initMontage() {
    const track = $("#montageTrack"); if (!track) return;
    // Duplicate the cards once so the pan can loop seamlessly.
    track.innerHTML += track.innerHTML;
    if (reduce) return;
    let paused = false;
    ["mouseenter", "touchstart", "pointerdown"].forEach((e) =>
      track.addEventListener(e, () => { paused = true; }, { passive: true }));
    track.addEventListener("mouseleave", () => { paused = false; });
    (function tick() {
      if (!paused) {
        const half = track.scrollWidth / 2;
        track.scrollLeft += 0.5;
        if (track.scrollLeft >= half) track.scrollLeft -= half;
      }
      requestAnimationFrame(tick);
    })();
  }

  /* -------------------------------- boot -------------------------------- */
  function boot() {
    initReveal(); initCounters(); initNav(); initCart();
    initFarmers(); initMessaging(); initOffline(); initMontage();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
