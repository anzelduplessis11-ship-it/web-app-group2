# 🌾 FarmConnect

> 🌍 No middlemen. Fair prices. Farmer-first. 🤝

A website that connects African farmers directly with buyers — households,
restaurants, supermarkets and exporters — with **no middlemen**. Farmers get
**AI-assisted fair pricing**, a **live market trends** dashboard, an **AI
farming expert** to ask questions in their own language, and every user can
**message each other** and **leave star ratings** to build trust.

Built with **Flask** (web), **SQLite** (storage, no server needed), and
**scikit-learn** (the AI pricing model). No external database or paid API
keys are required to run it. ✅

---

## ✨ Features

- 🛒 **Marketplace** — browse and filter crop/livestock listings by product,
  region and category; buyers see farmers closest to them first.
- 💰 **AI-assisted fair pricing** — a pricing model trained on data
  suggests a fair price range per crop, region, month and quantity.
- 📈 **Live market trends** — a dedicated Trends page shows the current price
  board, most-active products, and how a farmer's own prices compare to the
  regional market.
- 🤖 **AI Farm Expert (RAG assistant)** — an "Ask AI" chat assistant grounded
  in a 70+ article agronomy knowledge base (crops, pests, diseases, soil,
  irrigation, pricing, weather, storage, and more). Works with or without a
  local LLM (see [The AI Assistant](#-the-ai-assistant-ask-ai) below).
- 💬 **Direct messaging** — buyers and farmers negotiate price, quantity and
  pickup directly, with per-message translation.
- ⭐ **Star ratings** — both sides rate each other after a deal to build trust.
- 👨🏾‍🌾 **Farmer community board** — a shared board for farmers to post updates,
  tips and photos.
- 🌍 **20 regions across Africa**, each with the correct local currency,
  automatic currency conversion for buyers, and distance-to-farmer
  calculations (see [Regions & currencies](#-regions--currencies)).
- 🌐 **Multi-language translation** — pick a language on sign-up and the
  whole site (including messages, listing descriptions and community
  posts) follows you; see [Language & translation](#-language--translation)
  below.

---

## 🛠️ Tech stack

| Layer | Choice |
|---|---|
| 🐍 Backend | Flask (Python) |
| 🗄️ Database | SQLite (file-based, zero setup) |
| 🧠 AI pricing model | scikit-learn, trained by `train_model.py` |
| 🤖 AI assistant | Custom lightweight RAG (retrieval over local Markdown docs), optional [Ollama](https://ollama.com) for LLM-generated answers |
| 🌐 Translation | `deep-translator` (server-side) + a free client-side translation widget |
| 🎨 Frontend | Server-rendered Jinja2 templates, vanilla CSS/JS (no build step, no frameworks) |

---

## 🗂️ Project structure

| Path | Purpose |
|---|---|
| `app.py` | The website: every route (login, market, listings, messaging, ratings, trends, AI assistant). |
| `db.py` | Creates the database tables and provides small helpers to read/write data. |
| `pricing_model.py` | The AI pricing model: learns from price data, predicts a fair price + range. |
| `train_model.py` | Trains the pricing model — on your own CSV, or on generated sample data. |
| `trends.py` | Builds the data behind the Trends page (price board, most-active products, etc.). |
| `currency.py` | Region → country → currency mapping, plus live exchange-rate conversion. |
| `geo.py` | Approximate coordinates per region and distance calculation. |
| `rag/` | The AI assistant: `assistant.py` (answer logic), `retriever.py` (searches the knowledge base), `llm.py` (optional Ollama integration), `knowledge_base/` (the agronomy articles it's grounded in). |
| `translator/` | The floating translation widget (JS/CSS) and its server-side API blueprint (`translate_api.py`). |
| `static/js/ugc-translate.js` | Per-item "🌐 Translate" buttons for user-typed content (listing descriptions, community posts) — separate from the page-wide widget since this text isn't in English to begin with. |
| `templates/` | The HTML pages. `base.html` is the shared layout; the rest extend it. |
| `static/` | CSS, JS, and images. `static/style.css` is the core design system; `static/css/landing.css` is the landing-page-specific styling. |
| `data/` | Holds the database file, the trained model, and sample training data (created for you — not committed to git). |
| `apply_*_patch.py` (project root) | One-off migration scripts from earlier development (currency support, phone login, community photos, etc.). Their changes are already part of the current code — **you don't need to run these**; they're kept only as a historical record. |

---

## 🚀 Getting started

### 📋 Prerequisites

- **Python 3.10 or newer.** The code uses modern type-hint syntax
  (`dict | None`) that fails on Python 3.9 and earlier. Check your version:
  ```bash
  python3 --version
  ```
  If it's older than 3.10, either install a newer Python from
  [python.org](https://www.python.org/downloads/), or use
  [uv](https://docs.astral.sh/uv/) to get one without admin rights or
  touching your system Python at all:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh   # installs uv
  uv python install 3.12
  ```

### 1. Install the dependencies

```bash
pip install -r requirements.txt
```

If you created the venv with `uv` above, use `uv pip install` instead —
`uv venv` doesn't bundle `pip` itself:
```bash
uv pip install -r requirements.txt
```

### 3. Train the AI pricing model 🧠

With no data of your own, this generates a realistic sample dataset (based
on real coffee prices where available, clearly-labelled estimates
elsewhere — see [Data sources & credits](#-data-sources--credits)) and
trains on it:

```bash
python train_model.py
```

You'll see a summary of accuracy and which crops/regions the model knows.
This step is optional — the site still runs without it, just without AI
price suggestions — but it only takes a few seconds, so there's no reason
to skip it.

### 4. Run the website 🖥️

```bash
python app.py
```


### 5. Try the full flow

1. 📝 **Register two accounts** — one as a *farmer*, one as a *buyer* (use a
   different phone number for each). Sign-up is two steps: pick a language
   first, then fill in the account form — try picking something other than
   English to see the whole form translate itself.
2. 🌾 As the farmer: go to **Sell a crop**, post a listing (try the "Check the
   market price" button to see the AI pricing advisor in action).
3. 🛍️ As the buyer: go to **Market**, find the listing, open it, and click
   **Message this farmer** to start a conversation.
4. 📈 Check the **Trends** page to see the live price board for your region.
5. 🤖 Click **Ask AI** (bottom-left floating button, or the nav link) and ask
   a farming question, e.g. "What do I do about yellow maize leaves?"
6. ⭐ After a deal, leave each other a **star rating** from the listing or
   profile page.

---

## 🌍 Regions & currencies

FarmConnect covers 20 regions across North, West, East, Central and
Southern Africa, each with the correct local currency:

| Region | Country | Currency |
|---|---|---|
| Nairobi | Kenya | KES |
| Kano, Lagos | Nigeria | NGN |
| Kumasi | Ghana | GHS |
| Kampala | Uganda | UGX |
| Arusha | Tanzania | TZS |
| Addis Ababa | Ethiopia | ETB |
| Dakar | Senegal | XOF |
| Cairo | Egypt | EGP |
| Casablanca | Morocco | MAD |
| Tunis | Tunisia | TND |
| Johannesburg | South Africa | ZAR |
| Harare | Zimbabwe | ZWL |
| Lusaka | Zambia | ZMW |
| Kigali | Rwanda | RWF |
| Maputo | Mozambique | MZN |
| Kinshasa | DR Congo | CDF |
| Yaoundé | Cameroon | XAF |
| Luanda | Angola | AOA |
| Khartoum | Sudan | SDG |

💱 Buyers automatically see listing prices converted into their own region's
currency (live exchange rates, with a graceful fallback if the rate API is
unavailable).

---

## 📊 Plugging in your OWN price data (for real accuracy)

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

The website automatically uses the newly trained model. The crops and
regions it offers in the dropdowns come straight from your data. ✅

---

## 🤖 The AI Assistant ("Ask AI")

The assistant always works out of the box — it searches the local
agronomy knowledge base (`rag/knowledge_base/`) and returns grounded,
cited answers even with no internet connection and no LLM installed. 📚

If you want more natural, conversational answers, install
[Ollama](https://ollama.com) and pull a model:

```bash
ollama pull llama3.2
```

FarmConnect will automatically detect and use it (check `/api/kb-status`
for diagnostics). If Ollama isn't running, the assistant just falls back to
its knowledge-base-only mode — nothing breaks. 🛡️

---

## 🌐 Language & translation

FarmConnect is usable end-to-end in 20+ languages, not just English:

- 🗣️ **Sign-up asks for a language first** (step 1 of 2 on the Join page) and
  translates the rest of the form live, in that language, before the
  account even exists.
- 💾 **The choice follows the account**, not just the browser — it's saved to
  the database (`users.preferred_language`) and restored automatically
  next time that person logs in, on any device. Logging out drops back to
  English for the next (possibly different) person using that browser.
- 🌍 **The whole site translates**, via the floating language button (bottom
  right) — nav, buttons, page copy, everything with normal site text.
- ✍️ **User-typed content translates separately and on request** — a listing
  description, a community post, a chat message could be in any language,
  so blindly running them through the same page-wide translator (which
  assumes English) would produce nonsense. Each of these gets its own
  "🌐 Translate" button (`static/js/ugc-translate.js`) that detects the
  source language automatically.
- ⚡ Translations are cached (`translator/translation_cache.json`) and fetched
  in parallel (10 at a time) server-side, so only the *first* time a page is
  viewed in a given language is slow — everyone after that gets it instantly.



## 👥 Contributors

- 🧑‍💻 Anzel
- 🧑‍💻 Isaac
- 🧑‍💻 Siqhamo
- 🧑‍💻 Palesa
- 🧑‍💻 Ayabonga
- 🧑‍💻 Lynn

---

<p align="center">🌱 Built with care, for African farmers. 🌱</p>
