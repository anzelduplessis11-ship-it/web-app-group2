"""
pricing_model.py
----------------
The "AI-assisted pricing" engine for FarmConnect.

What it does, in plain terms:
  A farmer tells us WHAT they are selling (crop), WHERE they are (region),
  WHEN it is (month), and HOW MUCH they have (quantity in kg). This model,
  trained on historical price data, answers: "A fair price is about X per kg,
  and a reasonable range is between LOW and HIGH."

How it works:
  - It is a RandomForestRegressor (a collection of decision trees that vote).
  - Text inputs (crop, region) are one-hot encoded so the model can use them.
  - The month is turned into sine/cosine values so "December" and "January"
    are treated as close together (seasonality is circular).
  - Because a random forest is many trees, we read each tree's individual
    guess to produce a fair LOW-HIGH range, not just one number.

You train it on real data by running:  python train_model.py your_prices.csv
If you have no data yet, train_model.py can generate realistic sample data.
"""
from __future__ import annotations


import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

# Where the trained model file is saved/loaded from.
MODEL_PATH = Path(__file__).parent / "data" / "price_model.joblib"

# The columns the model expects as input, in order.
CATEGORICAL = ["crop", "region"]
NUMERIC = ["quantity_kg", "month_sin", "month_cos"]


def _add_month_cycle(df: pd.DataFrame) -> pd.DataFrame:
    """Turn month (1-12) into two smooth cyclical features.

    Why: month 12 (Dec) and month 1 (Jan) are one step apart in real life,
    but 12 and 1 look 'far apart' as plain numbers. Sine/cosine fixes that
    so the model understands seasons wrap around the year.
    """
    df = df.copy()
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    return df


class PricingModel:
    """A thin, friendly wrapper around a scikit-learn pipeline."""

    def __init__(self):
        self.pipeline: Pipeline | None = None
        # Filled in after training so the website can show dropdowns.
        self.known_crops: list[str] = []
        self.known_regions: list[str] = []

    # ---------- TRAINING ----------
    def train(self, df: pd.DataFrame) -> dict:
        """Fit the model on a table of historical prices.

        Expected columns: crop, region, month, quantity_kg, price_per_kg
        Returns a dict of accuracy metrics so you can see how good it is.
        """
        required = {"crop", "region", "month", "quantity_kg", "price_per_kg"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Your data is missing these columns: {missing}")

        df = _add_month_cycle(df)
        X = df[CATEGORICAL + NUMERIC]
        y = df["price_per_kg"]

        # Remember the categories so the website can build dropdown menus.
        self.known_crops = sorted(df["crop"].unique().tolist())
        self.known_regions = sorted(df["region"].unique().tolist())

        # One-hot encode the text columns; leave the numbers as they are.
        preprocess = ColumnTransformer(
            transformers=[
                ("cats", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
            ],
            remainder="passthrough",  # numeric columns pass straight through
        )

        model = RandomForestRegressor(
            n_estimators=300,   # 300 trees vote on each prediction
            max_depth=None,
            min_samples_leaf=2,
            random_state=42,    # makes results reproducible
            n_jobs=-1,          # use all CPU cores
        )

        self.pipeline = Pipeline([("prep", preprocess), ("model", model)])

        # Hold back 20% of data to honestly measure accuracy.
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        self.pipeline.fit(X_train, y_train)

        preds = self.pipeline.predict(X_test)
        return {
            "rows_trained_on": len(X_train),
            "mean_absolute_error": round(float(mean_absolute_error(y_test, preds)), 2),
            "r2_score": round(float(r2_score(y_test, preds)), 3),
        }

    # ---------- SAVING / LOADING ----------
    def save(self, path: Path = MODEL_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "pipeline": self.pipeline,
                "known_crops": self.known_crops,
                "known_regions": self.known_regions,
            },
            path,
        )

    @classmethod
    def load(cls, path: Path = MODEL_PATH) -> "PricingModel | None":
        """Load a saved model, or return None if none has been trained yet."""
        if not Path(path).exists():
            return None
        blob = joblib.load(path)
        obj = cls()
        obj.pipeline = blob["pipeline"]
        obj.known_crops = blob["known_crops"]
        obj.known_regions = blob["known_regions"]
        return obj

    # ---------- PREDICTING ----------
    def suggest(self, crop: str, region: str, month: int, quantity_kg: float) -> dict:
        """Return a suggested fair price plus a low-high range.

        The range comes from asking every tree in the forest for its own
        guess and taking the 10th and 90th percentiles. A wide gap means
        'the market is uncertain here'; a narrow gap means 'this is well
        established'.
        """
        if self.pipeline is None:
            raise RuntimeError("Model is not trained yet.")

        row = _add_month_cycle(
            pd.DataFrame([{
                "crop": crop,
                "region": region,
                "month": int(month),
                "quantity_kg": float(quantity_kg),
            }])
        )
        X = row[CATEGORICAL + NUMERIC]

        # Main prediction (the average of all trees).
        suggested = float(self.pipeline.predict(X)[0])

        # Individual tree predictions, for the fair range.
        # We must transform the input the same way the pipeline does first.
        prep = self.pipeline.named_steps["prep"]
        forest = self.pipeline.named_steps["model"]
        X_transformed = prep.transform(X)
        tree_guesses = np.array([t.predict(X_transformed)[0] for t in forest.estimators_])

        low = float(np.percentile(tree_guesses, 10))
        high = float(np.percentile(tree_guesses, 90))

        return {
            "suggested": round(suggested, 2),
            "fair_low": round(min(low, suggested), 2),
            "fair_high": round(max(high, suggested), 2),
        }
