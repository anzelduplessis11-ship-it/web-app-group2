"""Supabase client helpers for FarmConnect AI.

Two kinds of client:

* **service client** — authenticated with the service-role key. Used by the
  Flask server for trusted, server-side data operations (marketplace listings,
  messages, community posts, ratings) and by the KB ingestion script. It
  bypasses Row Level Security, so the app must enforce its own access checks
  (it already does, via login/role decorators).

* **auth client** — authenticated with the publishable/anon key. Used for the
  Supabase Auth phone-OTP sign-in/verify flow.

Both are created lazily and cached, so we open one connection per process.
"""
from __future__ import annotations

import config

_service_client = None
_auth_client = None


def _make(key: str):
    from supabase import create_client
    if not config.SUPABASE_URL or not key:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and the API keys in .env "
            "(see .env.example)."
        )
    return create_client(config.SUPABASE_URL, key)


def service():
    """Server-side client (service-role key). Bypasses RLS — server use only."""
    global _service_client
    if _service_client is None:
        _service_client = _make(config.SUPABASE_SERVICE_ROLE_KEY or config.SUPABASE_ANON_KEY)
    return _service_client


def auth_client():
    """Anon-key client, used for the Supabase Auth phone-OTP flow."""
    global _auth_client
    if _auth_client is None:
        _auth_client = _make(config.SUPABASE_ANON_KEY)
    return _auth_client


def available() -> bool:
    return config.supabase_ready()
