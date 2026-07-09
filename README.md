# FarmConnect

A website that connects African farmers directly with buyers — households,
restaurants, supermarkets and exporters — with **no middlemen**. Farmers get
**AI-assisted fair pricing**, both sides can **message each other**, and every
user can **leave star ratings** to build trust.

Built with Flask (web), SQLite (storage, no server needed), and scikit-learn
(the AI pricing model).

---

## What each file does

| File | Purpose |
|------|---------|
| `app.py` | The website: every page and action (login, market, listings, orders, messaging, ratings). |
| `db.py` | Creates the database tables and provides small helpers to read/write data. |
| `pricing_model.py` | The AI pricing model: learns from price data, predicts a fair price + range. |
| `recommender.py` | The "For you" AI: learns each user's buying rhythm and habits, then recommends listings with plain-language reasons. |
| `migrations/` | SQL for the Supabase tables behind orders and behaviour tracking. |
| `train_model.py` | Trains the model — on your CSV, or on generated sample data. |
| `templates/` | The HTML pages. `base.html` is the shared layout; the rest extend it. |
| `static/style.css` | All the styling (colors, fonts, layout, the price-tag design). |
| `data/` | Holds the database file and the trained model (created for you). |

---

## Run it in 4 steps

1. **Install the requirements** (ideally in a virtual environment):
   ```bash
   pip install -r requirements.txt
   ```

2. **Train the AI pricing model.** With no data of your own, this generates a
   realistic sample dataset and trains on it:
   ```bash
   python train_model.py
   ```

3. **Start the website:**
   ```bash
   python app.py
   ```

4. **Open** http://127.0.0.1:5000 in your browser. Register one account as a
   *farmer* and another (use a different email) as a *buyer* to try the full
   flow: list a crop → message → rate.

---

## Plugging in your OWN price data (for real accuracy)

The sample data is only illustrative. When you have real historical prices,
put them in a CSV with exactly these columns:

```
crop,region,month,quantity_kg,price_per_kg
Maize,Nairobi,8,500,0.44
Tomato,Lagos,1,50,1.05
...
```

Then retrain:
```bash
python train_model.py my_prices.csv
```

The website automatically uses the newly trained model. The crops and regions
it offers in the dropdowns come straight from your data.

---

## The "For you" AI (personal recommendations)

FarmConnect learns what each user actually does and uses it to keep the
market relevant to them:

- **Orders.** Buyers click **Request to buy** on any listing; the farmer
  confirms or declines from their dashboard. Confirming marks the listing
  sold, declines any other pending requests for it, and messages the buyer.
  Every order is a purchase record with a buyer and a timestamp.
- **Usage tracking.** For logged-in users the site also notes which listings
  they view and what they search for on the market page
  (the `activity_events` table).
- **The engine** (`recommender.py`) mines those records for patterns: which
  products you buy and browse, how often you restock each one, which day of
  the week and time of month you usually order, which farmers you already
  trust, what is close to you and what is genuinely below the local market
  price. It scores every active listing against your habits and fills the
  **"Recommended for you"** panel on the dashboard — each pick with an honest
  reason, e.g. *"You restock Maize about every 30 days — it's been 29."*
- **New users** see popular, nearby and freshly listed picks until the engine
  has real signals to learn from.

It is deliberately transparent (statistics, not a black box): every
recommendation can explain itself, and nothing is tracked for guests.

The two tables behind this live in Supabase; the SQL is in
`migrations/2026-07-09_add_orders_and_activity_events.sql` (already applied
to the team project).

---

## Before putting it online (production notes)

This runs great locally. Before a public launch you should:

- Change `app.secret_key` in `app.py` to a long random value.
- Turn off debug mode (`app.run(debug=False)`) and serve behind a real
  server such as gunicorn + nginx.
- Consider moving from SQLite to PostgreSQL if you expect many users.
- Add email verification and rate limiting on login.

These are deliberately left simple so the code stays easy to read and learn from.
