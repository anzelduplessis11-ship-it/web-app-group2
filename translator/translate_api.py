#!/usr/bin/env python3
"""
translate_api.py
================
An optional, higher-quality translation backend for the FarmConnect AI
Farm Translator widget.

It is a self-contained Flask *blueprint* built on the same free
GoogleTranslator backend as `sa_translator.py` (deep-translator, no API
key, no billing). Google covers the African languages this project targets
far better than the browser-only fallback, and doing the work server-side
lets us cache every translation so each phrase is only ever translated once.

It is NOT registered anywhere yet. To switch the widget over to it once the
site is finalised, see translator/README.md. In short:

    # app.py
    from translator.translate_api import translate_bp
    app.register_blueprint(translate_bp)

    # base.html widget config
    FarmTranslator.init({ backends: ["server"], endpoint: "/api/translate" });

Install the extra dependency:
    pip install deep-translator

Endpoints
---------
POST /api/translate
    body : {"q": ["Add Product", "My Orders"], "target": "sw", "source": "en"}
    reply: {"translations": {"Add Product": "Ongeza Bidhaa", "My Orders": "Maagizo Yangu"}}

GET  /api/translate/languages
    reply: {"languages": [{"code": "sw", "name": "Swahili", ...}, ...]}
"""
import json
import os
import threading

from flask import Blueprint, jsonify, request

try:
    from deep_translator import GoogleTranslator
    _HAVE_BACKEND = True
except Exception:  # deep-translator not installed yet
    GoogleTranslator = None
    _HAVE_BACKEND = False

translate_bp = Blueprint("translate", __name__)

MAX_CHARS = 4500  # GoogleTranslator caps each request near 5000 chars.
CACHE_PATH = os.path.join(os.path.dirname(__file__), "translation_cache.json")

# Same languages (and code fallbacks) the widget offers. Primary code first,
# alternates after — we keep the first the backend actually supports.
LANGUAGES = {
    "en":  {"name": "English",             "codes": ["en"]},
    "ar":  {"name": "Arabic",              "codes": ["ar"]},
    "sw":  {"name": "Swahili",             "codes": ["sw"]},
    "ha":  {"name": "Hausa",               "codes": ["ha"]},
    "yo":  {"name": "Yoruba",              "codes": ["yo"]},
    "ig":  {"name": "Igbo",                "codes": ["ig"]},
    "am":  {"name": "Amharic",             "codes": ["am"]},
    "om":  {"name": "Oromo",               "codes": ["om"]},
    "so":  {"name": "Somali",              "codes": ["so"]},
    "zu":  {"name": "Zulu",                "codes": ["zu"]},
    "xh":  {"name": "Xhosa",               "codes": ["xh"]},
    "sn":  {"name": "Shona",               "codes": ["sn"]},
    "rw":  {"name": "Kinyarwanda",         "codes": ["rw"]},
    "ln":  {"name": "Lingala",             "codes": ["ln"]},
    "lg":  {"name": "Luganda",             "codes": ["lg"]},
    "wo":  {"name": "Wolof",               "codes": ["wo"]},
    "ff":  {"name": "Fula (Fulfulde)",     "codes": ["ff", "ful"]},
    "bm":  {"name": "Bambara",             "codes": ["bm"]},
    "ber": {"name": "Berber (Tamazight)",  "codes": ["ber", "zgh", "tzm", "kab"]},
    "ti":  {"name": "Tigrinya",            "codes": ["ti"]},
    "ny":  {"name": "Chichewa (Nyanja)",   "codes": ["ny"]},
}

_cache_lock = threading.Lock()
_supported = None  # set of backend codes we confirmed at first use


# ----------------------------------------------------------------- cache
def _load_cache():
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


_CACHE = _load_cache()  # {"<target>": {"<source text>": "<translation>"}}


def _save_cache():
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as fh:
            json.dump(_CACHE, fh, ensure_ascii=False, indent=0)
    except Exception:
        pass  # a read-only disk shouldn't break translation


# ------------------------------------------------------------- backend
def _supported_codes():
    """Codes the live backend supports (queried once, then remembered)."""
    global _supported
    if _supported is not None:
        return _supported
    try:
        _supported = set(GoogleTranslator().get_supported_languages(as_dict=True).values())
    except Exception:
        _supported = set()  # couldn't verify — resolve() will fall back to primary
    return _supported


def _resolve(target):
    """Map a widget language key (e.g. 'sw') to a code the backend accepts."""
    entry = LANGUAGES.get(target)
    candidates = entry["codes"] if entry else [target]
    supported = _supported_codes()
    if supported:
        for code in candidates:
            if code in supported:
                return code
    return candidates[0]  # optimistic fallback (offline / unverified)


def _chunk(text, limit=MAX_CHARS):
    """Break long text into <=limit-sized pieces on word boundaries."""
    if len(text) <= limit:
        return [text]
    chunks, current = [], ""
    for word in text.split(" "):
        if len(current) + len(word) + 1 > limit:
            chunks.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        chunks.append(current)
    return chunks


def _translate_one(text, target_code, source_code):
    translator = GoogleTranslator(source=source_code or "auto", target=target_code)
    parts = [translator.translate(chunk) or "" for chunk in _chunk(text)]
    return " ".join(parts).strip()


# ------------------------------------------------------- reusable helpers
# These power the AI assistant's seamless translation flow (used from app.py):
# a farmer's question is translated to English, the AI answers in English, and
# the answer is translated back — all in the background. Both directions are
# cached so each phrase is translated only once.
def translate_text(text, target, source="en"):
    """Translate a single string between two widget language keys.

    ``target``/``source`` are widget keys such as "sw", "ha", "en". Unlike the
    page-widget route, this helper DOES translate *into* English (source lang
    -> "en"), which the assistant needs. It never raises: on any failure, or
    when no backend is available, it returns the original text so the caller
    can carry on.
    """
    text = text or ""
    target = (target or "en").strip()
    source = (source or "en").strip()
    if not text.strip() or target == source:
        return text
    if not _HAVE_BACKEND:
        return text

    pair = f"{source}->{target}"
    cache = _CACHE.setdefault(pair, {})
    key = text.strip()
    if key in cache:
        return cache[key]
    try:
        target_code = _resolve(target) if target != "en" else "en"
        source_code = _resolve(source) if source != "en" else "en"
        result = _translate_one(key, target_code, source_code)
        if result:
            cache[key] = result
            with _cache_lock:
                _save_cache()
            return result
    except Exception:
        pass
    return text


def to_english(text, source="auto"):
    """Translate a farmer's message into English.

    Defaults to auto-detection so it is robust even if the declared source
    language is wrong or the text is already partly English.
    """
    return translate_text(text, target="en", source=source or "auto")


def from_english(text, target):
    """Translate an English AI answer back into the farmer's language."""
    return translate_text(text, target=target, source="en")


def language_list():
    """The languages offered, as [{'code','name'}, ...] for UI menus."""
    return [{"code": key, "name": entry["name"]} for key, entry in LANGUAGES.items()]


# ------------------------------------------------------------- routes
@translate_bp.route("/api/translate", methods=["POST"])
def api_translate():
    data = request.get_json(silent=True) or {}
    target = (data.get("target") or "").strip()
    source = (data.get("source") or "en").strip()
    texts = data.get("q") or []
    if isinstance(texts, str):
        texts = [texts]

    # Nothing to do if there's no real language change. Note: target=="en"
    # is only a no-op when the SOURCE is also English (the page-widget's
    # case, translating the site's own English text) - it is NOT a no-op
    # for arbitrary content whose source isn't English, e.g. a message
    # typed in Swahili that a viewer wants translated into English.
    if not target or target == source or (target == "en" and source == "en"):
        return jsonify({"translations": {t: t for t in texts}})

    if not _HAVE_BACKEND:
        return jsonify({"translations": {}, "error": "backend_unavailable",
                        "detail": "Run: pip install deep-translator"}), 503

    target_code = _resolve(target)
    lang_cache = _CACHE.setdefault(target, {})

    translations, to_do, dirty = {}, [], False
    for t in texts:
        key = (t or "").strip()
        if not key:
            continue
        if key in lang_cache:
            translations[t] = lang_cache[key]
        else:
            to_do.append((t, key))

    for original, key in to_do:
        try:
            result = _translate_one(key, target_code, source)
            if result:
                lang_cache[key] = result
                translations[original] = result
                dirty = True
        except Exception:
            # Skip this phrase; the widget keeps the English original.
            continue

    if dirty:
        with _cache_lock:
            _save_cache()

    return jsonify({"translations": translations, "resolved": target_code})


@translate_bp.route("/api/translate/languages", methods=["GET"])
def api_languages():
    supported = _supported_codes()
    out = []
    for key, entry in LANGUAGES.items():
        resolved = _resolve(key)
        out.append({
            "code": key,
            "name": entry["name"],
            "resolved": resolved,
            "available": (not supported) or (resolved in supported) or key == "en",
        })
    return jsonify({"languages": out, "backend": _HAVE_BACKEND})


# Optional: run this file directly to smoke-test the endpoints on :5001.
if __name__ == "__main__":
    from flask import Flask

    demo = Flask(__name__)
    demo.register_blueprint(translate_bp)
    print("Translate API on http://127.0.0.1:5001  (POST /api/translate)")
    demo.run(port=5001, debug=True)
