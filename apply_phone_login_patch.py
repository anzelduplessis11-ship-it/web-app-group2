"""
apply_phone_login_patch.py
---------------------------
Run this once from inside your `farmconnect` folder:

    python3 apply_phone_login_patch.py

It will:
  1. Change the users table in db.py so `phone` is the required, unique
     identifier (email becomes optional and unused for login)
  2. Update /register and /login in app.py to use phone instead of email
  3. Update templates/register.html and templates/login.html to show a
     "Phone number" field instead of "Email"

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
# 1. db.py — phone becomes the required/unique identifier
# ---------------------------------------------------------------------------
print("Patching db.py ...")
patch(
    "db.py",
    old='''        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            role          TEXT    NOT NULL CHECK (role IN ('farmer', 'buyer')),
            region        TEXT    NOT NULL,
            phone         TEXT,
            created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        );''',
    new='''        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            phone         TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            role          TEXT    NOT NULL CHECK (role IN ('farmer', 'buyer')),
            region        TEXT    NOT NULL,
            email         TEXT,
            created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        );''',
    label="users table: phone is now required/unique",
)

# ---------------------------------------------------------------------------
# 2. app.py — register() and login() use phone instead of email
# ---------------------------------------------------------------------------
print("Patching app.py ...")
patch(
    "app.py",
    old='''    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "")
        region = request.form.get("region", "")
        phone = request.form.get("phone", "").strip()

        # Basic validation with friendly messages.
        if not all([name, email, password, role, region]):
            flash("Please fill in all required fields.", "error")
        elif role not in ("farmer", "buyer"):
            flash("Please choose whether you are a farmer or a buyer.", "error")
        elif len(password) < 6:
            flash("Choose a password with at least 6 characters.", "error")
        elif db.query_one("SELECT 1 FROM users WHERE email = ?", (email,)):
            flash("That email is already registered. Try logging in.", "error")
        else:
            uid = db.execute(
                "INSERT INTO users (name, email, password_hash, role, region, phone) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (name, email, generate_password_hash(password, method="pbkdf2:sha256"), role, region, phone),
            )
            session["user_id"] = uid
            flash(f"Welcome to FarmConnect, {name}!", "success")
            return redirect(url_for("dashboard"))

    return render_template("register.html", regions=REGIONS)''',
    new='''    if request.method == "POST":
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
                "VALUES (?, ?, ?, ?, ?)",
                (name, phone, generate_password_hash(password, method="pbkdf2:sha256"), role, region),
            )
            session["user_id"] = uid
            flash(f"Welcome to FarmConnect, {name}!", "success")
            return redirect(url_for("dashboard"))

    return render_template("register.html", regions=REGIONS)''',
    label="register() uses phone",
)

patch(
    "app.py",
    old='''    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db.query_one("SELECT * FROM users WHERE email = ?", (email,))
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['name']}!", "success")
            nxt = request.args.get("next")
            return redirect(nxt or url_for("dashboard"))
        flash("Email or password is incorrect.", "error")
    return render_template("login.html")''',
    new='''    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        user = db.query_one("SELECT * FROM users WHERE phone = ?", (phone,))
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['name']}!", "success")
            nxt = request.args.get("next")
            return redirect(nxt or url_for("dashboard"))
        flash("Phone number or password is incorrect.", "error")
    return render_template("login.html")''',
    label="login() uses phone",
)

# ---------------------------------------------------------------------------
# 3. templates/register.html — phone field replaces email field
# ---------------------------------------------------------------------------
print("Patching templates/register.html ...")
patch(
    "templates/register.html",
    old='''    <div class="field">
      <label for="email">Email</label>
      <input id="email" name="email" type="email" required>
    </div>
    <div class="row-2">
      <div class="field">
        <label for="region">Region</label>
        <select id="region" name="region" required>
          <option value="" disabled selected>Choose…</option>
          {% for r in regions %}<option value="{{ r }}">{{ r }}</option>{% endfor %}
        </select>
      </div>
      <div class="field">
        <label for="phone">Phone (optional)</label>
        <input id="phone" name="phone" type="tel">
      </div>
    </div>''',
    new='''    <div class="field">
      <label for="phone">Phone number</label>
      <input id="phone" name="phone" type="tel" required>
    </div>
    <div class="field">
      <label for="region">Region</label>
      <select id="region" name="region" required>
        <option value="" disabled selected>Choose…</option>
        {% for r in regions %}<option value="{{ r }}">{{ r }}</option>{% endfor %}
      </select>
    </div>''',
    label="register.html phone field",
)

# ---------------------------------------------------------------------------
# 4. templates/login.html — phone field replaces email field
# ---------------------------------------------------------------------------
print("Patching templates/login.html ...")
patch(
    "templates/login.html",
    old='''    <div class="field">
      <label for="email">Email</label>
      <input id="email" name="email" type="email" required>
    </div>''',
    new='''    <div class="field">
      <label for="phone">Phone number</label>
      <input id="phone" name="phone" type="tel" required>
    </div>''',
    label="login.html phone field",
)

print("\nDone. Delete data/farmconnect.db (schema changed) and restart the app.")
