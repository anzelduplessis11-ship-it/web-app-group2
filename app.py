"""
app.py
------
The FarmConnect website. Run it with:  python app.py
Then open http://127.0.0.1:5000 in your browser.

This file defines every page (called a "route"). Each route is a small
function that runs when someone visits a URL. Read them top to bottom:
they are grouped into Auth, Marketplace, Listings, Messaging, Ratings,
and Profiles.
"""
from __future__ import annotations


import os
import uuid
from functools import wraps
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, abort,
)
from werkzeug.security import generate_password_hash, check_password_hash

import db
import currency
import geo
import trends
from pricing_model import PricingModel
from translator.translate_api import translate_bp, to_english, from_english
from rag import answer as ai_answer, health as ai_health, get_kb

app = Flask(__name__)
app.register_blueprint(translate_bp)
# The secret key signs the login cookie. CHANGE THIS to a long random string
# before putting the site online.
app.secret_key = "change-me-to-a-long-random-secret"

# Load the trained AI pricing model once, when the server starts.
# If it hasn't been trained yet, the price tool is simply disabled.
PRICING = PricingModel.load()

# Regions the site offers. Kept in sync with the model where possible.
DEFAULT_REGIONS = [
    "Nairobi", "Kano", "Kumasi", "Kampala", "Arusha", "Lagos",
    "Addis Ababa", "Dakar", "Cairo", "Casablanca", "Tunis",
    "Johannesburg", "Harare", "Lusaka", "Kigali", "Maputo",
    "Kinshasa", "Yaounde", "Luanda", "Khartoum",
]
REGIONS = PRICING.known_regions if PRICING else DEFAULT_REGIONS
CROPS = PRICING.known_crops if PRICING else [
    "Maize", "Tomato", "Cassava", "Rice", "Beans", "Plantain",
]
LIVESTOCK = ["Chicken", "Goat", "Cattle", "Sheep", "Pig"]

# Close the database connection after every request.
app.teardown_appcontext(db.close_db)

# Where community-post photos get saved, and which file types we allow.
COMMUNITY_UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads", "community")
ALLOWED_PHOTO_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
os.makedirs(COMMUNITY_UPLOAD_FOLDER, exist_ok=True)


def allowed_photo(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_PHOTO_EXTENSIONS


# ---------------------------------------------------------------------------
# Helpers: who is logged in, and gates for protected pages
# ---------------------------------------------------------------------------
def current_user():
    """Return the logged-in user's row, or None."""
    uid = session.get("user_id")
    if uid is None:
        return None
    return db.query_one("SELECT * FROM users WHERE id = ?", (uid,))


@app.context_processor
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
    }


@app.context_processor
def inject_distance_helper():
    """Make distance_to(region) available in every template."""
    def distance_to(region):
        viewer = current_user()
        if viewer is None:
            return None
        return geo.distance_between_regions(viewer["region"], region)
    return {"distance_to": distance_to}


def login_required(view):
    """Decorator: bounce guests to the login page."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Please log in first.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def farmer_required(view):
    """Decorator: only logged-in farmers may access this page."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            flash("Please log in first.", "error")
            return redirect(url_for("login", next=request.path))
        if user["role"] != "farmer":
            flash("The community board is for farmers only.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# Auth: register, login, logout
# ---------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "")
        region = request.form.get("region", "")

        # Basic validation with friendly messages.
        if not all([name, phone, password, role, region]):
            flash("Please fill in all required fields.", "error")
        elif role not in ("farmer", "buyer"):
            flash("Please choose whether you are a farmer or a buyer.", "error")
        elif len(password) < 6:
            flash("Choose a password with at least 6 characters.", "error")
        elif db.query_one("SELECT 1 FROM users WHERE phone = ?", (phone,)):
            flash("That phone number is already registered. Try logging in.", "error")
        else:
            uid = db.execute(
                "INSERT INTO users (name, phone, password_hash, role, region) "
                "VALUES (?, ?, ?, ?, ?) RETURNING id",
                (name, phone, generate_password_hash(password, method="pbkdf2:sha256"), role, region),
            )
            session["user_id"] = uid
            flash(f"Welcome to FarmConnect, {name}!", "success")
            return redirect(url_for("dashboard"))

    preselect_role = request.args.get("role")
    if preselect_role not in ("farmer", "buyer"):
        preselect_role = None
    return render_template("register.html", regions=REGIONS, preselect_role=preselect_role)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        user = db.query_one("SELECT * FROM users WHERE phone = ?", (phone,))
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['name']}!", "success")
            nxt = request.args.get("next")
            return redirect(nxt or url_for("dashboard"))
        flash("Phone number or password is incorrect.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Marketplace: home page and browsing listings
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """The public cover page. Logged-in users skip it and go to their home."""
    if current_user() is not None:
        return redirect(url_for("dashboard"))

    # Live headline numbers for the cover page, from real data.
    stats = {
        "farmers": db.query_one(
            "SELECT COUNT(*) AS n FROM users WHERE role = 'farmer'")["n"],
        "listings": db.query_one(
            "SELECT COUNT(*) AS n FROM listings WHERE status = 'active'")["n"],
        "sold": db.query_one(
            "SELECT COUNT(*) AS n FROM listings WHERE status = 'sold'")["n"],
        "regions": db.query_one(
            "SELECT COUNT(DISTINCT region) AS n FROM users")["n"],
    }
    return render_template("index.html", stats=stats)


@app.route("/market")
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

    # If someone is logged in, recommend the closest farmers first.
    viewer = current_user()
    if viewer is not None:
        def distance_or_far(l):
            d = geo.distance_between_regions(viewer["region"], l["region"])
            return d if d is not None else float("inf")
        listings = sorted(listings, key=distance_or_far)

    return render_template(
        "market.html", listings=listings, crops=CROPS, livestock=LIVESTOCK, regions=REGIONS,
        sel_crop=crop, sel_region=region, sel_category=category,
    )


# ---------------------------------------------------------------------------
# Listings: create, view detail, mark sold
# ---------------------------------------------------------------------------
@app.route("/listings/new", methods=["GET", "POST"])
@login_required
def new_listing():
    me = current_user()
    if me["role"] != "farmer":
        flash("Only farmers can post crops for sale.", "error")
        return redirect(url_for("market"))

    if request.method == "POST":
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
            "price_per_kg, description) VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id",
            (me["id"], crop, category, region, quantity, price, description),
        )
        flash("Your listing is now live on the market.", "success")
        return redirect(url_for("listing_detail", listing_id=lid))

    return render_template(
        "new_listing.html", crops=CROPS, livestock=LIVESTOCK, regions=REGIONS,
        pricing_available=PRICING is not None, form={},
    )


@app.route("/listing/<int:listing_id>")
def listing_detail(listing_id):
    listing = db.query_one(
        "SELECT l.*, u.name AS farmer_name, u.id AS farmer_uid, "
        "u.phone AS farmer_phone FROM listings l "
        "JOIN users u ON u.id = l.farmer_id WHERE l.id = ?",
        (listing_id,),
    )
    if listing is None:
        abort(404)

    farmer_rating = db.average_rating(listing["farmer_id"])

    # If the AI model knows this crop/region, show a fair-price comparison.
    price_context = None
    if PRICING and listing["category"] == "crop" and listing["crop"] in PRICING.known_crops \
            and listing["region"] in PRICING.known_regions:
        price_context = PRICING.suggest(
            listing["crop"], listing["region"],
            datetime.now().month, listing["quantity_kg"],
        )

    # Real prices other farmers are currently asking for the same product.
    market_context = db.market_price_stats(
        listing["crop"], listing["category"], listing["region"],
    )

    # A fair opening-offer range for whoever is considering buying this.
    buyer_offer = _build_buyer_offer_range(price_context, market_context)

    return render_template(
        "listing_detail.html", listing=listing,
        farmer_rating=farmer_rating, price_context=price_context,
        market_context=market_context, buyer_offer=buyer_offer,
    )


@app.route("/listing/<int:listing_id>/sold", methods=["POST"])
@login_required
def mark_sold(listing_id):
    me = current_user()
    listing = db.query_one("SELECT * FROM listings WHERE id = ?", (listing_id,))
    if listing is None:
        abort(404)
    if listing["farmer_id"] != me["id"]:
        abort(403)
    db.execute("UPDATE listings SET status = 'sold' WHERE id = ?", (listing_id,))
    flash("Marked as sold. Well done!", "success")
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# The AI price tool: a small JSON endpoint the "new listing" page calls
# ---------------------------------------------------------------------------
def _build_price_advice(model: dict | None, market: dict | None, category: str) -> str:
    """Turn the AI estimate and/or real live listings into one plain-language tip."""
    plural = lambda n: "listing" if n == 1 else "listings"
    freshness = ""
    if market and market.get("newest_age_days", 0) > 7:
        freshness = f" (the most recent one was posted {int(market['newest_age_days'])} days ago)"

    if market and model:
        recommended = round((model["suggested"] + market["avg"]) / 2, 2)
        return (
            f"{market['count']} other {plural(market['count'])} in your region are "
            f"currently asking between {market['min']:.2f} and {market['max']:.2f} per kg "
            f"(recency-weighted average {market['avg']:.2f}){freshness}. Our AI model, based "
            f"on historical trends, estimates a fair price of {model['suggested']:.2f} per kg "
            f"(range {model['fair_low']:.2f}-{model['fair_high']:.2f}). "
            f"A competitive price would be around {recommended:.2f} per kg."
        )
    if market:
        return (
            f"{market['count']} other {plural(market['count'])} in your region are "
            f"currently asking between {market['min']:.2f} and {market['max']:.2f} per kg "
            f"(recency-weighted average {market['avg']:.2f}){freshness}. Price near that range "
            f"to stay competitive."
        )
    if model:
        return (
            f"Nobody else has listed this {category} in your region yet, so there's no "
            f"live price to compare against. Based on historical trends, a fair price is "
            f"around {model['suggested']:.2f} per kg "
            f"(range {model['fair_low']:.2f}-{model['fair_high']:.2f})."
        )
    return "No pricing data is available yet for this product in your region."


def _build_buyer_offer_range(model: dict | None, market: dict | None) -> dict | None:
    """A fair opening-offer range for the BUYER's side of the negotiation.

    Grounded in the same two signals as the farmer-facing advice (live local
    listings + the AI historical estimate) rather than an arbitrary percentage,
    so it stays consistent with whatever the farmer was told is a fair price.
    Blending both keeps the low end from being an exploitative lowball and the
    high end from being an overpay - a floor and ceiling both sides can trust.
    """
    if market and model:
        low = round((market["min"] + model["fair_low"]) / 2, 2)
        high = round((market["max"] + model["fair_high"]) / 2, 2)
    elif market:
        low, high = market["min"], market["max"]
    elif model:
        low, high = model["fair_low"], model["fair_high"]
    else:
        return None
    return {"low": low, "high": high}


def _trend_svg(trend: dict | None, width: int = 600, height: int = 160, pad: int = 12) -> dict | None:
    """Turn a trends.py price-trend series into SVG polyline/dot coordinates.

    Pure presentation math (no data invented) — kept out of the template
    because Jinja arithmetic for a scaled polyline is unreadable.
    """
    if not trend or len(trend["points"]) < 2:
        return None
    lo, hi = trend["min"], trend["max"]
    span = (hi - lo) or 1.0
    n = len(trend["points"])
    step = (width - 2 * pad) / (n - 1)

    def _xy(i, price):
        x = pad + i * step
        y = height - pad - ((price - lo) / span) * (height - 2 * pad)
        return round(x, 1), round(y, 1)

    dots = []
    coords = []
    for i, p in enumerate(trend["points"]):
        x, y = _xy(i, p["price"])
        coords.append(f"{x},{y}")
        dots.append({"x": x, "y": y, "week": p["week"], "price": p["price"]})
    return {"points": " ".join(coords), "dots": dots, "width": width, "height": height}


def _planting_note_for(crop: str) -> str | None:
    """Best-effort one-line planting-calendar context for an outlook product.

    Grounded strictly in the knowledge base (planting_calendars/crops docs) —
    returns None rather than guessing if nothing relevant is indexed, so the
    Trends page never states an agronomic fact that isn't backed by the KB.
    """
    try:
        hits, _, meta = get_kb().search_grouped(f"{crop} planting season calendar", k=6, max_docs=3)
    except Exception:
        return None
    if meta.get("confidence", 0.0) < 0.32:
        return None
    for h in hits:
        if h.category == "planting_calendars":
            return h.snippet(220)
    return None


@app.route("/api/suggest-price", methods=["POST"])
@login_required
def api_suggest_price():
    """Return the AI historical estimate plus real, current market prices."""
    data = request.get_json(silent=True) or {}
    try:
        product = str(data["crop"])
        region = str(data["region"])
        quantity = float(data["quantity_kg"])
        category = str(data.get("category", "crop"))
        month = datetime.now().month
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Please choose a crop, region, and quantity."}), 400

    model = None
    if PRICING and category == "crop" \
            and product in PRICING.known_crops and region in PRICING.known_regions:
        model = PRICING.suggest(product, region, month, quantity)

    market = db.market_price_stats(product, category, region)

    if model is None and market is None:
        return jsonify({
            "error": "No AI estimate and no other listings for that product/region yet.",
        }), 400

    return jsonify({
        "model": model,
        "market": market,
        "advice": _build_price_advice(model, market, category),
        "buyer_offer": _build_buyer_offer_range(model, market),
    })


# ---------------------------------------------------------------------------
# Dashboard: role-aware home for a logged-in user
# ---------------------------------------------------------------------------
@app.route("/dashboard")
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
    )


# ---------------------------------------------------------------------------
# Messaging: inbox + one-to-one conversation threads
# ---------------------------------------------------------------------------
@app.route("/messages")
@login_required
def inbox():
    me = current_user()
    # Get the most recent message with each other person (a conversation list).
    conversations = db.query_all(
        """
        SELECT
            other.id   AS other_id,
            other.name AS other_name,
            other.role AS other_role,
            MAX(m.created_at) AS last_time,
            SUM(CASE WHEN m.recipient_id = ? AND m.is_read = 0 THEN 1 ELSE 0 END)
                AS unread
        FROM messages m
        JOIN users other
          ON other.id = CASE WHEN m.sender_id = ? THEN m.recipient_id
                             ELSE m.sender_id END
        WHERE m.sender_id = ? OR m.recipient_id = ?
        GROUP BY other.id
        ORDER BY last_time DESC
        """,
        (me["id"], me["id"], me["id"], me["id"]),
    )
    return render_template("inbox.html", conversations=conversations)


@app.route("/messages/<int:other_id>", methods=["GET", "POST"])
@login_required
def conversation(other_id):
    me = current_user()
    other = db.query_one("SELECT * FROM users WHERE id = ?", (other_id,))
    if other is None or other_id == me["id"]:
        abort(404)

    if request.method == "POST":
        body = request.form.get("body", "").strip()
        listing_id = request.form.get("listing_id") or None
        if body:
            db.execute(
                "INSERT INTO messages (sender_id, recipient_id, listing_id, body) "
                "VALUES (?, ?, ?, ?)",
                (me["id"], other_id, listing_id, body),
            )
        return redirect(url_for("conversation", other_id=other_id))

    # Mark their messages to me as read now that I'm viewing them.
    db.execute(
        "UPDATE messages SET is_read = 1 WHERE sender_id = ? AND recipient_id = ?",
        (other_id, me["id"]),
    )

    thread = db.query_all(
        "SELECT * FROM messages WHERE (sender_id = ? AND recipient_id = ?) "
        "OR (sender_id = ? AND recipient_id = ?) ORDER BY created_at ASC",
        (me["id"], other_id, other_id, me["id"]),
    )
    # Optional listing context if arriving from a listing page.
    listing_id = request.args.get("listing_id", "")
    return render_template(
        "conversation.html", other=other, thread=thread, listing_id=listing_id,
    )


# ---------------------------------------------------------------------------
# Ratings: leave a star rating on another user
# ---------------------------------------------------------------------------
@app.route("/community", methods=["GET", "POST"])
@farmer_required
def community():
    """A shared board where farmers post messages (and optional photos)
    for other farmers to see."""
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        photo_filename = None

        photo = request.files.get("photo")
        if photo and photo.filename:
            if allowed_photo(photo.filename):
                ext = photo.filename.rsplit(".", 1)[1].lower()
                photo_filename = f"{uuid.uuid4().hex}.{ext}"
                photo.save(os.path.join(COMMUNITY_UPLOAD_FOLDER, photo_filename))
            else:
                flash("Photo must be a PNG, JPG, GIF, or WEBP file.", "error")
                return redirect(url_for("community"))

        if not body and not photo_filename:
            flash("Write something or add a photo before posting.", "error")
        else:
            db.execute(
                "INSERT INTO community_posts (author_id, body, photo_path) VALUES (?, ?, ?)",
                (current_user()["id"], body, photo_filename),
            )
            flash("Posted to the community board.", "success")
        return redirect(url_for("community"))

    posts = db.query_all(
        "SELECT community_posts.*, users.name AS author_name, "
        "users.region AS author_region "
        "FROM community_posts "
        "JOIN users ON users.id = community_posts.author_id "
        "ORDER BY community_posts.created_at DESC"
    )
    return render_template("community.html", posts=posts)


@app.route("/rate/<int:ratee_id>", methods=["POST"])
@login_required
def rate(ratee_id):
    me = current_user()
    if ratee_id == me["id"]:
        flash("You cannot rate yourself.", "error")
        return redirect(request.referrer or url_for("index"))

    try:
        stars = int(request.form.get("stars", ""))
        assert 1 <= stars <= 5
    except (ValueError, AssertionError):
        flash("Please pick between 1 and 5 stars.", "error")
        return redirect(request.referrer or url_for("index"))

    comment = request.form.get("comment", "").strip()
    listing_id = request.form.get("listing_id") or None

    # Upsert: let someone update a rating they already left (same rater+ratee+listing).
    db.execute(
        "INSERT INTO ratings (rater_id, ratee_id, listing_id, stars, comment) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT (rater_id, ratee_id, listing_id) DO UPDATE "
        "SET stars = EXCLUDED.stars, comment = EXCLUDED.comment",
        (me["id"], ratee_id, listing_id, stars, comment),
    )
    flash("Thank you — your rating has been saved.", "success")
    return redirect(url_for("profile", user_id=ratee_id))


# ---------------------------------------------------------------------------
# Profiles: public page for any user, with listings and ratings
# ---------------------------------------------------------------------------
@app.route("/user/<int:user_id>")
def profile(user_id):
    person = db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if person is None:
        abort(404)

    rating = db.average_rating(user_id)
    reviews = db.query_all(
        "SELECT r.*, u.name AS rater_name FROM ratings r "
        "JOIN users u ON u.id = r.rater_id WHERE r.ratee_id = ? "
        "ORDER BY r.created_at DESC",
        (user_id,),
    )
    active_listings = db.query_all(
        "SELECT * FROM listings WHERE farmer_id = ? AND status = 'active' "
        "ORDER BY created_at DESC",
        (user_id,),
    )
    return render_template(
        "profile.html", person=person, rating=rating,
        reviews=reviews, active_listings=active_listings,
    )


# ---------------------------------------------------------------------------
# Trends: a market-overview page built from real listings in a region
# ---------------------------------------------------------------------------
@app.route("/trends")
@login_required
def market_trends():
    me = current_user()
    # Default to the viewer's own region so prices stay in one currency
    # (listings store prices unconverted, in the lister's local currency).
    region = request.args.get("region", "") or me["region"]
    data = trends.region_overview(region, me["id"] if me["role"] == "farmer" else None)
    for o in data["outlook"][:3]:
        o["planting_note"] = _planting_note_for(o["crop"]) if o["category"] == "crop" else None
    trend_svg = _trend_svg(data["trend"])
    code, symbol = currency.currency_for_region(region)
    return render_template(
        "trends.html", data=data, region=region, regions=REGIONS, trend_svg=trend_svg,
        currency_symbol=symbol or code or "", currency_code=code or "",
    )


# ---------------------------------------------------------------------------
# AI assistant: "Ask the Farm Expert" (RAG over the agronomy knowledge base)
# ---------------------------------------------------------------------------
@app.route("/assistant")
@login_required
def assistant():
    """The RAG assistant page — answers grounded in the knowledge base."""
    return render_template("assistant.html")


@app.route("/api/ask", methods=["POST"])
@login_required
def api_ask():
    """Answer a farming question, translating seamlessly in the background.

    Flow: farmer's language -> English -> AI (grounded in the knowledge base,
    using a local model if one is running) -> back to the farmer's language.
    """
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    lang = (data.get("lang") or "en").strip() or "en"
    if not question:
        return jsonify({"ok": False, "error": "empty"}), 400

    # 1. Translate the farmer's question into English (auto-detect source).
    question_en = to_english(question) if lang != "en" else question

    # 2. The assistant reasons and answers in English, grounded in the KB.
    me = current_user()
    region = me["region"] if me else None
    result = ai_answer(question_en, region=region)
    answer_en = result["answer"]

    # 3. Translate the answer back into the farmer's language.
    answer_out = from_english(answer_en, lang) if lang != "en" else answer_en

    return jsonify({
        "ok": True,
        "lang": lang,
        "question_en": question_en,
        "answer": answer_out,
        "answer_en": answer_en,
        "sources": result["sources"],
        "mode": result["mode"],
        "used_llm": result["used_llm"],
        "backend": result.get("backend"),
        "confidence": result.get("confidence"),
        "confidence_band": result.get("confidence_band"),
    })


@app.route("/api/kb-status")
def api_kb_status():
    """Diagnostics: knowledge-base size + whether a local model is available."""
    return jsonify(ai_health())


# ---------------------------------------------------------------------------
# Start the server (development mode)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    db.init_db()  # create tables on first run
    print("FarmConnect running at http://127.0.0.1:5050")
    # threaded=True so a slow AI answer (the local model can take a while) never
    # blocks the rest of the site for other requests.
    app.run(debug=True, port=5050, threaded=True)
