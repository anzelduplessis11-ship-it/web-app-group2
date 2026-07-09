"""
db.py
-----
Data access for FarmConnect AI. The store is now **Supabase Postgres** instead
of a local SQLite file — but the app's login flow and route code are unchanged.
This module keeps the same tiny helper API it always had:

    query_one(sql, params) -> one row (dict) or None
    query_all(sql, params) -> list of rows (dicts)
    execute(sql, params)   -> new row id (for INSERT ... RETURNING id) or rowcount

Tables (all in Supabase): users, listings, messages, ratings, community_posts.

We connect with a privileged Postgres role using the connection string in
SUPABASE_DB_URL (see .env.example). Get it from the Supabase dashboard:
  Project Settings > Database > Connection string (URI).

SQL uses '?' placeholders (as before); this adapter rewrites them to Postgres
'%s' automatically, so the queries in app.py/trends.py read the same.
"""
from __future__ import annotations

from pathlib import Path

from flask import g

import config

DB_PATH = Path(__file__).parent / "data" / "farmconnect.db"  # legacy; no longer used


def _dsn() -> str:
    dsn = config.SUPABASE_DB_URL
    if not dsn:
        raise RuntimeError(
            "SUPABASE_DB_URL is not set. Put your Supabase Postgres connection "
            "string in .env (Dashboard > Project Settings > Database > Connection string)."
        )
    return dsn


# A small shared pool of Postgres connections. Opening a fresh TLS connection
# to Supabase costs hundreds of milliseconds per request; reusing warm
# connections makes every page load noticeably faster.
import threading

_pool = None
_pool_lock = threading.Lock()
_POOL_MAX = 10  # a few more than gunicorn's thread count


def _get_pool():
    global _pool
    if _pool is None:
        import psycopg2.extras
        from psycopg2.pool import ThreadedConnectionPool
        with _pool_lock:
            if _pool is None:
                _pool = ThreadedConnectionPool(
                    minconn=1, maxconn=_POOL_MAX, dsn=_dsn(),
                    cursor_factory=psycopg2.extras.RealDictCursor,
                    # TCP keepalives so pooled connections aren't silently
                    # dropped by the network while idle.
                    keepalives=1, keepalives_idle=30,
                    keepalives_interval=10, keepalives_count=3,
                )
    return _pool


def get_db():
    """Check out one pooled connection per web request and reuse it within it."""
    if "db" not in g:
        conn = _get_pool().getconn()
        if conn.closed:            # the pool handed us a dead connection
            _get_pool().putconn(conn, close=True)
            conn = _get_pool().getconn()
        g.db = conn
    return g.db


def close_db(exception=None):
    """Return the connection to the pool when the request finishes."""
    db = g.pop("db", None)
    if db is not None:
        try:
            if exception is None:
                db.commit()
            else:
                db.rollback()
        except Exception:
            pass
        finally:
            try:
                _get_pool().putconn(db, close=db.closed)
            except Exception:
                db.close()


def init_db():
    """No-op: the schema lives in Supabase (managed by SQL migrations).

    Kept so `app.py`'s startup call still works. We do a light connectivity
    check and warn rather than fail, so the app can still start (and fall back)
    if the database is temporarily unreachable.
    """
    if not config.SUPABASE_DB_URL:
        print("[db] SUPABASE_DB_URL not set — set it in .env before using the marketplace.")
        return
    try:
        import psycopg2
        conn = psycopg2.connect(_dsn())
        conn.close()
        print("[db] Connected to Supabase Postgres.")
    except Exception as e:
        print(f"[db] WARNING: could not connect to Supabase ({e}).")


def _pg(sql: str) -> str:
    """Rewrite '?' placeholders to Postgres '%s'."""
    return sql.replace("?", "%s")


# ---------- small query helpers ----------
def query_one(sql: str, params: tuple = ()):
    cur = get_db().cursor()
    try:
        cur.execute(_pg(sql), params) if params else cur.execute(_pg(sql))
        return cur.fetchone()
    finally:
        cur.close()


def query_all(sql: str, params: tuple = ()):
    cur = get_db().cursor()
    try:
        cur.execute(_pg(sql), params) if params else cur.execute(_pg(sql))
        return cur.fetchall()
    finally:
        cur.close()


def execute(sql: str, params: tuple = ()) -> int:
    """Run INSERT/UPDATE/DELETE, commit, and return the new row id (when the
    statement ends with `RETURNING id`) or the number of affected rows."""
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(_pg(sql), params) if params else cur.execute(_pg(sql))
        result = cur.rowcount
        if cur.description is not None:      # statement returned rows (e.g. RETURNING id)
            row = cur.fetchone()
            if row is not None:
                result = row.get("id", list(row.values())[0])
        db.commit()
        return result
    finally:
        cur.close()


# Half-life (in days) for weighting live listings by freshness.
_MARKET_PRICE_HALF_LIFE_DAYS = 14


def market_price_stats(product: str, category: str, region: str) -> dict | None:
    """What other farmers are actually asking, right now, for this product.

    Scoped to active listings for the same product + category + region. Returns
    None if nobody in this region has listed it yet. The average is weighted by
    how recently each listing was posted (see _MARKET_PRICE_HALF_LIFE_DAYS).
    """
    rows = query_all(
        "SELECT price_per_kg, "
        "GREATEST(EXTRACT(EPOCH FROM (now() - created_at)) / 86400.0, 0) AS age_days "
        "FROM listings WHERE crop = ? AND category = ? AND region = ? "
        "AND status = 'active'",
        (product, category, region),
    )
    if not rows:
        return None

    prices = [float(r["price_per_kg"]) for r in rows]
    ages = [float(r["age_days"]) for r in rows]
    weights = [0.5 ** (a / _MARKET_PRICE_HALF_LIFE_DAYS) for a in ages]
    weighted_avg = sum(p * w for p, w in zip(prices, weights)) / sum(weights)

    return {
        "count": len(rows),
        "avg": round(weighted_avg, 2),
        "min": round(min(prices), 2),
        "max": round(max(prices), 2),
        "newest_age_days": round(min(ages), 1),
    }


def average_rating(user_id: int) -> dict:
    """Return {'avg': float|None, 'count': int} for a user's received ratings."""
    row = query_one(
        "SELECT ROUND(AVG(stars), 1) AS avg, COUNT(*) AS count "
        "FROM ratings WHERE ratee_id = ?",
        (user_id,),
    )
    avg = row["avg"]
    return {"avg": float(avg) if avg is not None else None, "count": row["count"]}
