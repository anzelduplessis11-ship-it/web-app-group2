/* ============================================================
   FarmConnect AI — Farm Translator widget
   ------------------------------------------------------------
   A drop-in language switcher that translates the visible page
   into the farmer's own language. Vanilla JS, no dependencies.

   • 20 African / regional languages + English (the original).
   • Translates text + placeholders/titles/labels on the page.
   • Caches every translation in localStorage, so a page stays
     translated even OFFLINE (matches FarmConnect's offline-first
     design) and repeat visits are instant.
   • Remembers the farmer's chosen language across pages.
   • Right-to-left layout for Arabic.
   • Works with ZERO backend (free browser translation) or with
     the bundled Flask endpoint for higher-quality translation.

   This file is standalone and is NOT wired into the app yet.
   See translator/README.md for how to add it when the site is
   finalised.  Public API:  window.FarmTranslator
   ============================================================ */
(function () {
  "use strict";

  /* ---------------- languages ----------------
     Each entry: primary backend code + optional alternates that
     are tried if the primary is not supported. `en` is the
     source/original — selecting it restores the page. */
  const LANGUAGES = [
    { code: "en", name: "English",             native: "English",       flag: "🌐", original: true },
    { code: "ar", name: "Arabic",              native: "العربية",        flag: "🇸🇦", rtl: true },
    { code: "sw", name: "Swahili",             native: "Kiswahili",     flag: "🇰🇪" },
    { code: "ha", name: "Hausa",               native: "Hausa",         flag: "🇳🇬" },
    { code: "yo", name: "Yoruba",              native: "Yorùbá",        flag: "🇳🇬" },
    { code: "ig", name: "Igbo",                native: "Igbo",          flag: "🇳🇬" },
    { code: "am", name: "Amharic",             native: "አማርኛ",          flag: "🇪🇹" },
    { code: "om", name: "Oromo",               native: "Afaan Oromoo",  flag: "🇪🇹" },
    { code: "so", name: "Somali",              native: "Soomaali",      flag: "🇸🇴" },
    { code: "zu", name: "Zulu",                native: "isiZulu",       flag: "🇿🇦" },
    { code: "xh", name: "Xhosa",               native: "isiXhosa",      flag: "🇿🇦" },
    { code: "sn", name: "Shona",               native: "chiShona",      flag: "🇿🇼" },
    { code: "rw", name: "Kinyarwanda",         native: "Ikinyarwanda",  flag: "🇷🇼" },
    { code: "ln", name: "Lingala",             native: "Lingála",       flag: "🇨🇩" },
    { code: "lg", name: "Luganda",             native: "Luganda",       flag: "🇺🇬" },
    { code: "wo", name: "Wolof",               native: "Wolof",         flag: "🇸🇳" },
    { code: "ff", name: "Fula (Fulfulde)",     native: "Fulfulde",      flag: "🌍" },
    { code: "bm", name: "Bambara",             native: "Bamanankan",    flag: "🇲🇱" },
    { code: "ber", name: "Berber (Tamazight)", native: "Tamaziɣt",      flag: "🇲🇦", alt: ["zgh", "tzm", "kab"] },
    { code: "ti", name: "Tigrinya",            native: "ትግርኛ",          flag: "🇪🇷" },
    { code: "ny", name: "Chichewa (Nyanja)",   native: "Chichewa",      flag: "🇲🇼" },
  ];

  /* ---------------- config ---------------- */
  const DEFAULTS = {
    languages: LANGUAGES,
    root: null,                 // element to translate (default: document.body)
    exclude: "[data-no-translate], .notranslate, script, style, noscript, code, pre, [translate='no']",
    attributes: ["placeholder", "title", "aria-label", "alt"],
    source: "en",               // the language the site is written in
    backends: ["google", "mymemory"], // client-side order; or ["server"]
    endpoint: null,             // e.g. "/api/translate" for the server backend
    email: null,                // MyMemory "de" param → raises the free daily limit
    position: "bottom-right",   // bottom-right | bottom-left | top-right | top-left
    mount: null,                // CSS selector to render inline instead of floating
    persist: true,              // remember the chosen language
    autoApply: true,            // re-apply the saved language on load
    concurrency: 6,             // parallel requests for client backends
    onReady: null,
    onTranslate: null,          // (langCode, {translated, failed}) => {}
  };

  /* ---------------- storage (mirrors the app's store helper) ---------------- */
  const LANG_KEY = "ft_lang";
  const CACHE_PREFIX = "ft_cache_";
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* quota — ignore */ } },
    raw(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
    setRaw(k, v) { try { localStorage.setItem(k, v); } catch { /* ignore */ } },
  };

  /* ---------------- module state ---------------- */
  const cfg = Object.assign({}, DEFAULTS);
  let state = {
    lang: "en",
    tracked: null,   // [{kind:'text'|'attr', node/el, attr?, original}]
    busy: false,
    mounted: false,
  };
  let els = {};      // widget DOM references

  const $ = (s, r = document) => r.querySelector(s);
  const hasLetters = (s) => /\p{L}/u.test(s);
  const langByCode = (c) => cfg.languages.find((l) => l.code === c);

  /* ---------------- small toast (uses the app's if present) ---------------- */
  function toast(msg, type) {
    if (window.AC && typeof window.AC.toast === "function") { window.AC.toast(msg, type); return; }
    let box = $("#ft-toast");
    if (!box) { box = document.createElement("div"); box.id = "ft-toast"; box.setAttribute("data-no-translate", ""); document.body.appendChild(box); }
    const el = document.createElement("div");
    el.className = "ft-toast-item" + (type === "error" ? " ft-toast-error" : "");
    el.textContent = msg;
    box.appendChild(el);
    setTimeout(() => { el.classList.add("ft-hide"); setTimeout(() => el.remove(), 350); }, 3200);
  }

  /* ================= TRANSLATION CACHE ================= */
  function cacheKey(code) { return CACHE_PREFIX + code; }
  function loadCache(code) { return store.get(cacheKey(code), {}); }
  function saveCache(code, map) { store.set(cacheKey(code), map); }

  /* ================= BACKENDS =================
     Each backend translates ONE string and returns the result.
     They throw on failure so the next backend in cfg.backends
     can be tried. `codesFor` yields the primary code + alternates. */
  function codesFor(lang) { return [lang.code].concat(lang.alt || []); }

  const backends = {
    // Google's public gtx endpoint — best coverage of African languages.
    async google(text, lang) {
      let lastErr;
      for (const code of codesFor(lang)) {
        try {
          const url = "https://translate.googleapis.com/translate_a/single?client=gtx"
            + "&sl=" + encodeURIComponent(cfg.source) + "&tl=" + encodeURIComponent(code)
            + "&dt=t&q=" + encodeURIComponent(text);
          const res = await fetch(url);
          if (!res.ok) throw new Error("HTTP " + res.status);
          const data = await res.json();
          const out = (data[0] || []).map((seg) => seg[0]).join("");
          if (out && out.trim()) return out;
          throw new Error("empty");
        } catch (e) { lastErr = e; }
      }
      throw lastErr || new Error("google failed");
    },

    // MyMemory — CORS-friendly fallback. Source cannot be "auto".
    async mymemory(text, lang) {
      let lastErr;
      for (const code of codesFor(lang)) {
        try {
          const src = cfg.source === "auto" ? "en" : cfg.source;
          let url = "https://api.mymemory.translated.net/get?q=" + encodeURIComponent(text)
            + "&langpair=" + encodeURIComponent(src) + "|" + encodeURIComponent(code);
          if (cfg.email) url += "&de=" + encodeURIComponent(cfg.email);
          const res = await fetch(url);
          if (!res.ok) throw new Error("HTTP " + res.status);
          const data = await res.json();
          const out = data && data.responseData && data.responseData.translatedText;
          if (out && !/^"?MYMEMORY WARNING/i.test(out) && data.responseStatus !== 403) return out;
          throw new Error("no result");
        } catch (e) { lastErr = e; }
      }
      throw lastErr || new Error("mymemory failed");
    },
  };

  // Try each configured client backend in order for a single string.
  async function translateOneClient(text, lang) {
    let lastErr;
    for (const name of cfg.backends) {
      const fn = backends[name];
      if (!fn) continue;
      try { return await fn(text, lang); }
      catch (e) { lastErr = e; }
    }
    throw lastErr || new Error("all backends failed");
  }

  // Server backend: translate the whole batch in ONE request.
  async function translateBatchServer(texts, lang) {
    const res = await fetch(cfg.endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ q: texts, target: lang.code, source: cfg.source }),
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    return data.translations || {};   // { original: translated }
  }

  /* ---- tiny concurrency pool for the client backends ---- */
  async function pool(items, limit, worker) {
    const results = new Array(items.length);
    let i = 0;
    const runners = Array.from({ length: Math.min(limit, items.length) }, async () => {
      while (i < items.length) {
        const idx = i++;
        try { results[idx] = await worker(items[idx], idx); }
        catch { results[idx] = undefined; }
      }
    });
    await Promise.all(runners);
    return results;
  }

  /* Translate a list of unique strings into `lang`, using cache first.
     Returns { map: {orig:trans}, failed: n }. */
  async function translateStrings(texts, lang) {
    const cache = loadCache(lang.code);
    const map = {};
    const missing = [];
    for (const t of texts) {
      if (cache[t] != null) map[t] = cache[t];
      else missing.push(t);
    }

    let failed = 0;
    if (missing.length) {
      if (!navigator.onLine) {
        // Offline: we can only use what's cached. Leave the rest as-is.
        failed = missing.length;
      } else {
        // 1) Try the server backend first (higher quality, shared cache).
        let remaining = missing;
        if (cfg.backends.includes("server") && cfg.endpoint) {
          try {
            const got = await translateBatchServer(remaining, lang);
            const still = [];
            for (const t of remaining) {
              if (got[t] != null && got[t] !== "") { map[t] = got[t]; cache[t] = got[t]; }
              else still.push(t);
            }
            remaining = still;
          } catch { /* server down/blocked -> fall through to client backends */ }
        }
        // 2) Anything the server couldn't do falls back to translating
        //    directly from the farmer's browser (their own connection is
        //    rarely blocked, unlike a cloud server's shared IP).
        const hasClientBackends = cfg.backends.some((b) => backends[b]);
        if (remaining.length && hasClientBackends) {
          const out = await pool(remaining, cfg.concurrency, (t) => translateOneClient(t, lang));
          remaining.forEach((t, k) => {
            const v = out[k];
            if (v != null && v !== "") { map[t] = v; cache[t] = v; }
            else failed++;
          });
        } else {
          failed += remaining.length;
        }
      }
      saveCache(lang.code, cache);
    }
    return { map, failed };
  }

  /* ================= DOM: collect / apply / restore ================= */
  function isExcluded(node) {
    const el = node.nodeType === 1 ? node : node.parentElement;
    if (!el) return true;
    if (els.root && els.root.contains(el)) return true;     // never translate the widget UI
    return !!el.closest(cfg.exclude);
  }

  // Build (once) the list of translatable text nodes + attributes, capturing
  // each English original so we can restore it later.
  function collect() {
    const root = cfg.root || document.body;
    const items = [];

    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const txt = node.nodeValue;
        if (!txt || !txt.trim() || !hasLetters(txt)) return NodeFilter.FILTER_REJECT;
        if (isExcluded(node)) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    let n;
    while ((n = walker.nextNode())) items.push({ kind: "text", node: n, original: n.nodeValue });

    if (cfg.attributes && cfg.attributes.length) {
      const sel = cfg.attributes.map((a) => "[" + a + "]").join(",");
      root.querySelectorAll(sel).forEach((el) => {
        if (isExcluded(el)) return;
        cfg.attributes.forEach((attr) => {
          const val = el.getAttribute(attr);
          if (val && val.trim() && hasLetters(val)) items.push({ kind: "attr", el, attr, original: val });
        });
      });
    }
    return items;
  }

  function tracked() {
    if (!state.tracked) state.tracked = collect();
    return state.tracked;
  }

  function uniqueOriginals() {
    const set = new Set();
    tracked().forEach((it) => set.add(it.original.trim()));
    return Array.from(set);
  }

  // Apply a translation map (keyed by trimmed original) or restore English.
  function apply(map /* null → restore */) {
    tracked().forEach((it) => {
      const key = it.original.trim();
      let value = it.original;
      if (map && map[key] != null) {
        // Preserve the original leading/trailing whitespace around the text.
        const lead = it.original.match(/^\s*/)[0];
        const trail = it.original.match(/\s*$/)[0];
        value = lead + map[key] + trail;
      }
      if (it.kind === "text") { if (it.node.nodeValue !== value) it.node.nodeValue = value; }
      else { it.el.setAttribute(it.attr, value); }
    });
  }

  function setDirection(lang) {
    const rtl = !!(lang && lang.rtl);
    const html = document.documentElement;
    if (rtl) { html.setAttribute("dir", "rtl"); html.classList.add("ft-rtl"); }
    else { if (html.getAttribute("dir") === "rtl") html.removeAttribute("dir"); html.classList.remove("ft-rtl"); }
  }

  /* ================= public: switch language ================= */
  async function setLanguage(code) {
    const lang = langByCode(code) || langByCode("en");
    if (state.busy) return;

    if (lang.original) {                 // back to English
      apply(null);
      setDirection(lang);
      state.lang = "en";
      if (cfg.persist) store.setRaw(LANG_KEY, "en");
      updateUI();
      return;
    }

    state.busy = true;
    setBusy(true);
    try {
      const originals = uniqueOriginals();
      const { map, failed } = await translateStrings(originals, lang);
      apply(map);
      setDirection(lang);
      state.lang = code;
      if (cfg.persist) store.setRaw(LANG_KEY, code);
      document.documentElement.setAttribute("lang", code);
      if (failed && navigator.onLine) toast("Some text couldn't be translated — showing it in English.", "error");
      else if (failed) toast("You're offline — text will finish translating when you reconnect.");
      if (typeof cfg.onTranslate === "function") cfg.onTranslate(code, { translated: originals.length - failed, failed });
    } catch (e) {
      toast("Translation is unavailable right now. Please try again.", "error");
    } finally {
      state.busy = false;
      setBusy(false);
      updateUI();
    }
  }

  // Re-scan the page (e.g. after new content was added) and re-apply.
  function retranslate() {
    state.tracked = null;
    if (state.lang && state.lang !== "en") return setLanguage(state.lang);
  }

  /* ================= WIDGET UI ================= */
  function currentLang() { return langByCode(state.lang) || langByCode("en"); }

  function buildUI() {
    const root = document.createElement("div");
    root.id = "ft-root";
    root.className = "ft-root ft-" + cfg.position;
    root.setAttribute("data-no-translate", "");
    root.setAttribute("translate", "no");
    root.dir = "ltr";

    root.innerHTML = `
      <button class="ft-launcher" type="button" aria-haspopup="dialog" aria-expanded="false"
              title="Choose your language / Chagua lugha yako">
        <span class="ft-launcher-globe">🌐</span>
        <span class="ft-launcher-label"></span>
        <span class="ft-launcher-caret" aria-hidden="true">▾</span>
      </button>

      <div class="ft-panel" role="dialog" aria-label="Language" hidden>
        <div class="ft-panel-head">
          <span class="ft-panel-title">🌍 Choose your language</span>
          <button class="ft-close" type="button" aria-label="Close">✕</button>
        </div>
        <div class="ft-search-wrap">
          <input class="ft-search" type="search" placeholder="Search language…" aria-label="Search language" autocomplete="off">
        </div>
        <div class="ft-progress" hidden><span class="ft-progress-bar"></span></div>
        <ul class="ft-list" role="listbox"></ul>
        <div class="ft-foot">Automatic translation — may not be perfect.</div>
      </div>
    `;

    // Optional inline mount, otherwise float over the page.
    const mountEl = cfg.mount ? document.querySelector(cfg.mount) : null;
    if (mountEl) { root.classList.add("ft-inline"); mountEl.appendChild(root); }
    else document.body.appendChild(root);

    els = {
      root,
      launcher: root.querySelector(".ft-launcher"),
      label: root.querySelector(".ft-launcher-label"),
      panel: root.querySelector(".ft-panel"),
      close: root.querySelector(".ft-close"),
      search: root.querySelector(".ft-search"),
      list: root.querySelector(".ft-list"),
      progress: root.querySelector(".ft-progress"),
    };

    renderList();
    wireEvents();
    updateUI();
  }

  function renderList(filter) {
    const q = (filter || "").trim().toLowerCase();
    els.list.innerHTML = "";
    cfg.languages
      .filter((l) => !q || l.name.toLowerCase().includes(q) || l.native.toLowerCase().includes(q) || l.code.includes(q))
      .forEach((l) => {
        const li = document.createElement("li");
        li.className = "ft-item" + (l.code === state.lang ? " ft-active" : "") + (l.original ? " ft-original" : "");
        li.setAttribute("role", "option");
        li.setAttribute("data-code", l.code);
        li.setAttribute("aria-selected", l.code === state.lang ? "true" : "false");
        li.innerHTML =
          '<span class="ft-flag">' + l.flag + "</span>"
          + '<span class="ft-names"><span class="ft-native">' + l.native + "</span>"
          + '<span class="ft-en">' + (l.original ? "Original" : l.name) + "</span></span>"
          + (l.code === state.lang ? '<span class="ft-check">✓</span>' : "");
        li.addEventListener("click", () => { closePanel(); setLanguage(l.code); });
        els.list.appendChild(li);
      });
  }

  function updateUI() {
    if (!els.label) return;
    const l = currentLang();
    els.label.textContent = l.original ? "Language" : l.native;
    els.root.classList.toggle("ft-is-translated", state.lang !== "en");
    renderList(els.search ? els.search.value : "");
  }

  function setBusy(b) {
    if (!els.progress) return;
    els.progress.hidden = !b;
    els.root.classList.toggle("ft-busy", b);
    els.launcher.disabled = b;
  }

  function openPanel() {
    els.panel.hidden = false;
    els.launcher.setAttribute("aria-expanded", "true");
    els.root.classList.add("ft-open");
    setTimeout(() => els.search && els.search.focus(), 50);
  }
  function closePanel() {
    els.panel.hidden = true;
    els.launcher.setAttribute("aria-expanded", "false");
    els.root.classList.remove("ft-open");
  }
  function togglePanel() { (els.panel.hidden ? openPanel : closePanel)(); }

  function wireEvents() {
    els.launcher.addEventListener("click", togglePanel);
    els.close.addEventListener("click", closePanel);
    els.search.addEventListener("input", () => renderList(els.search.value));
    document.addEventListener("click", (e) => {
      if (!els.root.contains(e.target)) closePanel();
    });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") closePanel(); });
  }

  /* ================= INIT ================= */
  function init(options) {
    Object.assign(cfg, options || {});
    if (state.mounted) { updateUI(); return api; }

    const start = () => {
      buildUI();
      state.mounted = true;
      // Restore the farmer's saved language.
      const saved = cfg.persist ? store.raw(LANG_KEY, "en") : "en";
      if (cfg.autoApply && saved && saved !== "en" && langByCode(saved)) {
        setLanguage(saved);
      }
      if (typeof cfg.onReady === "function") cfg.onReady(api);
    };

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
    else start();
    return api;
  }

  /* ================= PUBLIC API ================= */
  const api = {
    init,
    setLanguage,
    retranslate,
    languages: LANGUAGES,
    get current() { return state.lang; },
    clearCache() { cfg.languages.forEach((l) => { try { localStorage.removeItem(cacheKey(l.code)); } catch {} }); },
    _config: cfg,
  };
  window.FarmTranslator = api;

  // Auto-init if a config object was provided before this script loaded.
  if (window.FarmTranslatorConfig) init(window.FarmTranslatorConfig);
})();
