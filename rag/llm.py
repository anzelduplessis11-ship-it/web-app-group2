"""Language-model client for FarmConnect AI.

FarmConnect AI is offline-first, so a **local** model is the default: no data
leaves the device, no API keys, works with a weak or absent network. By default
it talks to `Ollama <https://ollama.com>`_ over its local HTTP API
(``http://localhost:11434``), which is the simplest way to run models such as
Llama, Gemma or Phi on a laptop.

An **optional cloud model** (Anthropic's Claude API) can be enabled for higher
accuracy when the device has internet and an API key. Local stays the default;
the cloud path is only used when it is configured and — in ``auto`` mode — only
when no local model is reachable.

Everything degrades gracefully. If neither backend is available,
:func:`available` returns ``False`` and the assistant falls back to a grounded,
extractive answer built directly from the retrieved knowledge base (see
``rag/assistant.py``). The site is therefore fully functional with no model at
all — a model simply makes answers more fluent.

Configuration (environment variables)
-------------------------------------
Backend selection:
    FARMCONNECT_LLM_BACKEND     "auto" (default) | "local" | "cloud"
                                auto = prefer local, fall back to cloud.

Local model (Ollama):
    FARMCONNECT_LLM_HOST        default "http://localhost:11434"
    FARMCONNECT_LLM_MODEL       default "llama3.2" (any installed Ollama model)
    FARMCONNECT_LLM_TIMEOUT     default 120 (seconds for a generation request)
    FARMCONNECT_LLM_NUM_PREDICT default 480 (max tokens the local model emits)

Cloud model (Claude):
    FARMCONNECT_CLOUD_API_KEY   Anthropic API key (falls back to ANTHROPIC_API_KEY)
    FARMCONNECT_CLOUD_MODEL     default "claude-opus-4-8"
    FARMCONNECT_CLOUD_MAX_TOKENS default 1024

The older ``AGRICONNECT_LLM_*`` variable names are still honoured as aliases so
existing deployments keep working after the rename to FarmConnect AI.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request


def _env(name: str, default: str) -> str:
    """Read a FARMCONNECT_* variable, falling back to the legacy AGRICONNECT_*
    name so pre-rename deployments keep working."""
    if name in os.environ:
        return os.environ[name]
    legacy = name.replace("FARMCONNECT_", "AGRICONNECT_", 1)
    return os.environ.get(legacy, default)


# --- Backend selection ------------------------------------------------------
BACKEND = _env("FARMCONNECT_LLM_BACKEND", "auto").strip().lower()

# --- Local (Ollama) configuration -------------------------------------------
HOST = _env("FARMCONNECT_LLM_HOST", "http://localhost:11434").rstrip("/")
MODEL = _env("FARMCONNECT_LLM_MODEL", "llama3.2")
TIMEOUT = float(_env("FARMCONNECT_LLM_TIMEOUT", "120"))
# Cap the answer length so a slow CPU model can't run away; keeps latency sane.
NUM_PREDICT = int(_env("FARMCONNECT_LLM_NUM_PREDICT", "480"))

# --- Cloud (Claude) configuration -------------------------------------------
CLOUD_API_KEY = _env("FARMCONNECT_CLOUD_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
CLOUD_MODEL = _env("FARMCONNECT_CLOUD_MODEL", "claude-opus-4-8")
CLOUD_MAX_TOKENS = int(_env("FARMCONNECT_CLOUD_MAX_TOKENS", "1024"))

# Cache the availability probe for a short while so we don't hit the socket on
# every request; None means "not yet checked".
_available_cache: dict = {"ok": None}
_anthropic_client = None  # lazily constructed Anthropic() client


# ---------------------------------------------------------------------------
# Local backend (Ollama)
# ---------------------------------------------------------------------------
def _get(path: str, timeout: float = 3.0) -> dict | None:
    try:
        # Avoid a system proxy silently swallowing a localhost call and hanging.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"{HOST}{path}", timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def installed_models() -> list[str]:
    tags = _get("/api/tags")
    if not tags:
        return []
    return [m.get("name", "") for m in tags.get("models", [])]


def _local_available() -> bool:
    tags = _get("/api/tags")
    return bool(tags and tags.get("models"))


def _resolve_model() -> str:
    """Prefer the configured local model; otherwise use whatever is installed.

    Matching is case-insensitive and tag-tolerant, so ``FARMCONNECT_LLM_MODEL``
    values like ``qwen3.5`` match an installed ``Qwen3.5:latest`` and ``llama3.2``
    matches ``llama3.2:latest``.
    """
    names = installed_models()
    if not names:
        return MODEL
    want = MODEL.lower()
    want_base = want.split(":")[0]
    for n in names:
        if n.lower() == want or n.split(":")[0].lower() == want_base:
            return n
    return names[0]


# Strip any inline chain-of-thought a "thinking" model leaves in its answer.
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _post_generate(payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{HOST}/api/generate", data=data,
        headers={"Content-Type": "application/json"},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _generate_local(prompt: str, system: str | None, temperature: float) -> str:
    payload = {
        "model": _resolve_model(),
        "prompt": prompt,
        "system": system or "",
        "stream": False,
        # Disable chain-of-thought for "thinking" models (Qwen3, DeepSeek-R1):
        # this is grounded factual Q&A, not a reasoning task, so we want the
        # answer directly — faster, and it doesn't spend scarce memory/time on
        # reasoning we would only strip out anyway.
        "think": False,
        "options": {
            "temperature": temperature,
            "num_ctx": 4096,          # trimmed context fits comfortably
            "num_predict": NUM_PREDICT,
        },
    }
    try:
        body = _post_generate(payload)
    except urllib.error.HTTPError as e:
        # Older Ollama builds reject the `think` field — retry once without it
        # so we stay compatible across versions.
        detail = ""
        try:
            detail = e.read().decode("utf-8", "ignore")
        except Exception:
            pass
        if "think" in detail.lower():
            payload.pop("think", None)
            body = _post_generate(payload)
        else:
            raise
    # Some thinking models return their reasoning in a separate field; prefer
    # the visible answer and strip any leftover inline <think>…</think>.
    text = (body.get("response") or "").strip()
    text = _THINK_RE.sub("", text).strip()
    if not text:
        raise RuntimeError("Empty response from local model.")
    return text


# ---------------------------------------------------------------------------
# Cloud backend (Claude / Anthropic)
# ---------------------------------------------------------------------------
def _cloud_configured() -> bool:
    """Is the cloud path usable: a key is set and the SDK is importable?"""
    if not CLOUD_API_KEY:
        return False
    try:
        import anthropic  # noqa: F401
    except Exception:
        return False
    return True


def _cloud_client():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        _anthropic_client = anthropic.Anthropic(api_key=CLOUD_API_KEY, timeout=TIMEOUT)
    return _anthropic_client


def _generate_cloud(prompt: str, system: str | None) -> str:
    """One grounded generation via the Claude API.

    Thinking is left off: this is a short, grounded, factual answer, not a
    reasoning task, so we keep it fast and cheap. The system prompt already
    forbids inventing anything outside the provided context.
    """
    client = _cloud_client()
    resp = client.messages.create(
        model=CLOUD_MODEL,
        max_tokens=CLOUD_MAX_TOKENS,
        system=system or "",
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(
        b.text for b in resp.content if getattr(b, "type", None) == "text"
    ).strip()
    if not text:
        raise RuntimeError("Empty response from cloud model.")
    return text


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def active_backend() -> str | None:
    """Which backend a generation would use right now: 'local', 'cloud', or None.

    In ``auto`` mode local is preferred (offline-first) and cloud is the
    fallback. ``local`` / ``cloud`` force one backend.
    """
    if BACKEND == "local":
        return "local" if _local_available() else None
    if BACKEND == "cloud":
        return "cloud" if _cloud_configured() else None
    # auto: local first, cloud fallback.
    if _local_available():
        return "local"
    if _cloud_configured():
        return "cloud"
    return None


def available(refresh: bool = False) -> bool:
    """Is any usable model reachable right now? Cheap, cached, never raises.

    Only a *positive* result is cached: if the first probe fails (e.g. Ollama
    is still cold-starting), later calls will re-probe so the assistant starts
    using the model as soon as it comes up, without a server restart.
    """
    if not refresh and _available_cache["ok"] is True:
        return True
    ok = active_backend() is not None
    _available_cache["ok"] = ok or None
    return ok


def generate(prompt: str, system: str | None = None,
             temperature: float = 0.2) -> str:
    """Run a single grounded generation, raising on any failure so the caller
    can fall back cleanly to the extractive answer.

    Uses a low temperature for the local model because this is a factual,
    grounded assistant — it should stick to the retrieved context, not be
    creative. (The cloud path controls determinism through prompting.)
    """
    backend = active_backend()
    if backend == "cloud":
        return _generate_cloud(prompt, system)
    if backend == "local":
        return _generate_local(prompt, system, temperature)
    raise RuntimeError("No language-model backend is available.")


def info() -> dict:
    """Backend diagnostics for the status probe and README."""
    backend = active_backend()
    return {
        "backend": backend,
        "mode": BACKEND,
        "local_host": HOST,
        "local_models": installed_models(),
        "cloud_configured": _cloud_configured(),
        "cloud_model": CLOUD_MODEL if _cloud_configured() else None,
    }
