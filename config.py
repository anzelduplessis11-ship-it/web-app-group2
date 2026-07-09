"""Central configuration for FarmConnect AI.

All secrets and connection details live in environment variables (loaded from a
local ``.env`` file in development). Nothing sensitive is hard-coded. Copy
``.env.example`` to ``.env`` and fill in the blanks — see the README / setup
walkthrough.

This is the single "environment" that carries the Supabase login/API details and
the Hugging Face token between the app and those services.
"""
from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
    load_dotenv()  # read .env into the environment if present
except Exception:
    pass  # python-dotenv is optional; real env vars still work without it


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


# --- Flask ------------------------------------------------------------------
FLASK_SECRET_KEY = _get("FLASK_SECRET_KEY", "dev-only-change-me")

# --- Supabase ---------------------------------------------------------------
SUPABASE_URL = _get("SUPABASE_URL")
# Publishable/anon key — safe for client-side use, RLS-protected.
SUPABASE_ANON_KEY = _get("SUPABASE_ANON_KEY")
# Service-role key — SERVER ONLY. Bypasses RLS; never expose to the browser.
SUPABASE_SERVICE_ROLE_KEY = _get("SUPABASE_SERVICE_ROLE_KEY")
# Postgres connection string (URI) for the app's data layer (db.py). Get it from
# Dashboard > Project Settings > Database > Connection string.
SUPABASE_DB_URL = _get("SUPABASE_DB_URL")

# --- Hugging Face -----------------------------------------------------------
HF_TOKEN = _get("HF_TOKEN")
# Serverless instruct model used to write the final answer.
HF_CHAT_MODEL = _get("HF_CHAT_MODEL", "Qwen/Qwen2.5-7B-Instruct")
# Embedding model — its output dimension MUST match the vector(N) column in the
# kb_chunks table (all-MiniLM-L6-v2 -> 384). Change both together.
HF_EMBED_MODEL = _get("HF_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
HF_PROVIDER = _get("HF_PROVIDER", "hf-inference")

# --- Backend selection ------------------------------------------------------
# Where retrieval runs: "supabase" (pgvector + HF embeddings) or "local"
# (the offline BM25+TF-IDF engine in rag/retriever.py).
RAG_BACKEND = _get("FARMCONNECT_RAG_BACKEND", "supabase").lower()
# Which model writes answers: "hf" (Hugging Face), "cloud" (Claude), "local"
# (Ollama), or "auto" (try in that order).
LLM_BACKEND = _get("FARMCONNECT_LLM_BACKEND", "hf").lower()


def supabase_ready() -> bool:
    return bool(SUPABASE_URL and (SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY))


def hf_ready() -> bool:
    return bool(HF_TOKEN)


def missing() -> list[str]:
    """Names of required settings that are not yet configured."""
    gaps = []
    if not SUPABASE_URL:
        gaps.append("SUPABASE_URL")
    if not SUPABASE_ANON_KEY:
        gaps.append("SUPABASE_ANON_KEY")
    if not SUPABASE_SERVICE_ROLE_KEY:
        gaps.append("SUPABASE_SERVICE_ROLE_KEY")
    if not HF_TOKEN:
        gaps.append("HF_TOKEN")
    return gaps
