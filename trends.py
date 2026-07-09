"""
trends.py
---------
Market-trends intelligence built ENTIRELY from real FarmConnect listings.

The Simple site does not track orders, price history or product views, so —
unlike a webshop — "demand" here is read from what farmers actually list and
mark sold. Everything is scoped to ONE region, because listing prices are
stored unconverted in each region's own currency; mixing regions would mix
currencies. That also matches the region-scoped "Trending" box on the
dashboard.

Every number below comes from the `listings` table. Nothing is simulated.
"""
from __future__ import annotations
import db

# How many weeks of history the price-trend line covers.
_TREND_WEEKS = 8


def region_overview(region: str, farmer_id: int | None = None) -> dict:
    """Assemble the whole Trends page for one region.

    `farmer_id` (when the viewer is a farmer) adds a "your prices vs the
    market" comparison for that farmer's own active listings.
    """
    return {
        "totals": _totals(region),
        "price_board": _price_board(region),
        "hot": _hot_products(region),
        "product_share": _product_share(region),
        "trend": _price_trend(region),
        "outlook": _next_season_outlook(region),
        "my_vs_market": _my_vs_market(farmer_id) if farmer_id else None,
    }


def _totals(region: str) -> dict:
    row = db.query_one(
        "SELECT COUNT(*) AS listings, COUNT(DISTINCT farmer_id) AS farmers, "
        "COUNT(DISTINCT crop) AS crops "
        "FROM listings WHERE region = ? AND status = 'active'",
        (region,),
    )
    return {"listings": row["listings"], "farmers": row["farmers"], "crops": row["crops"]}


def _price_board(region: str):
    """Live price board: per product, what farmers in this region are asking."""
    rows = db.query_all(
        "SELECT crop, category, "
        "COUNT(DISTINCT farmer_id) AS sellers, "
        "ROUND(AVG(price_per_kg)::numeric, 2) AS avg_p, "
        "ROUND(MIN(price_per_kg)::numeric, 2) AS min_p, "
        "ROUND(MAX(price_per_kg)::numeric, 2) AS max_p "
        "FROM listings WHERE region = ? AND status = 'active' "
        "GROUP BY crop, category ORDER BY sellers DESC, crop",
        (region,),
    )
    return [dict(r) for r in rows]


def _hot_products(region: str, limit: int = 6):
    """Most active products in this region: how many listed, how many sold, and
    whether listing activity is rising or falling (last 30 days vs the 30 before).
    """
    rows = db.query_all(
        "SELECT crop, category, COUNT(*) AS listed, "
        "SUM(CASE WHEN status = 'sold' THEN 1 ELSE 0 END) AS sold, "
        "SUM(CASE WHEN created_at >= now() - interval '30 days' "
        "         THEN 1 ELSE 0 END) AS recent, "
        "SUM(CASE WHEN created_at <  now() - interval '30 days' "
        "          AND created_at >= now() - interval '60 days' "
        "         THEN 1 ELSE 0 END) AS prev "
        "FROM listings WHERE region = ? "
        "GROUP BY crop, category ORDER BY listed DESC, sold DESC LIMIT ?",
        (region, limit),
    )
    out = []
    for r in rows:
        listed, sold, recent, prev = r["listed"], r["sold"], r["recent"], r["prev"]
        change = round((recent - prev) / prev * 100) if prev > 0 else None
        out.append({
            "crop": r["crop"], "category": r["category"],
            "listed": listed, "sold": sold,
            "sell_through": round(sold / listed * 100) if listed else 0,
            "change": change,
            "is_new": prev == 0 and recent > 0,
        })
    return out


def _product_share(region: str, top: int = 6):
    """Share of the region's active listings held by each product (top N + Other)."""
    rows = db.query_all(
        "SELECT crop, COUNT(*) AS n FROM listings "
        "WHERE region = ? AND status = 'active' GROUP BY crop ORDER BY n DESC",
        (region,),
    )
    total = sum(r["n"] for r in rows)
    if not total:
        return []
    share = [{"crop": r["crop"], "n": r["n"],
              "pct": round(r["n"] / total * 100)} for r in rows[:top]]
    other = total - sum(s["n"] for s in share)
    if other > 0:
        share.append({"crop": "Other", "n": other, "pct": round(other / total * 100)})
    return share


def _price_trend(region: str, weeks: int = _TREND_WEEKS):
    """Weekly average asking price over the last `weeks` weeks, for the region's
    most-listed product in that window. Returns None if there isn't enough data
    to draw a line (fewer than two weeks with listings).
    """
    window_days = weeks * 7
    top = db.query_one(
        "SELECT crop, category, COUNT(*) AS n FROM listings "
        "WHERE region = ? AND created_at >= now() - make_interval(days => ?) "
        "GROUP BY crop, category ORDER BY n DESC LIMIT 1",
        (region, window_days),
    )
    if not top:
        return None

    points = db.query_all(
        "SELECT to_char(created_at, 'IYYY-IW') AS wk, "
        "ROUND(AVG(price_per_kg)::numeric, 2) AS avg_p, COUNT(*) AS n "
        "FROM listings WHERE region = ? AND crop = ? AND category = ? "
        "AND created_at >= now() - make_interval(days => ?) "
        "GROUP BY wk ORDER BY wk",
        (region, top["crop"], top["category"], window_days),
    )
    if len(points) < 2:
        return None

    prices = [p["avg_p"] for p in points]
    return {
        "crop": top["crop"],
        "points": [{"week": p["wk"][-2:], "price": p["avg_p"], "n": p["n"]} for p in points],
        "min": min(prices),
        "max": max(prices),
    }


def _next_season_outlook(region: str, months: int = 4, top: int = 5):
    """Which products' listing activity is climbing month over month here.

    This is a real momentum signal, not a prediction pulled from nowhere: we
    look at how many listings each product got per calendar month over the
    last `months` months and rank by growth from the first month with data to
    the most recent one. A product needs at least two distinct months of
    listings to be ranked at all (one data point has no trend). Returns an
    empty list if the region doesn't have enough history yet.
    """
    rows = db.query_all(
        "SELECT crop, category, to_char(created_at, 'YYYY-MM') AS ym, COUNT(*) AS n "
        "FROM listings WHERE region = ? "
        "AND created_at >= now() - make_interval(months => ?) "
        "GROUP BY crop, category, ym ORDER BY crop, category, ym",
        (region, months),
    )
    by_product: dict[tuple[str, str], list[tuple[str, int]]] = {}
    for r in rows:
        by_product.setdefault((r["crop"], r["category"]), []).append((r["ym"], r["n"]))

    outlook = []
    for (crop, category), points in by_product.items():
        if len(points) < 2:
            continue
        first_n, last_n = points[0][1], points[-1][1]
        total = sum(n for _, n in points)
        growth_pct = round((last_n - first_n) / first_n * 100) if first_n else 100
        outlook.append({
            "crop": crop, "category": category,
            "months_tracked": len(points), "total_listed": total,
            "growth_pct": growth_pct,
            "rising": growth_pct > 0,
        })
    outlook.sort(key=lambda o: (o["growth_pct"], o["total_listed"]), reverse=True)
    return outlook[:top]


def _my_vs_market(farmer_id: int):
    """Compare this farmer's active listing prices with the local market
    (same product + category + region, other farmers only). Each listing is
    compared within its OWN region so the currency always matches.
    """
    mine = db.query_all(
        "SELECT id, crop, category, region, price_per_kg FROM listings "
        "WHERE farmer_id = ? AND status = 'active' ORDER BY created_at DESC",
        (farmer_id,),
    )
    out = []
    for l in mine:
        m = db.query_one(
            "SELECT ROUND(AVG(price_per_kg)::numeric, 2) AS avg_p, "
            "COUNT(DISTINCT farmer_id) AS sellers "
            "FROM listings WHERE crop = ? AND category = ? AND region = ? "
            "AND status = 'active' AND farmer_id != ?",
            (l["crop"], l["category"], l["region"], farmer_id),
        )
        avg_p = float(m["avg_p"]) if m["avg_p"] is not None else None
        diff_pct = round((l["price_per_kg"] - avg_p) / avg_p * 100, 1) if avg_p else None
        if diff_pct is None:
            position = "only"
        elif diff_pct > 5:
            position = "above"
        elif diff_pct < -5:
            position = "below"
        else:
            position = "at"
        out.append({
            "crop": l["crop"], "category": l["category"], "region": l["region"],
            "my_price": round(l["price_per_kg"], 2), "market_avg": avg_p,
            "sellers": m["sellers"], "diff_pct": diff_pct, "position": position,
        })
    return out
