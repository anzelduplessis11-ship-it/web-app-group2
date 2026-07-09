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
     - region:        e.g. "Nairobi", "Kano"       (text)
     - month:         1 to 12                       (whole number)
     - quantity_kg:   e.g. 50, 500                  (number)
     - price_per_kg:  the actual price it sold for, IN THE SAME LOCAL
                       CURRENCY farmers in that region use to price
                       their listings (see currency.py) - e.g. KES for
                       Nairobi, NGN for Kano/Lagos, GHS for Kumasi, UGX
                       for Kampala, TZS for Arusha. Mixing currencies in
                       one region will make the AI's suggestions wrong,
                       since app.py blends this number directly with real
                       listing prices which are entered in local currency.

  2) With NO data yet (generate sample data anchored on real prices
     where we have them, and clearly-labeled estimates elsewhere):
         python train_model.py

Either way, the trained model is saved to data/price_model.joblib and the
website will pick it up automatically.

---------------------------------------------------------------------------
Where BASE_PRICES_BY_REGION below came from
---------------------------------------------------------------------------
Every region's prices are in THAT region's own local currency (matching
what farmers actually type into the "price per kg" field on the site), not
a shared generic unit - this matters because app.py averages the AI's
number directly with real, currently-active listing prices.

Two tiers, marked per entry:
  - VERIFIED: read directly from a live, cited source. Currently this is
    only Kampala/Coffee, sourced from the Uganda Coffee Development
    Authority's official "Daily Coffee Market Analysis Report" farmgate
    price bulletins (ugandacoffee.go.ug), 6 dated reports Dec 2023-Feb
    2026. See REAL_COFFEE_KAMPALA_POINTS below for the exact figures,
    dates and URLs.
  - ESTIMATE: a rough, illustrative order-of-magnitude figure based on
    general knowledge of typical staple-crop prices in that country, NOT
    read from a specific dated source. These exist so every crop/region
    combination the site offers has *something* plausible to show, but
    they should be replaced with real data (via the CSV path above) before
    you rely on this for real farmers' decisions.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from pricing_model import PricingModel

DATA_DIR = Path(__file__).parent / "data"
SAMPLE_CSV = DATA_DIR / "sample_prices.csv"

REGIONS = [
    "Nairobi", "Kano", "Kumasi", "Kampala", "Arusha", "Lagos",
    "Addis Ababa", "Dakar", "Cairo", "Casablanca", "Tunis",
    "Johannesburg", "Harare", "Lusaka", "Kigali", "Maputo",
    "Kinshasa", "Yaounde", "Luanda", "Khartoum",
]
CROPS = [
    "Maize", "Tomato", "Cassava", "Rice", "Beans", "Plantain",
    "Onion", "Irish Potato", "Cocoa", "Coffee",
]

# Base price per kg, in EACH REGION'S OWN LOCAL CURRENCY (see currency.py):
#   Nairobi -> KES, Kano/Lagos -> NGN, Kumasi -> GHS, Kampala -> UGX,
#   Arusha -> TZS.
# "source" is "verified" (see REAL_COFFEE_KAMPALA_POINTS) or "estimate"
# (illustrative order-of-magnitude only - see module docstring).
BASE_PRICES_BY_REGION = {
    "Nairobi": {  # KES/kg
        "Maize": 55, "Tomato": 80, "Cassava": 35, "Rice": 140,
        "Beans": 145, "Plantain": 60, "Onion": 85, "Irish Potato": 50,
        "Cocoa": 300, "Coffee": 450,
    },
    "Kano": {  # NGN/kg
        "Maize": 600, "Tomato": 600, "Cassava": 200, "Rice": 1300,
        "Beans": 1300, "Plantain": 500, "Onion": 650, "Irish Potato": 700,
        "Cocoa": 6000, "Coffee": 3000,
    },
    "Lagos": {  # NGN/kg (produce typically costs a bit more than Kano)
        "Maize": 700, "Tomato": 750, "Cassava": 250, "Rice": 1500,
        "Beans": 1500, "Plantain": 550, "Onion": 750, "Irish Potato": 800,
        "Cocoa": 6500, "Coffee": 3200,
    },
    "Kumasi": {  # GHS/kg
        "Maize": 9, "Tomato": 11, "Cassava": 4, "Rice": 17,
        "Beans": 20, "Plantain": 8, "Onion": 12, "Irish Potato": 10,
        "Cocoa": 48, "Coffee": 30,
    },
    "Kampala": {  # UGX/kg
        "Maize": 1000, "Tomato": 2000, "Cassava": 650, "Rice": 3500,
        "Beans": 3800, "Plantain": 1100, "Onion": 2200, "Irish Potato": 1800,
        "Cocoa": 4000,
        "Coffee": 9500,  # ESTIMATE fallback only - real points below override nearby months
    },
    "Arusha": {  # TZS/kg
        "Maize": 850, "Tomato": 1200, "Cassava": 650, "Rice": 3000,
        "Beans": 3200, "Plantain": 900, "Onion": 1100, "Irish Potato": 1200,
        "Cocoa": 3500, "Coffee": 7500,
    },
    # The regions below are ESTIMATES only (illustrative order-of-magnitude
    # figures, not from a specific dated source - see module docstring).
    "Addis Ababa": {  # ETB/kg
        "Maize": 25, "Tomato": 40, "Cassava": 20, "Rice": 80,
        "Beans": 70, "Plantain": 35, "Onion": 45, "Irish Potato": 25,
        "Cocoa": 250, "Coffee": 350,
    },
    "Dakar": {  # XOF/kg
        "Maize": 350, "Tomato": 400, "Cassava": 150, "Rice": 700,
        "Beans": 750, "Plantain": 300, "Onion": 380, "Irish Potato": 400,
        "Cocoa": 3500, "Coffee": 2000,
    },
    "Cairo": {  # EGP/kg
        "Maize": 15, "Tomato": 18, "Cassava": 10, "Rice": 35,
        "Beans": 40, "Plantain": 20, "Onion": 15, "Irish Potato": 14,
        "Cocoa": 150, "Coffee": 200,
    },
    "Casablanca": {  # MAD/kg
        "Maize": 6, "Tomato": 7, "Cassava": 5, "Rice": 14,
        "Beans": 16, "Plantain": 8, "Onion": 6, "Irish Potato": 5,
        "Cocoa": 60, "Coffee": 80,
    },
    "Tunis": {  # TND/kg
        "Maize": 2, "Tomato": 2.5, "Cassava": 1.8, "Rice": 4.5,
        "Beans": 5, "Plantain": 2.8, "Onion": 2, "Irish Potato": 1.8,
        "Cocoa": 18, "Coffee": 25,
    },
    "Johannesburg": {  # ZAR/kg
        "Maize": 6, "Tomato": 12, "Cassava": 8, "Rice": 22,
        "Beans": 28, "Plantain": 10, "Onion": 9, "Irish Potato": 9,
        "Cocoa": 90, "Coffee": 130,
    },
    "Harare": {  # ZWL/kg
        "Maize": 1500, "Tomato": 2500, "Cassava": 1000, "Rice": 4500,
        "Beans": 5000, "Plantain": 1800, "Onion": 2000, "Irish Potato": 1600,
        "Cocoa": 15000, "Coffee": 20000,
    },
    "Lusaka": {  # ZMW/kg
        "Maize": 8, "Tomato": 14, "Cassava": 6, "Rice": 25,
        "Beans": 30, "Plantain": 10, "Onion": 11, "Irish Potato": 9,
        "Cocoa": 100, "Coffee": 140,
    },
    "Kigali": {  # RWF/kg
        "Maize": 350, "Tomato": 500, "Cassava": 250, "Rice": 900,
        "Beans": 950, "Plantain": 400, "Onion": 450, "Irish Potato": 300,
        "Cocoa": 3000, "Coffee": 3800,
    },
    "Maputo": {  # MZN/kg
        "Maize": 35, "Tomato": 55, "Cassava": 25, "Rice": 90,
        "Beans": 100, "Plantain": 45, "Onion": 48, "Irish Potato": 40,
        "Cocoa": 350, "Coffee": 450,
    },
    "Kinshasa": {  # CDF/kg
        "Maize": 800, "Tomato": 1400, "Cassava": 600, "Rice": 2800,
        "Beans": 3000, "Plantain": 900, "Onion": 1100, "Irish Potato": 900,
        "Cocoa": 8000, "Coffee": 10000,
    },
    "Yaounde": {  # XAF/kg
        "Maize": 350, "Tomato": 450, "Cassava": 150, "Rice": 750,
        "Beans": 800, "Plantain": 300, "Onion": 400, "Irish Potato": 380,
        "Cocoa": 1200, "Coffee": 2200,
    },
    "Luanda": {  # AOA/kg
        "Maize": 250, "Tomato": 400, "Cassava": 150, "Rice": 750,
        "Beans": 800, "Plantain": 300, "Onion": 350, "Irish Potato": 300,
        "Cocoa": 3000, "Coffee": 3500,
    },
    "Khartoum": {  # SDG/kg
        "Maize": 450, "Tomato": 700, "Cassava": 350, "Rice": 1400,
        "Beans": 1500, "Plantain": 600, "Onion": 650, "Irish Potato": 500,
        "Cocoa": 5000, "Coffee": 6000,
    },
}

# A gentle regional multiplier so prices differ by place.
REGION_FACTOR = {
    "Nairobi": 1.10, "Kano": 0.92, "Kumasi": 1.00,
    "Kampala": 0.95, "Arusha": 1.05, "Lagos": 1.15,
    "Addis Ababa": 1.00, "Dakar": 1.05, "Cairo": 0.95,
    "Casablanca": 1.02, "Tunis": 0.98, "Johannesburg": 1.12,
    "Harare": 0.90, "Lusaka": 0.97, "Kigali": 1.03,
    "Maputo": 0.95, "Kinshasa": 0.93, "Yaounde": 1.00,
    "Luanda": 1.08, "Khartoum": 0.92,
}

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
            records.append(("Coffee", "Kampala", month, quantity, round(price * bulk, 2)))
    return pd.DataFrame(records, columns=["crop", "region", "month", "quantity_kg", "price_per_kg"])


def generate_sample_data(rows: int = 4000, seed: int = 42) -> pd.DataFrame:
    """Create a believable dataset with seasonality and bulk discounts,
    anchored on BASE_PRICES_BY_REGION (real where we have it, clearly
    labeled estimates elsewhere - see the module docstring)."""
    rng = np.random.default_rng(seed)
    records = []

    for _ in range(rows):
        crop = rng.choice(CROPS)
        region = rng.choice(REGIONS)
        month = int(rng.integers(1, 13))
        quantity = float(rng.choice([10, 25, 50, 100, 250, 500, 1000]))

        base = BASE_PRICES_BY_REGION[region][crop]

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
