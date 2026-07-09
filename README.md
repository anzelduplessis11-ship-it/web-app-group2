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
| `app.py` | The website: every page and action (login, market, listings, messaging, ratings). |
| `db.py` | Creates the database tables and provides small helpers to read/write data. |
| `pricing_model.py` | The AI pricing model: learns from price data, predicts a fair price + range. |
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

## Before putting it online (production notes)

This runs great locally. Before a public launch you should:

- Change `app.secret_key` in `app.py` to a long random value.
- Turn off debug mode (`app.run(debug=False)`) and serve behind a real
  server such as gunicorn + nginx.
- Consider moving from SQLite to PostgreSQL if you expect many users.
- Add email verification and rate limiting on login.

These are deliberately left simple so the code stays easy to read and learn from.
