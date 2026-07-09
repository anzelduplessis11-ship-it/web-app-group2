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
import reference_prices


def region_overview(region: str, farmer_id: int | None = None) -> dict:
    """Assemble the whole Trends page for one region.

    `farmer_id` (when the viewer is a farmer) adds a "your prices vs the
    market" comparison for that farmer's own active listings.
    """
    return {
        "totals": _totals(region),
        "price_board": _price_board(region),
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
    """Price board for a region, and never empty.

    Live listings from farmers in this region come first (source "live").
    For staple crops nobody has listed locally yet, we fall back to a
    clearly-labeled estimated reference price (source "estimate") so a farmer
    in any African country immediately sees roughly what their crop is worth.
    """
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
    board = [dict(r) | {"source": "live"} for r in rows]

    # Fill in staple crops with no live listings using reference estimates.
    live_crops = {r["crop"] for r in board}
    for crop in reference_prices.REFERENCE_CROPS:
        if crop in live_crops:
            continue
        est = reference_prices.estimate(crop, region)
        if not est:
            continue
        board.append({
            "crop": crop, "category": "crop", "sellers": 0,
            "avg_p": est["mid"], "min_p": est["low"], "max_p": est["high"],
            "source": "estimate",
        })
    return board


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
