"""
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
    "Addis Ababa": "Ethiopia",
    "Dakar": "Senegal",
    "Cairo": "Egypt",
    "Casablanca": "Morocco",
    "Tunis": "Tunisia",
    "Johannesburg": "South Africa",
    "Harare": "Zimbabwe",
    "Lusaka": "Zambia",
    "Kigali": "Rwanda",
    "Maputo": "Mozambique",
    "Kinshasa": "Congo (DRC)",
    "Yaounde": "Cameroon",
    "Luanda": "Angola",
    "Khartoum": "Sudan",
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
    "Ghana": ("GHS", "GH₵"),
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
    "Nigeria": ("NGN", "₦"),
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
