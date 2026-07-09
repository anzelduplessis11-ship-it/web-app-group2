# 🌐 FarmConnect AI — Farm Translator

A drop-in language widget that lets farmers read FarmConnect in **their own language**.
It adds a floating 🌐 button; tapping it lets the farmer pick a language and the whole
page is translated for them. It is **standalone and not yet wired into the app** — this
folder is self-contained so you can add it whenever the site is finalised.

## Languages (20 + English)

Arabic · Swahili · Hausa · Yoruba · Igbo · Amharic · Oromo · Somali · Zulu · Xhosa ·
Shona · Kinyarwanda · Lingala · Luganda · Wolof · Fula (Fulfulde) · Bambara ·
Berber (Tamazight) · Tigrinya · Chichewa (Nyanja) — plus **English** (the original).

Each is shown in its own script (e.g. **Kiswahili**, **العربية**, **አማርኛ**) so a farmer
can find their language without reading English.

## Files

| File | What it is |
|------|-----------|
| `farm-translator.js`   | The widget — vanilla JS, no dependencies, matches the app's `window.AC` style. |
| `farm-translator.css`  | Styling, themed to FarmConnect (greens/gold/cream), mobile bottom-sheet, RTL for Arabic. |
| `translator_demo.html` | **Standalone preview** — open it in a browser to try the translator with no server. |
| `translate_api.py`     | Optional Flask backend (reuses your `sa_translator.py` approach) for best quality. |
| `README.md`            | This file. |

## ▶️ Try it right now (no setup)

Just open **`translator_demo.html`** in any browser and tap the 🌐 button (bottom-right).
It translates in the browser using a free service, so there's nothing to install or run.

---

## How it works

- **Translates the visible page** — headings, paragraphs, buttons, and also
  `placeholder` / `title` / `aria-label` / `alt` text.
- **Caches every translation** in `localStorage`. So a page a farmer has seen once stays
  translated **even offline** — this matches FarmConnect's offline-first design — and
  repeat visits are instant.
- **Remembers the language** the farmer picked, across pages and sessions.
- **Right-to-left** layout is applied automatically for Arabic.
- **Never translates** things marked `data-no-translate`, `.notranslate`, `translate="no"`,
  or inside `<script>`, `<style>`, `<code>`, `<pre>`. Prices/numbers (text with no letters)
  are left untouched, so `KSh 1,200` stays correct.

### Two translation backends

1. **Browser (default)** — zero setup. Calls Google's free endpoint with a MyMemory
   fallback. Great for the demo and for static hosting.
2. **Server (recommended for production)** — `translate_api.py`, built on the same
   `deep-translator` + Google backend as your `sa_translator.py`. Higher quality on
   African languages and it caches each phrase on the server so it's translated only once.

---

## Adding it to the app later (when the site is finalised)

**Do this only when you're ready — nothing below has been applied yet.**

### 1. Move the two front-end files into `static/`

```
static/js/farm-translator.js      ←  translator/farm-translator.js
static/css/farm-translator.css     ←  translator/farm-translator.css
```

### 2. Load them in `templates/base.html`

In `<head>`, next to the existing stylesheet:

```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/farm-translator.css') }}">
```

Just before `</body>` (after `app.js`):

```html
<script src="{{ url_for('static', filename='js/farm-translator.js') }}" defer></script>
<script>
  window.addEventListener("DOMContentLoaded", function () {
    FarmTranslator.init({
      position: "bottom-right"
      // Uses the free browser backend by default.
      // For the server backend, add:  backends: ["server"], endpoint: "/api/translate"
    });
  });
</script>
```

That's it — the 🌐 button appears on every page.

> **Tip:** to put the picker *inside* your sidebar/topbar instead of floating, add a
> container in `base.html` (e.g. `<div id="langPicker"></div>`) and pass `mount: "#langPicker"`.

### 3. (Optional) Turn on the high-quality server backend

```bash
pip install deep-translator          # add "deep-translator>=1.11" to requirements.txt
```

```python
# app.py — near the other imports / blueprint setup
from translator.translate_api import translate_bp
app.register_blueprint(translate_bp)
```

Then change the widget config to:

```js
FarmTranslator.init({ backends: ["server"], endpoint: "/api/translate" });
```

(Keep `translate_api.py` in a `translator/` package with an `__init__.py`, or move it
next to `app.py` and import it as `from translate_api import translate_bp`.)

---

## Configuration options

```js
FarmTranslator.init({
  position: "bottom-right",        // bottom-right | bottom-left | top-right | top-left
  mount: null,                      // CSS selector to render inline instead of floating
  backends: ["google", "mymemory"],// or ["server"]
  endpoint: null,                   // "/api/translate" for the server backend
  email: null,                      // your email → raises the free MyMemory daily limit
  root: null,                       // element to translate (default: document.body)
  exclude: "[data-no-translate], .notranslate, script, style, code, pre",
  attributes: ["placeholder", "title", "aria-label", "alt"],
  persist: true,                    // remember the farmer's language
});

// Handy methods:
FarmTranslator.setLanguage("sw");   // switch programmatically
FarmTranslator.retranslate();       // re-run after you inject new content (AJAX)
FarmTranslator.clearCache();        // wipe cached translations
```

## Good to know

- **Machine translation isn't perfect.** For the most critical instructions you may later
  want a human to check the translations — the server cache (`translation_cache.json`) is
  plain JSON you can hand-edit to correct any phrase.
- **Coverage varies.** Widely spoken languages (Swahili, Hausa, Arabic, Amharic, Zulu…)
  translate very well. A few (e.g. Wolof, Fula, Berber) have thinner support; if the
  backend can't translate a phrase, the widget safely keeps the English text and tells the
  farmer, rather than showing anything broken.
- **User-generated content** (product names farmers type, chat messages) is translated too
  by default. If you'd rather leave, say, live chat messages untouched, add
  `data-no-translate` to that container.
