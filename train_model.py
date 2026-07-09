"""
train_model.py
--------------
Run this to TRAIN the AI pricing model.

Two ways to use it:

  1) With YOUR real historical data (a CSV file):
         python train_model.py my_prices.csv

     Your CSV must have these columns (header row required):
         crop, region, month, quantity_kg, price_per_kg
     - crop:          e.g. "Maize", "Tomato"      (text)
     - region:        an African country, e.g. "Kenya", "Nigeria" (text)
     - month:         1 to 12                       (whole number)
     - quantity_kg:   e.g. 50, 500                  (number)
     - price_per_kg:  the actual price it sold for, IN THAT COUNTRY'S OWN
                       LOCAL CURRENCY (the same currency farmers type into
                       the "price per kg" field on the site - see
                       currency.py). Mixing currencies within one country
                       will make the AI's suggestions wrong, since app.py
                       blends this number directly with real listing prices
                       which are entered in local currency.

  2) With NO data yet (generate sample data anchored on real prices
     where we have them, and clearly-labeled estimates elsewhere):
         python train_model.py

Either way, the trained model is saved to data/price_model.joblib and the
website will pick it up automatically.

---------------------------------------------------------------------------
Where the sample prices come from
---------------------------------------------------------------------------
Locations are country-level, so the model covers every African country.
Each country's prices are in THAT country's own local currency (matching
what farmers actually type into the "price per kg" field), not a shared
generic unit - this matters because app.py averages the AI's number
directly with real, currently-active listing prices.

Two tiers:
  - VERIFIED: read directly from a live, cited source. Currently this is
    only Uganda/Coffee, sourced from the Uganda Coffee Development
    Authority's official "Daily Coffee Market Analysis Report" farmgate
    price bulletins (ugandacoffee.go.ug), 6 dated reports Dec 2023-Feb
    2026. See REAL_COFFEE_KAMPALA_POINTS below for the exact figures,
    dates and URLs.
  - ESTIMATE: rough, illustrative order-of-magnitude figures from
    reference_prices.py (a typical farmgate USD price per crop, converted
    into each country's local currency), NOT read from a specific dated
    source. They exist so every crop/country the site offers has
    *something* plausible to show, but should be replaced with real data
    (via the CSV path above) before you rely on this for real decisions.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from pricing_model import PricingModel

import currency
import reference_prices

DATA_DIR = Path(__file__).parent / "data"
SAMPLE_CSV = DATA_DIR / "sample_prices.csv"

# Locations are country-level (pan-African): every African country.
REGIONS = currency.COUNTRIES
# Crops the model learns — kept in sync with the reference-price table so the
# AI estimate and the Trends "reference" prices cover the same staples.
CROPS = reference_prices.REFERENCE_CROPS

# Which months are peak harvest (cheaper) per crop, roughly.
# We give each crop a "cheap month" and prices rise the further away you get.
HARVEST_MONTH = {
    "Maize": 8, "Tomato": 3, "Cassava": 11, "Rice": 10, "Beans": 6,
    "Plantain": 9, "Onion": 2, "Irish Potato": 7, "Cocoa": 12, "Coffee": 11,
}

# ---------------------------------------------------------------------------
# VERIFIED real data: Kampala coffee farmgate prices, read directly from
# UCDA's official "Daily Coffee Market Analysis Report" PDFs. "FAQ" (Fair
# Average Quality, clean/hulled Robusta) is the closest match to a per-kg
# sale price a farmer on this site would be quoting. We use the midpoint of
# each week's printed range.
#   Source: Uganda Coffee Development Authority, ugandacoffee.go.ug
# ---------------------------------------------------------------------------
REAL_COFFEE_KAMPALA_POINTS = [
    # (month, price_per_kg UGX, report date, source URL)
    (12, 8000, "2023-12-01",
     "ugandacoffee.go.ug/sites/default/files/2023-12/UCDA%20Daily%20Coffee%20Market%20Report%20(December%201%202023).pdf"),
    (2, 9750, "2024-02-06",
     "ugandacoffee.go.ug/sites/default/files/2024-02/UCDA%20Daily%20Coffee%20Market%20Report%20(February%206%202024).pdf"),
    (5, 12750, "2024-05-06",
     "ugandacoffee.go.ug/sites/default/files/2024-05/UCDA%20Daily%20Coffee%20Market%20Report%20(May%206%202024).pdf"),
    (11, 12600, "2024-11-18",
     "ugandacoffee.go.ug/sites/default/files/2024-11/UCDA%20Daily%20Coffee%20Market%20Report%20(November%2018th%202024).pdf"),
    (9, 12500, "2025-09-29",
     "ugandacoffee.go.ug/sites/default/files/2025-09/Daily%20Coffee%20Market%20Report%20(September%2029th%20%20%202025).%20(1).ppt%20II.pdf"),
    (2, 12500, "2026-02-05",
     "ugandacoffee.go.ug/sites/default/files/2026-02/Daily%20Coffee%20Market%20Report%20(February%205th%20%20%202026).pdf"),
]


def _real_data_rows() -> pd.DataFrame:
    """Verified real price points, replicated across a spread of realistic
    quantities so they carry meaningful weight during training (a single
    row per data point would be drowned out by thousands of estimated
    rows)."""
    records = []
    for month, price, _date, _url in REAL_COFFEE_KAMPALA_POINTS:
        for quantity in [10, 25, 50, 100, 250, 500, 1000]:
            bulk = 1.0 - min(quantity / 1000, 1.0) * 0.15
            records.append(("Coffee", "Uganda", month, quantity, round(price * bulk, 2)))
    return pd.DataFrame(records, columns=["crop", "region", "month", "quantity_kg", "price_per_kg"])


def generate_sample_data(rows: int = 8000, seed: int = 42) -> pd.DataFrame:
    """Create a believable pan-African dataset with seasonality and bulk
    discounts. Base prices come from reference_prices (a typical farmgate USD
    price per crop, converted into each country's local currency with a
    baked-in rate snapshot). These are clearly-labeled estimates, layered with
    the verified Kampala/Coffee points below - see the module docstring."""
    rng = np.random.default_rng(seed)
    records = []

    for _ in range(rows):
        crop = str(rng.choice(CROPS))
        region = str(rng.choice(REGIONS))
        month = int(rng.integers(1, 13))
        quantity = float(rng.choice([10, 25, 50, 100, 250, 500, 1000]))

        base = reference_prices.base_local(crop, region)
        if base is None:
            continue

        # Seasonality: cheapest at harvest month, up to +35% off-season.
        harvest = HARVEST_MONTH[crop]
        # Circular distance between this month and the harvest month (0..6).
        dist = min((month - harvest) % 12, (harvest - month) % 12)
        season = 1 + 0.35 * (dist / 6)

        # Bulk discount: buying 1000kg is cheaper per kg than buying 10kg.
        bulk = 1.0 - min(quantity / 1000, 1.0) * 0.15

        # A little random market noise so the model has something to learn.
        noise = rng.normal(1.0, 0.05)

        price = round(base * season * bulk * noise, 2)
        records.append((crop, region, month, quantity, max(price, 0.05)))

    synthetic = pd.DataFrame(
        records, columns=["crop", "region", "month", "quantity_kg", "price_per_kg"]
    )
    # Layer the verified real points on top so the model actually learns
    # from them rather than treating Kampala/Coffee as pure estimate.
    return pd.concat([synthetic, _real_data_rows()], ignore_index=True)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
        if not csv_path.exists():
            print(f"Could not find file: {csv_path}")
            sys.exit(1)
        print(f"Loading your data from {csv_path} ...")
        df = pd.read_csv(csv_path)
    else:
        print("No CSV given. Generating sample data (real Kampala/Coffee")
        print("prices from UCDA + clearly-labeled estimates elsewhere).")
        df = generate_sample_data()
        df.to_csv(SAMPLE_CSV, index=False)
        print(f"Saved a sample dataset you can inspect at: {SAMPLE_CSV}")
        print("  (Match this column layout when you bring your own data.)")
        print("  (Prices are in each region's own local currency - see the")
        print("   module docstring in train_model.py for which figures are")
        print("   verified real data vs. illustrative estimates.)")

    print(f"\nTraining on {len(df):,} rows ...")
    model = PricingModel()
    metrics = model.train(df)
    model.save()

    print("\nDone! Model saved to data/price_model.joblib")
    print("-" * 40)
    print(f"Rows trained on:        {metrics['rows_trained_on']:,}")
    print(f"Average error (+/-):    {metrics['mean_absolute_error']} per kg")
    print(f"Accuracy score (R2):    {metrics['r2_score']}  (1.0 is perfect)")
    print("-" * 40)
    print(f"Crops it knows:   {', '.join(model.known_crops)}")
    print(f"Regions it knows: {', '.join(model.known_regions)}")


if __name__ == "__main__":
    main()
