"""
apply_trending_livestock_patch.py
-----------------------------------
Run this once from inside your `farmconnect` folder:

    python3 apply_trending_livestock_patch.py

It will:
  1. Add a `category` column ('crop' or 'livestock') to the listings table
  2. Add a LIVESTOCK list next to CROPS in app.py
  3. Update /listings/new to accept a category (crop vs livestock) and the
     right product list for each
  4. Update /market to filter by category too
  5. Update /dashboard to compute "Trending in your region" from real data
     (most-sold items in your region, falling back to most-listed if
     nothing has sold yet)
  6. Update templates/new_listing.html, templates/market.html, and
     templates/dashboard.html to match

Safe to re-run — it checks for existing markers and skips anything
already applied. If a step fails to match, everything else still applies;
just tell me and we'll fix that one piece directly.
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
# 1. db.py — add category column to listings
# ---------------------------------------------------------------------------
print("Patching db.py ...")
patch(
    "db.py",
    old='''        CREATE TABLE IF NOT EXISTS listings (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id    INTEGER NOT NULL REFERENCES users(id),
            crop         TEXT    NOT NULL,
            region       TEXT    NOT NULL,
            quantity_kg  REAL    NOT NULL,
            price_per_kg REAL    NOT NULL,
            description  TEXT,
            status       TEXT    NOT NULL DEFAULT 'active'
                                 CHECK (status IN ('active', 'sold')),
            created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
        );''',
    new='''        CREATE TABLE IF NOT EXISTS listings (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id    INTEGER NOT NULL REFERENCES users(id),
            crop         TEXT    NOT NULL,
            category     TEXT    NOT NULL DEFAULT 'crop'
                                 CHECK (category IN ('crop', 'livestock')),
            region       TEXT    NOT NULL,
            quantity_kg  REAL    NOT NULL,
            price_per_kg REAL    NOT NULL,
            description  TEXT,
            status       TEXT    NOT NULL DEFAULT 'active'
                                 CHECK (status IN ('active', 'sold')),
            created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
        );''',
    label="listings table: category column",
)

# ---------------------------------------------------------------------------
# 2. app.py — LIVESTOCK constant
# ---------------------------------------------------------------------------
print("Patching app.py ...")
patch(
    "app.py",
    old='''CROPS = PRICING.known_crops if PRICING else [
    "Maize", "Tomato", "Cassava", "Rice", "Beans", "Plantain",
]''',
    new='''CROPS = PRICING.known_crops if PRICING else [
    "Maize", "Tomato", "Cassava", "Rice", "Beans", "Plantain",
]
LIVESTOCK = ["Chicken", "Goat", "Cattle", "Sheep", "Pig"]''',
    label="LIVESTOCK constant",
)

# ---------------------------------------------------------------------------
# 3. app.py — /listings/new accepts category
# ---------------------------------------------------------------------------
patch(
    "app.py",
    old='''    if request.method == "POST":
        crop = request.form.get("crop", "").strip()
        region = request.form.get("region", "").strip()
        quantity = request.form.get("quantity_kg", "")
        price = request.form.get("price_per_kg", "")
        description = request.form.get("description", "").strip()

        try:
            quantity = float(quantity)
            price = float(price)
            assert quantity > 0 and price > 0
        except (ValueError, AssertionError):
            flash("Quantity and price must be positive numbers.", "error")
            return render_template(
                "new_listing.html", crops=CROPS, regions=REGIONS,
                pricing_available=PRICING is not None, form=request.form,
            )

        lid = db.execute(
            "INSERT INTO listings (farmer_id, crop, region, quantity_kg, "
            "price_per_kg, description) VALUES (?, ?, ?, ?, ?, ?)",
            (me["id"], crop, region, quantity, price, description),
        )
        flash("Your crop is now listed on the market.", "success")
        return redirect(url_for("listing_detail", listing_id=lid))

    return render_template(
        "new_listing.html", crops=CROPS, regions=REGIONS,
        pricing_available=PRICING is not None, form={},
    )''',
    new='''    if request.method == "POST":
        category = request.form.get("category", "crop").strip()
        if category == "livestock":
            crop = request.form.get("livestock", "").strip()
        else:
            category = "crop"
            crop = request.form.get("crop", "").strip()
        region = request.form.get("region", "").strip()
        quantity = request.form.get("quantity_kg", "")
        price = request.form.get("price_per_kg", "")
        description = request.form.get("description", "").strip()

        try:
            quantity = float(quantity)
            price = float(price)
            assert quantity > 0 and price > 0
        except (ValueError, AssertionError):
            flash("Quantity and price must be positive numbers.", "error")
            return render_template(
                "new_listing.html", crops=CROPS, livestock=LIVESTOCK, regions=REGIONS,
                pricing_available=PRICING is not None, form=request.form,
            )

        lid = db.execute(
            "INSERT INTO listings (farmer_id, crop, category, region, quantity_kg, "
            "price_per_kg, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (me["id"], crop, category, region, quantity, price, description),
        )
        flash("Your listing is now live on the market.", "success")
        return redirect(url_for("listing_detail", listing_id=lid))

    return render_template(
        "new_listing.html", crops=CROPS, livestock=LIVESTOCK, regions=REGIONS,
        pricing_available=PRICING is not None, form={},
    )''',
    label="/listings/new handles category",
)

# ---------------------------------------------------------------------------
# 4. app.py — /market filters by category too
# ---------------------------------------------------------------------------
patch(
    "app.py",
    old='''@app.route("/market")
def market():
    """Full marketplace with optional crop/region filters."""
    crop = request.args.get("crop", "")
    region = request.args.get("region", "")

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
    sql += " ORDER BY l.created_at DESC"

    listings = db.query_all(sql, tuple(params))
    return render_template(
        "market.html", listings=listings, crops=CROPS, regions=REGIONS,
        sel_crop=crop, sel_region=region,
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
    return render_template(
        "market.html", listings=listings, crops=CROPS, livestock=LIVESTOCK, regions=REGIONS,
        sel_crop=crop, sel_region=region, sel_category=category,
    )''',
    label="/market filters by category",
)

# ---------------------------------------------------------------------------
# 5. app.py — /dashboard computes real trending data
# ---------------------------------------------------------------------------
patch(
    "app.py",
    old='''@app.route("/dashboard")
@login_required
def dashboard():
    me = current_user()
    my_listings = []
    if me["role"] == "farmer":
        my_listings = db.query_all(
            "SELECT * FROM listings WHERE farmer_id = ? ORDER BY created_at DESC",
            (me["id"],),
        )
    rating = db.average_rating(me["id"])
    return render_template(
        "dashboard.html", my_listings=my_listings, rating=rating,
    )''',
    new='''@app.route("/dashboard")
@login_required
def dashboard():
    me = current_user()
    my_listings = []
    if me["role"] == "farmer":
        my_listings = db.query_all(
            "SELECT * FROM listings WHERE farmer_id = ? ORDER BY created_at DESC",
            (me["id"],),
        )
    rating = db.average_rating(me["id"])

    # "Trending" = what's actually being bought (sold) most in this region.
    # If nothing has sold there yet, fall back to the most-listed items so
    # the section is never empty for no reason.
    trending = db.query_all(
        "SELECT crop, category, COUNT(*) AS total FROM listings "
        "WHERE region = ? AND status = 'sold' "
        "GROUP BY crop, category ORDER BY total DESC LIMIT 5",
        (me["region"],),
    )
    trending_basis = "sold"
    if not trending:
        trending = db.query_all(
            "SELECT crop, category, COUNT(*) AS total FROM listings "
            "WHERE region = ? "
            "GROUP BY crop, category ORDER BY total DESC LIMIT 5",
            (me["region"],),
        )
        trending_basis = "listed"

    return render_template(
        "dashboard.html", my_listings=my_listings, rating=rating,
        trending=trending, trending_basis=trending_basis,
    )''',
    label="/dashboard computes trending",
)

# ---------------------------------------------------------------------------
# 6a. templates/new_listing.html — category toggle
# ---------------------------------------------------------------------------
print("Patching templates/new_listing.html ...")
patch(
    "templates/new_listing.html",
    old='''  <form method="post" class="card" style="margin-top:18px;">
    <div class="row-2">
      <div class="field">
        <label for="crop">Crop</label>
        <select id="crop" name="crop" required>
          <option value="" disabled {{ 'selected' if not form.get('crop') }}>Choose…</option>
          {% for c in crops %}
            <option value="{{ c }}" {{ 'selected' if form.get('crop') == c }}>{{ c }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="field">
        <label for="region">Region</label>
        <select id="region" name="region" required>
          <option value="" disabled {{ 'selected' if not form.get('region') }}>Choose…</option>
          {% for r in regions %}
            <option value="{{ r }}" {{ 'selected' if form.get('region') == r }}>{{ r }}</option>
          {% endfor %}
        </select>
      </div>
    </div>''',
    new='''  <form method="post" class="card" style="margin-top:18px;">
    <div class="field">
      <label>What are you selling?</label>
      <div class="row-2">
        <label class="pill" style="padding:12px;display:flex;gap:8px;cursor:pointer;">
          <input type="radio" name="category" value="crop" id="cat-crop"
            {{ 'checked' if form.get('category', 'crop') != 'livestock' }}> Crop
        </label>
        <label class="pill" style="padding:12px;display:flex;gap:8px;cursor:pointer;">
          <input type="radio" name="category" value="livestock" id="cat-livestock"
            {{ 'checked' if form.get('category') == 'livestock' }}> Livestock
        </label>
      </div>
    </div>

    <div class="row-2">
      <div class="field" id="crop-field">
        <label for="crop">Crop</label>
        <select id="crop" name="crop">
          <option value="" disabled {{ 'selected' if not form.get('crop') }}>Choose…</option>
          {% for c in crops %}
            <option value="{{ c }}" {{ 'selected' if form.get('crop') == c }}>{{ c }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="field" id="livestock-field" style="display:none;">
        <label for="livestock">Livestock</label>
        <select id="livestock" name="livestock">
          <option value="" disabled {{ 'selected' if not form.get('livestock') }}>Choose…</option>
          {% for a in livestock %}
            <option value="{{ a }}" {{ 'selected' if form.get('livestock') == a }}>{{ a }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="field">
        <label for="region">Region</label>
        <select id="region" name="region" required>
          <option value="" disabled {{ 'selected' if not form.get('region') }}>Choose…</option>
          {% for r in regions %}
            <option value="{{ r }}" {{ 'selected' if form.get('region') == r }}>{{ r }}</option>
          {% endfor %}
        </select>
      </div>
    </div>''',
    label="new_listing.html category toggle",
)

patch(
    "templates/new_listing.html",
    old='''{% block scripts %}
{% if pricing_available %}''',
    new='''{% block scripts %}
<script>
// Show the Crop dropdown or the Livestock dropdown depending on which
// category radio button is selected, and keep "required" in sync.
document.querySelectorAll('input[name="category"]').forEach(function (radio) {
  radio.addEventListener('change', function () {
    const isLivestock = document.getElementById('cat-livestock').checked;
    document.getElementById('crop-field').style.display = isLivestock ? 'none' : '';
    document.getElementById('livestock-field').style.display = isLivestock ? '' : 'none';
    document.getElementById('crop').required = !isLivestock;
    document.getElementById('livestock').required = isLivestock;
  });
});
window.addEventListener('DOMContentLoaded', function () {
  const checked = document.querySelector('input[name="category"]:checked');
  if (checked) checked.dispatchEvent(new Event('change'));
});
</script>
{% if pricing_available %}''',
    label="new_listing.html category toggle script",
)

# ---------------------------------------------------------------------------
# 6b. templates/market.html — filter by category, combined product list
# ---------------------------------------------------------------------------
print("Patching templates/market.html ...")
patch(
    "templates/market.html",
    old='''      <div class="field" style="margin:0;">
        <label for="crop">Crop</label>
        <select id="crop" name="crop">
          <option value="">All crops</option>
          {% for c in crops %}
            <option value="{{ c }}" {{ 'selected' if c == sel_crop }}>{{ c }}</option>
          {% endfor %}
        </select>
      </div>''',
    new='''      <div class="field" style="margin:0;">
        <label for="category">Type</label>
        <select id="category" name="category">
          <option value="">All types</option>
          <option value="crop" {{ 'selected' if sel_category == 'crop' }}>Crops</option>
          <option value="livestock" {{ 'selected' if sel_category == 'livestock' }}>Livestock</option>
        </select>
      </div>
      <div class="field" style="margin:0;">
        <label for="crop">Product</label>
        <select id="crop" name="crop">
          <option value="">All products</option>
          {% for c in crops %}
            <option value="{{ c }}" {{ 'selected' if c == sel_crop }}>{{ c }}</option>
          {% endfor %}
          {% for a in livestock %}
            <option value="{{ a }}" {{ 'selected' if a == sel_crop }}>{{ a }}</option>
          {% endfor %}
        </select>
      </div>''',
    label="market.html category + combined product filter",
)

# ---------------------------------------------------------------------------
# 6c. templates/dashboard.html — trending section
# ---------------------------------------------------------------------------
print("Patching templates/dashboard.html ...")
patch(
    "templates/dashboard.html",
    old='''  <p>Your reputation: {{ ui.stars(rating['avg'], rating['count']) }}
     · <a href="{{ url_for('profile', user_id=user['id']) }}">View public profile</a></p>

  {% if user['role'] == 'farmer' %}''',
    new='''  <p>Your reputation: {{ ui.stars(rating['avg'], rating['count']) }}
     · <a href="{{ url_for('profile', user_id=user['id']) }}">View public profile</a></p>

  <div class="card" style="margin-top:20px;">
    <p class="eyebrow" style="margin-bottom:8px;">Trending in {{ user['region'] }}</p>
    {% if trending %}
      <div class="grid grid-3">
        {% for t in trending %}
          <span class="tag" style="align-self:flex-start;">
            <span class="amount">{{ t['crop'] }}</span>
            <span class="unit">{{ t['category'] | capitalize }} ·
              {{ t['total'] }} {{ 'sold' if trending_basis == 'sold' else 'listed' }}</span>
          </span>
        {% endfor %}
      </div>
    {% else %}
      <p class="muted" style="margin:0;">No trends yet for {{ user['region'] }} —
      be the first to buy or sell something here!</p>
    {% endif %}
  </div>

  {% if user['role'] == 'farmer' %}''',
    label="dashboard.html trending section",
)

print("\nDone. Reset the database (schema changed) and restart the app:")
print("  rm data/farmconnect.db")
print("  python3 app.py")
