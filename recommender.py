"""
recommender.py
--------------
The "For you" recommendation engine. It studies each user's real behaviour —
what they order, when in the week and month they order it, how often they
restock, and what they've been viewing or searching lately — then scores every
active listing and returns the best few, each with a plain-language reason
("You usually restock Maize about every 30 days — you're due").

It is deliberately a transparent pattern-mining engine, not a black box:
every point of a listing's score comes from a named signal, and the strongest
signals become the reasons shown to the user. No external services, no extra
dependencies — just SQL + Python over the `orders` and `activity_events`
tables (see migrations/2026-07-09_add_orders_and_activity_events.sql).

Layout:
  build_profile(orders, events, now)  -> a dict describing the user's habits
  score_candidates(...)               -> scored + explained listings (pure)
  recommend_for(user)                 -> the one call app.py makes; fetches
                                         from the DB and returns the top picks
The first two are pure functions of their inputs so they can be tested
without a database.
"""
from __future__ import annotations

from datetime import datetime, timezone

import db
import geo

# How quickly old behaviour fades. An order from ~2 months ago counts half as
# much as one from today; views/searches fade faster because interest moves on.
_ORDER_HALF_LIFE_DAYS = 60
_EVENT_HALF_LIFE_DAYS = 21

# A user needs at least this many orders before we trust their timing habits
# (weekday / time-of-month). Below that it's coincidence, not a pattern.
_MIN_ORDERS_FOR_TIMING = 3

_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
             "Friday", "Saturday", "Sunday"]
_MONTH_PHASES = {"early": "early in the month", "mid": "mid-month",
                 "late": "late in the month"}


def _as_utc(dt: datetime) -> datetime:
    """DB timestamps are timezone-aware; test data may be naive. Normalise."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _age_days(dt: datetime, now: datetime) -> float:
    return max((now - _as_utc(dt)).total_seconds() / 86400.0, 0.0)


def _decay(age_days: float, half_life: float) -> float:
    return 0.5 ** (age_days / half_life)


def _month_phase(day: int) -> str:
    return "early" if day <= 10 else ("mid" if day <= 20 else "late")


# ---------------------------------------------------------------------------
# Step 1 — turn raw history into a habit profile
# ---------------------------------------------------------------------------
def build_profile(orders: list[dict], events: list[dict], now: datetime) -> dict:
    """Distil a user's orders + browsing events into their buying habits.

    `orders` rows need: crop, category, farmer_id, created_at (status already
    filtered to real intent, i.e. not cancelled). `events` rows need:
    event_type, crop, created_at.
    """
    crop_bought: dict[str, float] = {}     # recency-weighted order counts
    crop_viewed: dict[str, float] = {}     # recency-weighted view/search interest
    category_w: dict[str, float] = {}
    farmer_counts: dict[int, int] = {}
    order_times: dict[str, list[datetime]] = {}   # per crop, in time order
    weekday_counts = [0] * 7
    phase_counts = {"early": 0, "mid": 0, "late": 0}

    for o in orders:
        when = _as_utc(o["created_at"])
        w = _decay(_age_days(when, now), _ORDER_HALF_LIFE_DAYS)
        crop_bought[o["crop"]] = crop_bought.get(o["crop"], 0.0) + w
        category_w[o["category"]] = category_w.get(o["category"], 0.0) + w
        farmer_counts[o["farmer_id"]] = farmer_counts.get(o["farmer_id"], 0) + 1
        order_times.setdefault(o["crop"], []).append(when)
        weekday_counts[when.weekday()] += 1
        phase_counts[_month_phase(when.day)] += 1

    for ev in events:
        if not ev.get("crop"):
            continue        # a search with no product filter tells us nothing
        w = _decay(_age_days(ev["created_at"], now), _EVENT_HALF_LIFE_DAYS)
        # A deliberate search signals slightly more intent than a page view.
        w *= 0.6 if ev["event_type"] == "search" else 0.4
        crop_viewed[ev["crop"]] = crop_viewed.get(ev["crop"], 0.0) + w

    # Restock rhythm: the typical number of days between same-crop orders.
    cadence: dict[str, float] = {}
    last_order: dict[str, datetime] = {}
    for crop, times in order_times.items():
        times.sort()
        last_order[crop] = times[-1]
        gaps = [(b - a).total_seconds() / 86400.0 for a, b in zip(times, times[1:])]
        gaps = [gap for gap in gaps if gap >= 2]   # same-day repeats aren't a rhythm
        if gaps:
            gaps.sort()
            cadence[crop] = gaps[len(gaps) // 2]   # median: robust to one odd gap

    return {
        "crop_bought": crop_bought,
        "crop_viewed": crop_viewed,
        "category_w": category_w,
        "farmer_counts": farmer_counts,
        "cadence": cadence,
        "last_order": last_order,
        "weekday_counts": weekday_counts,
        "phase_counts": phase_counts,
        "order_count": len(orders),
        "has_signals": bool(orders) or bool(crop_viewed),
    }


def _timing_matches(profile: dict, now: datetime) -> list[tuple[str, str]]:
    """Which of the user's timing habits does *right now* line up with?

    Returns [(kind, human phrase), ...] — empty if we don't have enough
    orders to call anything a habit yet.
    """
    total = profile["order_count"]
    if total < _MIN_ORDERS_FOR_TIMING:
        return []
    matches = []
    wd = now.weekday()
    if profile["weekday_counts"][wd] / total >= 0.4:
        matches.append(("weekday", f"{_WEEKDAYS[wd]} is your usual buying day"))
    phase = _month_phase(now.day)
    if profile["phase_counts"][phase] / total >= 0.5:
        matches.append(("phase", f"you often buy {_MONTH_PHASES[phase]}"))
    return matches


# ---------------------------------------------------------------------------
# Step 2 — score every candidate listing against the profile
# ---------------------------------------------------------------------------
def score_candidates(candidates: list[dict], profile: dict, viewer_region: str,
                     now: datetime, market_avgs: dict | None = None,
                     region_popular: dict | None = None,
                     skip_listing_ids: set | None = None) -> list[dict]:
    """Return [{listing, score, reasons}] sorted best-first.

    Every signal adds (contribution, reason) pairs; the reasons shown are the
    highest-contributing ones, so the explanation always matches the ranking.
    """
    market_avgs = market_avgs or {}
    region_popular = region_popular or {}
    skip_listing_ids = skip_listing_ids or set()
    timing = _timing_matches(profile, now)

    scored = []
    for l in candidates:
        if l["id"] in skip_listing_ids:
            continue        # they already have an open order on this one
        parts: list[tuple[float, str | None]] = []
        crop = l["crop"]

        # --- what they buy -------------------------------------------------
        bought = profile["crop_bought"].get(crop, 0.0)
        if bought > 0:
            label = (f"You've ordered {crop} before" if bought < 1.8
                     else f"{crop} is one of your regulars")
            parts.append((3.0 * min(bought, 1.0), label))
        viewed = profile["crop_viewed"].get(crop, 0.0)
        if viewed > 0.2 and bought == 0:
            parts.append((1.2 * min(viewed, 1.0),
                          f"You've been looking at {crop} lately"))
        cat_w = profile["category_w"].get(l["category"], 0.0)
        if cat_w > 0:
            parts.append((0.6 * min(cat_w / 3.0, 1.0), None))

        # --- when they buy: are they due to restock this crop? -------------
        gap = profile["cadence"].get(crop)
        last = profile["last_order"].get(crop)
        due = False
        if gap and last:
            since = _age_days(last, now)
            if since >= 0.7 * gap:
                due = True
                parts.append((2.0, f"You restock {crop} about every "
                                   f"{gap:.0f} days — it's been {since:.0f}"))
        # Their general shopping rhythm only matters for products they
        # actually care about, so gate it on some crop affinity.
        if (bought > 0 or viewed > 0.2) and timing:
            for _, phrase in timing:
                parts.append((0.6, phrase[0].upper() + phrase[1:]))

        # --- where: closer farmers are easier deals ------------------------
        km = geo.distance_between_regions(viewer_region, l["region"])
        if l["region"] == viewer_region:
            parts.append((1.5, "In your region"))
        elif km is not None:
            closeness = max(0.0, 1.0 - km / 2500.0)
            parts.append((1.5 * closeness,
                          f"{km:.0f} km from you" if km <= 800 else None))

        # --- price: is this listing actually a good deal? ------------------
        mkt = market_avgs.get((crop, l["category"], l["region"]))
        if mkt and mkt["n"] >= 2 and mkt["avg_price"]:
            discount = 1.0 - float(l["price_per_kg"]) / float(mkt["avg_price"])
            if discount >= 0.07:
                parts.append((min(discount * 5.0, 1.0),
                              f"{discount * 100:.0f}% below the local average"))

        # --- freshness + social proof --------------------------------------
        age = _age_days(l["created_at"], now)
        age_n = round(age)
        parts.append((0.5 * _decay(age, 10),
                      ("Listed today" if age_n == 0 else
                       f"Listed {age_n} day{'s' if age_n != 1 else ''} ago"
                       if age <= 3 else None)))
        if l["farmer_id"] in profile["farmer_counts"]:
            parts.append((0.8, f"From {l.get('farmer_name', 'a farmer')} — "
                               "you've bought from them before"))
        pop = region_popular.get(crop, 0)
        if pop and l["region"] == viewer_region:
            parts.append((0.4 * min(pop / 3.0, 1.0),
                          f"Popular in {viewer_region}"))

        score = sum(c for c, _ in parts)
        if score < 0.8:
            # Nothing meaningful connects this listing to the user. The bar
            # sits above the generic signals (category taste + freshness can
            # reach ~0.7 on their own) so only listings with at least one
            # *specific* hook — their crop, their region, a real discount —
            # make the panel.
            continue
        reasons = [text for c, text in
                   sorted(parts, key=lambda p: -p[0]) if text][:3]
        scored.append({"listing": l, "score": round(score, 3),
                       "reasons": reasons, "due": due})

    scored.sort(key=lambda s: -s["score"])

    # Variety guard: never fill the panel with four listings of the same crop.
    picked, per_crop = [], {}
    for s in scored:
        c = s["listing"]["crop"]
        if per_crop.get(c, 0) >= 2:
            continue
        per_crop[c] = per_crop.get(c, 0) + 1
        picked.append(s)
    return picked


def _build_headline(profile: dict, picks: list[dict], now: datetime) -> str | None:
    """One friendly nudge sentence for the top of the panel, if we have a
    genuinely personal hook. Restock-due beats calendar habits."""
    for p in picks:
        if p["due"]:
            crop = p["listing"]["crop"]
            gap = profile["cadence"].get(crop)
            since = _age_days(profile["last_order"][crop], now)
            return (f"Time to restock {crop}? You usually buy it about every "
                    f"{gap:.0f} days, and it's been {since:.0f}.")
    for kind, _phrase in _timing_matches(profile, now):
        if kind == "phase":
            return (f"It's {_MONTH_PHASES[_month_phase(now.day)]} — around when "
                    "you usually stock up.")
        return f"It's {_WEEKDAYS[now.weekday()]} — your usual FarmConnect day."
    return None


# ---------------------------------------------------------------------------
# Step 3 — the one call the dashboard makes
# ---------------------------------------------------------------------------
def recommend_for(user: dict, limit: int = 4) -> dict:
    """Personal recommendations for this user, ready for the template.

    Returns {basis, headline, items}: basis is 'personal' when the picks come
    from the user's own habits, or 'popular' for brand-new users (cold start),
    where we fall back to fresh, nearby and locally popular listings.
    """
    now = datetime.now(timezone.utc)

    orders = db.query_all(
        "SELECT crop, category, region, farmer_id, listing_id, status, created_at "
        "FROM orders WHERE buyer_id = ? AND status != 'cancelled' "
        "ORDER BY created_at",
        (user["id"],),
    )
    events = db.query_all(
        "SELECT event_type, crop, category, region, created_at "
        "FROM activity_events WHERE user_id = ? "
        "AND created_at > now() - interval '60 days' "
        "ORDER BY created_at DESC LIMIT 500",
        (user["id"],),
    )
    candidates = db.query_all(
        "SELECT l.*, u.name AS farmer_name FROM listings l "
        "JOIN users u ON u.id = l.farmer_id "
        "WHERE l.status = 'active' AND l.farmer_id != ? "
        "ORDER BY l.created_at DESC LIMIT 300",
        (user["id"],),
    )
    market_rows = db.query_all(
        "SELECT crop, category, region, AVG(price_per_kg) AS avg_price, "
        "COUNT(*) AS n FROM listings WHERE status = 'active' "
        "GROUP BY crop, category, region"
    )
    # "Popular near you" = what actually gets ordered or sold in their region.
    popular_rows = db.query_all(
        "SELECT crop, COUNT(*) AS n FROM ("
        "  SELECT crop FROM orders WHERE region = ? AND status != 'cancelled'"
        "  UNION ALL"
        "  SELECT crop FROM listings WHERE region = ? AND status = 'sold'"
        ") t GROUP BY crop ORDER BY n DESC LIMIT 8",
        (user["region"], user["region"]),
    )

    profile = build_profile(orders, events, now)
    market_avgs = {(r["crop"], r["category"], r["region"]): r for r in market_rows}
    region_popular = {r["crop"]: r["n"] for r in popular_rows}
    open_orders = {o["listing_id"] for o in orders
                   if o["status"] in ("pending", "confirmed")}

    picks = score_candidates(
        candidates, profile, user["region"], now,
        market_avgs=market_avgs, region_popular=region_popular,
        skip_listing_ids=open_orders,
    )[:limit]

    basis = "personal" if profile["has_signals"] else "popular"
    headline = _build_headline(profile, picks, now) if basis == "personal" else None
    return {"basis": basis, "headline": headline, "items": picks}
