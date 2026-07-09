"""
apply_currency_patch.py
--------------------------
Run this once from inside your `farmconnect` folder:

    python3 apply_currency_patch.py

It will:
  1. Create currency.py: a complete map of every African country to its
     official currency (54 countries), plus a region->country lookup for
     your existing 6 regions, plus live exchange-rate conversion using a
     free, keyless API (rates cached for an hour so the app stays fast)
  2. Add currency helper functions to app.py, available in every template:
       currency_symbol(region), currency_code(region), converted_price(amount, region)
  3. Update templates/market.html to show each listing's real local
     currency, plus a live-converted price "for you" if you're logged in
     and your own region uses a different currency
  4. Update templates/new_listing.html so the price label shows your own
     currency code

Notes:
  - If the exchange-rate API can't be reached (no internet, rate limited),
    conversion is simply skipped - the app keeps working, it just won't
    show the "for you" converted amount.
  - Several African countries share a currency on purpose (e.g. the West
    and Central African CFA francs) - that's correct, not a bug.
  - Your active REGIONS list still only has 6 cities; the full 54-country
    currency table is ready to use the moment you add more regions/countries.

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
# 1. currency.py — new file
# ---------------------------------------------------------------------------
print("Creating currency.py ...")
currency_path = ROOT / "currency.py"
if currency_path.exists():
    print("  [skip] currency.py already exists")
else:
    currency_path.write_text('''"""
currency.py
------------
Maps FarmConnect's regions to countries and their official African
currencies (ISO 4217), and does live currency conversion using a free,
keyless exchange-rate API.

If live rates can't be fetched (no internet, API down), conversion is
skipped and the original amount/currency is shown instead - the app
never breaks because of this.
"""

import time
import json
import urllib.request

# Which country each of FarmConnect's current regions is in.
REGION_COUNTRY = {
    "Nairobi": "Kenya",
    "Kano": "Nigeria",
    "Lagos": "Nigeria",
    "Kumasi": "Ghana",
    "Kampala": "Uganda",
    "Arusha": "Tanzania",
}

# Currency code + symbol for every African country (ISO 4217 codes).
# Several countries intentionally share a currency (e.g. the CFA francs).
AFRICAN_CURRENCIES = {
    "Algeria": ("DZD", "DA"),
    "Angola": ("AOA", "Kz"),
    "Benin": ("XOF", "CFA"),
    "Botswana": ("BWP", "P"),
    "Burkina Faso": ("XOF", "CFA"),
    "Burundi": ("BIF", "FBu"),
    "Cabo Verde": ("CVE", "$"),
    "Cameroon": ("XAF", "FCFA"),
    "Central African Republic": ("XAF", "FCFA"),
    "Chad": ("XAF", "FCFA"),
    "Comoros": ("KMF", "CF"),
    "Congo (DRC)": ("CDF", "FC"),
    "Congo (Republic)": ("XAF", "FCFA"),
    "Cote d'Ivoire": ("XOF", "CFA"),
    "Djibouti": ("DJF", "Fdj"),
    "Egypt": ("EGP", "E£"),
    "Equatorial Guinea": ("XAF", "FCFA"),
    "Eritrea": ("ERN", "Nfk"),
    "Eswatini": ("SZL", "L"),
    "Ethiopia": ("ETB", "Br"),
    "Gabon": ("XAF", "FCFA"),
    "Gambia": ("GMD", "D"),
    "Ghana": ("GHS", "GH\u20b5"),
    "Guinea": ("GNF", "FG"),
    "Guinea-Bissau": ("XOF", "CFA"),
    "Kenya": ("KES", "KSh"),
    "Lesotho": ("LSL", "L"),
    "Liberia": ("LRD", "L$"),
    "Libya": ("LYD", "LD"),
    "Madagascar": ("MGA", "Ar"),
    "Malawi": ("MWK", "MK"),
    "Mali": ("XOF", "CFA"),
    "Mauritania": ("MRU", "UM"),
    "Mauritius": ("MUR", "Rs"),
    "Morocco": ("MAD", "DH"),
    "Mozambique": ("MZN", "MT"),
    "Namibia": ("NAD", "N$"),
    "Niger": ("XOF", "CFA"),
    "Nigeria": ("NGN", "\u20a6"),
    "Rwanda": ("RWF", "FRw"),
    "Sao Tome and Principe": ("STN", "Db"),
    "Senegal": ("XOF", "CFA"),
    "Seychelles": ("SCR", "Rs"),
    "Sierra Leone": ("SLL", "Le"),
    "Somalia": ("SOS", "Sh"),
    "South Africa": ("ZAR", "R"),
    "South Sudan": ("SSP", "SSP"),
    "Sudan": ("SDG", "SDG"),
    "Tanzania": ("TZS", "TSh"),
    "Togo": ("XOF", "CFA"),
    "Tunisia": ("TND", "DT"),
    "Uganda": ("UGX", "USh"),
    "Zambia": ("ZMW", "ZK"),
    "Zimbabwe": ("ZWL", "Z$"),
}


def country_for_region(region):
    """Best-effort: which country is this FarmConnect region in?"""
    return REGION_COUNTRY.get(region)


def currency_for_region(region):
    """Return (code, symbol) for a region, or (None, None) if unknown."""
    country = country_for_region(region)
    if country is None:
        return (None, None)
    return AFRICAN_CURRENCIES.get(country, (None, None))


# ---------------------------------------------------------------------------
# Live exchange rates (cached for an hour so we don't hit the API on every
# page load). Uses the free, keyless endpoint at open.er-api.com.
# ---------------------------------------------------------------------------
_rates_cache = {"rates": None, "fetched_at": 0}
_CACHE_SECONDS = 60 * 60  # 1 hour


def _fetch_rates():
    url = "https://open.er-api.com/v6/latest/USD"
    with urllib.request.urlopen(url, timeout=5) as resp:
        data = json.loads(resp.read().decode())
    if data.get("result") != "success":
        raise ValueError("Exchange rate API did not return success.")
    return data["rates"]


def get_rates():
    """Return {currency_code: rate_vs_usd}, using a cached copy when it's
    less than an hour old. Returns None if rates can't be fetched at all
    (e.g. no internet) - callers should handle that gracefully."""
    now = time.time()
    if _rates_cache["rates"] and (now - _rates_cache["fetched_at"] < _CACHE_SECONDS):
        return _rates_cache["rates"]
    try:
        rates = _fetch_rates()
        _rates_cache["rates"] = rates
        _rates_cache["fetched_at"] = now
        return rates
    except Exception:
        # Fall back to a stale cache if we have one, otherwise give up quietly.
        return _rates_cache["rates"]


def convert(amount, from_code, to_code):
    """Convert `amount` from one currency code to another. Returns None if
    conversion isn't possible right now (rates unavailable, unknown code)."""
    if not from_code or not to_code:
        return None
    if from_code == to_code:
        return amount
    rates = get_rates()
    if not rates or from_code not in rates or to_code not in rates:
        return None
    amount_in_usd = amount / rates[from_code]
    return amount_in_usd * rates[to_code]
''')
    print("  [ok] currency.py created")

# ---------------------------------------------------------------------------
# 2. app.py — import currency + template helper functions
# ---------------------------------------------------------------------------
print("Patching app.py ...")
patch(
    "app.py",
    old='''import db
from pricing_model import PricingModel''',
    new='''import db
import currency
from pricing_model import PricingModel''',
    label="import currency module",
)

patch(
    "app.py",
    old='''@app.context_processor
def inject_user():
    """Make `user` and unread-message count available in every template."""
    user = current_user()
    unread = 0
    if user:
        row = db.query_one(
            "SELECT COUNT(*) AS n FROM messages WHERE recipient_id = ? AND is_read = 0",
            (user["id"],),
        )
        unread = row["n"]
    return {"user": user, "unread_count": unread}''',
    new='''@app.context_processor
def inject_user():
    """Make `user` and unread-message count available in every template."""
    user = current_user()
    unread = 0
    if user:
        row = db.query_one(
            "SELECT COUNT(*) AS n FROM messages WHERE recipient_id = ? AND is_read = 0",
            (user["id"],),
        )
        unread = row["n"]
    return {"user": user, "unread_count": unread}


@app.context_processor
def inject_currency_helpers():
    """Make currency helpers available in every template."""
    def currency_symbol(region):
        code, symbol = currency.currency_for_region(region)
        return symbol or code or ""

    def currency_code(region):
        code, symbol = currency.currency_for_region(region)
        return code or ""

    def converted_price(amount, listing_region):
        """Convert a listing's price into the current viewer's own
        currency, if we know both currencies and live rates are available.
        Returns None (shows nothing) if conversion isn't possible."""
        viewer = current_user()
        if viewer is None:
            return None
        from_code, _ = currency.currency_for_region(listing_region)
        to_code, to_symbol = currency.currency_for_region(viewer["region"])
        if not from_code or not to_code or from_code == to_code:
            return None
        result = currency.convert(amount, from_code, to_code)
        if result is None:
            return None
        return {"amount": result, "code": to_code, "symbol": to_symbol}

    return {
        "currency_symbol": currency_symbol,
        "currency_code": currency_code,
        "converted_price": converted_price,
    }''',
    label="currency helper functions",
)

# ---------------------------------------------------------------------------
# 3. templates/market.html — show real currency + converted price
# ---------------------------------------------------------------------------
print("Patching templates/market.html ...")
patch(
    "templates/market.html",
    old='''      {% for l in listings %}
        <a class="card listing-card" href="{{ url_for('listing_detail', listing_id=l['id']) }}" style="text-decoration:none;color:inherit;">
          <div class="crop">{{ l['crop'] }}</div>
          <div class="meta">{{ l['region'] }} · {{ l['quantity_kg'] | int }} kg available</div>
          <span class="tag" style="align-self:flex-start;">
            <span class="amount">{{ "%.2f"|format(l['price_per_kg']) }}</span>
            <span class="unit">per kg</span>
          </span>
          <div class="meta">by {{ l['farmer_name'] }}</div>
        </a>
      {% endfor %}''',
    new='''      {% for l in listings %}
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
    label="market.html shows real currency + conversion",
)

# ---------------------------------------------------------------------------
# 4. templates/new_listing.html — price label shows farmer's own currency
# ---------------------------------------------------------------------------
print("Patching templates/new_listing.html ...")
patch(
    "templates/new_listing.html",
    old='''        <label for="price_per_kg">Your price per kg</label>''',
    new='''        <label for="price_per_kg">Your price per kg ({{ currency_code(user['region']) }})</label>''',
    label="new_listing.html price label shows currency",
)

print("\nDone. Restart the app to see the changes (no database reset needed).")
print("  python3 app.py")
