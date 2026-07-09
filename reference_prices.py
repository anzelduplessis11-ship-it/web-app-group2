"""
reference_prices.py
--------------------
Estimated, clearly-labeled reference prices for every African country, so the
marketplace and the Trends "Live price board" always have *something* useful to
show — even in a country where no FarmConnect farmer has listed anything yet.

Design (pan-African by construction):
  * We keep ONE small table of typical farmgate prices per crop, expressed in
    US dollars per kg (REFERENCE_PRICES_USD). These are rough, illustrative
    order-of-magnitude figures — NOT a live market feed and NOT authoritative.
  * At display time we convert that USD figure into the viewer's own local
    currency using the live exchange rates already fetched by currency.py.
    That single small table therefore covers all 54 countries with sensible
    local-currency magnitudes, with no per-country price tables to maintain.
  * If live rates can't be fetched (offline / API down), we fall back to a
    baked-in snapshot of approximate USD rates (FALLBACK_USD_RATES) so the
    board never goes blank. The same snapshot gives train_model.py a
    deterministic, offline base for generating sample training data.

Every number produced here is an ESTIMATE and is labeled as such in the UI.
When real historical prices are available, train the model on them (see
train_model.py) — the live listings farmers post always take priority over
these reference figures.
"""
from __future__ import annotations

import currency

# --- Typical farmgate price per crop, in USD/kg: (low, mid, high) ------------
# Rough order-of-magnitude estimates for smallholder farmgate prices across
# sub-Saharan Africa. Illustrative only; refine with real data when available.
REFERENCE_PRICES_USD: dict[str, tuple[float, float, float]] = {
    "Maize":        (0.18, 0.28, 0.42),
    "Tomato":       (0.35, 0.60, 0.95),
    "Cassava":      (0.10, 0.18, 0.30),
    "Rice":         (0.45, 0.70, 1.05),
    "Beans":        (0.60, 0.95, 1.40),
    "Plantain":     (0.25, 0.40, 0.65),
    "Onion":        (0.30, 0.50, 0.80),
    "Irish Potato": (0.25, 0.42, 0.65),
    "Cocoa":        (1.80, 2.60, 3.60),
    "Coffee":       (2.00, 3.20, 4.80),
}

# Display/order the board uses for reference rows.
REFERENCE_CROPS: list[str] = list(REFERENCE_PRICES_USD.keys())

# --- Approximate USD exchange rates (units of currency per 1 USD) ------------
# A baked-in snapshot used only when live rates are unavailable, and by
# train_model.py for deterministic offline training. Approximate; not live.
FALLBACK_USD_RATES: dict[str, float] = {
    "USD": 1.0,
    "DZD": 134.0, "AOA": 910.0, "XOF": 605.0, "BWP": 13.5, "BIF": 2950.0,
    "CVE": 100.0, "XAF": 605.0, "KMF": 455.0, "CDF": 2800.0, "DJF": 178.0,
    "EGP": 49.0, "ERN": 15.0, "SZL": 18.0, "ETB": 120.0, "GMD": 70.0,
    "GHS": 15.5, "GNF": 8600.0, "KES": 129.0, "LSL": 18.0, "LRD": 193.0,
    "LYD": 4.85, "MGA": 4550.0, "MWK": 1735.0, "MRU": 39.8, "MUR": 46.0,
    "MAD": 9.9, "MZN": 63.9, "NAD": 18.0, "NGN": 1580.0, "RWF": 1370.0,
    "STN": 22.5, "SCR": 13.7, "SLL": 22500.0, "SOS": 571.0, "ZAR": 18.0,
    "SSP": 3100.0, "SDG": 601.0, "TZS": 2680.0, "TND": 3.1, "UGX": 3720.0,
    "ZMW": 26.5, "ZWL": 26.0,
}


def usd_rate(code: str, live: bool = True) -> float | None:
    """Units of `code` per 1 USD. Prefers live rates, falls back to the
    baked-in snapshot. Returns None if the currency is unknown to us."""
    if not code:
        return None
    if live:
        rates = currency.get_rates()
        if rates and code in rates:
            return rates[code]
    return FALLBACK_USD_RATES.get(code)


def _tidy(value: float) -> float:
    """Round to a clean, human-sensible figure for the currency's magnitude."""
    if value >= 1000:
        return round(value / 50) * 50
    if value >= 100:
        return round(value / 5) * 5
    if value >= 10:
        return round(value)
    return round(value, 2)


def estimate(crop: str, region: str, live: bool = True) -> dict | None:
    """Estimated local-currency reference price for a crop in a region/country.

    Returns {"low","mid","high","code","symbol","is_estimate": True} in the
    region's own currency, or None if we can't (unknown crop, currency, or
    rate). `live=False` forces the offline snapshot (used during training).
    """
    band = REFERENCE_PRICES_USD.get(crop)
    if band is None:
        return None
    code, symbol = currency.currency_for_region(region)
    rate = usd_rate(code, live=live)
    if not code or rate is None:
        return None
    low, mid, high = band
    return {
        "low": _tidy(low * rate),
        "mid": _tidy(mid * rate),
        "high": _tidy(high * rate),
        "code": code,
        "symbol": symbol or code,
        "is_estimate": True,
    }


def base_local(crop: str, region: str) -> float | None:
    """Deterministic offline mid-price in local currency, for training data."""
    band = REFERENCE_PRICES_USD.get(crop)
    if band is None:
        return None
    code, _ = currency.currency_for_region(region)
    rate = FALLBACK_USD_RATES.get(code)
    if rate is None:
        return None
    return band[1] * rate
