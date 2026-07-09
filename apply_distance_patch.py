"""
apply_distance_patch.py
--------------------------
Run this once from inside your `farmconnect` folder:

    python3 apply_distance_patch.py

It will:
  1. Create geo.py: approximate coordinates for your 6 existing regions
     and a distance calculator (haversine formula, no API needed)
  2. Update /market so that when someone is logged in, listings are
     sorted with the closest farmers to their region shown first
  3. Add a distance_to(region) helper available in every template
  4. Update templates/market.html to show "X km from you" on each
     listing, and a short note that results are sorted by distance

Notes:
  - Distance is calculated region-to-region (city center to city center)
    using fixed coordinates, not live GPS - there's no per-user exact
    location in this app yet.
  - If you add more regions later without adding their coordinates to
    geo.py, distance just won't show for those - nothing breaks.

Safe to re-run — it checks for existing markers and skips anything
already applied.
"""

from pathlib import Path

ROOT = Path(__file__).parent

def patch(path: str, old: str, new: str, label: str):
    p = ROOT / path
    text = p.read_text()
    if new in text:
        print(f"  [skip] {label} already applied")
        return
    if old not in text:
        print(f"  [!!] Could not find expected text in {path} for: {label}")
        print("       You may need to apply this change manually.")
        return
    p.write_text(text.replace(old, new, 1))
    print(f"  [ok] {label}")


# ---------------------------------------------------------------------------
# 1. geo.py — new file
# ---------------------------------------------------------------------------
print("Creating geo.py ...")
geo_path = ROOT / "geo.py"
if geo_path.exists():
    print("  [skip] geo.py already exists")
else:
    geo_path.write_text('''"""
geo.py
-------
Approximate coordinates for FarmConnect's regions, and a straight-line
distance calculator (the haversine formula) so the market page can show
buyers which farmers are closest to them.

This is region-to-region distance (city center to city center), not
precise GPS - there's no per-user exact location stored in this app.
"""

import math

# Approximate latitude/longitude for each of FarmConnect's current regions.
REGION_COORDS = {
    "Nairobi": (-1.2921, 36.8219),
    "Kano": (12.0022, 8.5920),
    "Lagos": (6.5244, 3.3792),
    "Kumasi": (6.6885, -1.6244),
    "Kampala": (0.3476, 32.5825),
    "Arusha": (-3.3869, 36.6830),
}


def coords_for_region(region):
    return REGION_COORDS.get(region)


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points, in kilometers."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def distance_between_regions(region_a, region_b):
    """Distance in km between two regions, or None if either is unknown."""
    a = coords_for_region(region_a)
    b = coords_for_region(region_b)
    if not a or not b:
        return None
    return haversine_km(a[0], a[1], b[0], b[1])
''')
    print("  [ok] geo.py created")

# ---------------------------------------------------------------------------
# 2. app.py — import geo
# ---------------------------------------------------------------------------
print("Patching app.py ...")
patch(
    "app.py",
    old='''import db
import currency
from pricing_model import PricingModel''',
    new='''import db
import currency
import geo
from pricing_model import PricingModel''',
    label="import geo module",
)

# ---------------------------------------------------------------------------
# 3. app.py — /market sorts listings by distance when someone is logged in
# ---------------------------------------------------------------------------
patch(
    "app.py",
    old='''@app.route("/market")
def market():
    """Full marketplace with optional crop/livestock/region filters."""
    crop = request.args.get("crop", "")
    region = request.args.get("region", "")
    category = request.args.get("category", "")

    sql = (
        "SELECT l.*, u.name AS farmer_name FROM listings l "
        "JOIN users u ON u.id = l.farmer_id WHERE l.status = 'active'"
    )
    params = []
    if crop:
        sql += " AND l.crop = ?"
        params.append(crop)
    if region:
        sql += " AND l.region = ?"
        params.append(region)
    if category:
        sql += " AND l.category = ?"
        params.append(category)
    sql += " ORDER BY l.created_at DESC"

    listings = db.query_all(sql, tuple(params))
    return render_template(
        "market.html", listings=listings, crops=CROPS, livestock=LIVESTOCK, regions=REGIONS,
        sel_crop=crop, sel_region=region, sel_category=category,
    )''',
    new='''@app.route("/market")
def market():
    """Full marketplace with optional crop/livestock/region filters."""
    crop = request.args.get("crop", "")
    region = request.args.get("region", "")
    category = request.args.get("category", "")

    sql = (
        "SELECT l.*, u.name AS farmer_name FROM listings l "
        "JOIN users u ON u.id = l.farmer_id WHERE l.status = 'active'"
    )
    params = []
    if crop:
        sql += " AND l.crop = ?"
        params.append(crop)
    if region:
        sql += " AND l.region = ?"
        params.append(region)
    if category:
        sql += " AND l.category = ?"
        params.append(category)
    sql += " ORDER BY l.created_at DESC"

    listings = db.query_all(sql, tuple(params))

    # If someone is logged in, recommend the closest farmers first.
    viewer = current_user()
    if viewer is not None:
        def distance_or_far(l):
            d = geo.distance_between_regions(viewer["region"], l["region"])
            return d if d is not None else float("inf")
        listings = sorted(listings, key=distance_or_far)

    return render_template(
        "market.html", listings=listings, crops=CROPS, livestock=LIVESTOCK, regions=REGIONS,
        sel_crop=crop, sel_region=region, sel_category=category,
    )''',
    label="/market sorts by distance",
)

# ---------------------------------------------------------------------------
# 4. app.py — distance_to() template helper
# ---------------------------------------------------------------------------
patch(
    "app.py",
    old='''    return {
        "currency_symbol": currency_symbol,
        "currency_code": currency_code,
        "converted_price": converted_price,
    }''',
    new='''    return {
        "currency_symbol": currency_symbol,
        "currency_code": currency_code,
        "converted_price": converted_price,
    }


@app.context_processor
def inject_distance_helper():
    """Make distance_to(region) available in every template."""
    def distance_to(region):
        viewer = current_user()
        if viewer is None:
            return None
        return geo.distance_between_regions(viewer["region"], region)
    return {"distance_to": distance_to}''',
    label="distance_to() template helper",
)

# ---------------------------------------------------------------------------
# 5. templates/market.html — show distance + sorted-by-distance note
# ---------------------------------------------------------------------------
print("Patching templates/market.html ...")
patch(
    "templates/market.html",
    old='''<section class="section">
  <p class="eyebrow">The market</p>
  <h1>Browse crops for sale</h1>''',
    new='''<section class="section">
  <p class="eyebrow">The market</p>
  <h1>Browse crops for sale</h1>
  {% if user %}
    <p class="muted">Showing farmers closest to you first.</p>
  {% endif %}''',
    label="market.html closest-first note",
)

patch(
    "templates/market.html",
    old='''      {% for l in listings %}
        <a class="card listing-card" href="{{ url_for('listing_detail', listing_id=l['id']) }}" style="text-decoration:none;color:inherit;">
          <div class="crop">{{ l['crop'] }}</div>
          <div class="meta">{{ l['region'] }} · {{ l['quantity_kg'] | int }} kg available</div>
          <span class="tag" style="align-self:flex-start;">
            <span class="amount">{{ currency_symbol(l['region']) }}{{ "%.2f"|format(l['price_per_kg']) }}</span>
            <span class="unit">per kg ({{ currency_code(l['region']) }})</span>
          </span>
          {% set conv = converted_price(l['price_per_kg'], l['region']) %}
          {% if conv %}
            <div class="meta">≈ {{ conv.symbol }}{{ "%.2f"|format(conv.amount) }} {{ conv.code }} for you</div>
          {% endif %}
          <div class="meta">by {{ l['farmer_name'] }}</div>
        </a>
      {% endfor %}''',
    new='''      {% for l in listings %}
        <a class="card listing-card" href="{{ url_for('listing_detail', listing_id=l['id']) }}" style="text-decoration:none;color:inherit;">
          <div class="crop">{{ l['crop'] }}</div>
          <div class="meta">{{ l['region'] }} · {{ l['quantity_kg'] | int }} kg available</div>
          {% set d = distance_to(l['region']) %}
          {% if d is not none %}
            <div class="meta">{{ "%.0f"|format(d) }} km from you</div>
          {% endif %}
          <span class="tag" style="align-self:flex-start;">
            <span class="amount">{{ currency_symbol(l['region']) }}{{ "%.2f"|format(l['price_per_kg']) }}</span>
            <span class="unit">per kg ({{ currency_code(l['region']) }})</span>
          </span>
          {% set conv = converted_price(l['price_per_kg'], l['region']) %}
          {% if conv %}
            <div class="meta">≈ {{ conv.symbol }}{{ "%.2f"|format(conv.amount) }} {{ conv.code }} for you</div>
          {% endif %}
          <div class="meta">by {{ l['farmer_name'] }}</div>
        </a>
      {% endfor %}''',
    label="market.html shows distance per listing",
)

print("\nDone. Restart the app to see the changes (no database reset needed).")
print("  python3 app.py")
