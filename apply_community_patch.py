"""
apply_community_patch.py
-------------------------
Run this once from inside your `farmconnect` folder:

    python3 apply_community_patch.py

It will:
  1. Add a `community_posts` table to db.py
  2. Add a `farmer_required` decorator and a `/community` route to app.py
  3. Add a "Community" nav link (farmers only) to templates/base.html
  4. Create templates/community.html

It edits files in place and prints what it changed. Safe to re-run —
it checks for existing markers and skips anything already applied.
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
# 1. db.py — add community_posts table
# ---------------------------------------------------------------------------
print("Patching db.py ...")
patch(
    "db.py",
    old='''            UNIQUE (rater_id, ratee_id, listing_id)
        );
        """
    )''',
    new='''            UNIQUE (rater_id, ratee_id, listing_id)
        );

        CREATE TABLE IF NOT EXISTS community_posts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id  INTEGER NOT NULL REFERENCES users(id),
            body       TEXT    NOT NULL,
            created_at TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        """
    )''',
    label="community_posts table",
)

# ---------------------------------------------------------------------------
# 2. app.py — farmer_required decorator + /community route
# ---------------------------------------------------------------------------
print("Patching app.py ...")
patch(
    "app.py",
    old='''        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# Auth: register, login, logout''',
    new='''        return view(*args, **kwargs)
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
# Auth: register, login, logout''',
    label="farmer_required decorator",
)

patch(
    "app.py",
    old='@app.route("/rate/<int:ratee_id>", methods=["POST"])',
    new='''@app.route("/community", methods=["GET", "POST"])
@farmer_required
def community():
    """A shared board where farmers post messages for other farmers to see."""
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        if not body:
            flash("Write something before posting.", "error")
        else:
            db.execute(
                "INSERT INTO community_posts (author_id, body) VALUES (?, ?)",
                (current_user()["id"], body),
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


@app.route("/rate/<int:ratee_id>", methods=["POST"])''',
    label="/community route",
)

# ---------------------------------------------------------------------------
# 3. templates/base.html — nav link for farmers
# ---------------------------------------------------------------------------
print("Patching templates/base.html ...")
patch(
    "templates/base.html",
    old='''            <a href="{{ url_for('new_listing') }}">Sell a crop</a>
          {% endif %}''',
    new='''            <a href="{{ url_for('new_listing') }}">Sell a crop</a>
            <a href="{{ url_for('community') }}">Community</a>
          {% endif %}''',
    label="Community nav link",
)

# ---------------------------------------------------------------------------
# 4. templates/community.html — new template
# ---------------------------------------------------------------------------
print("Creating templates/community.html ...")
community_html_path = ROOT / "templates" / "community.html"
if community_html_path.exists():
    print("  [skip] templates/community.html already exists")
else:
    community_html_path.write_text('''{% extends "base.html" %}
{% block title %}Community{% endblock %}
{% block content %}

<section class="section">
  <p class="eyebrow">Farmer community</p>
  <h1>Talk with other farmers</h1>
  <p class="muted">A shared board for farmers to share tips, ask questions,
  and help each other out. Only farmers can see and post here.</p>

  <form method="post" class="card" style="margin:18px 0;">
    <div class="field" style="margin:0;">
      <label for="body">Share something with other farmers</label>
      <textarea id="body" name="body" rows="3" required
        placeholder="e.g. Anyone else seeing good rain in Kano this week?"></textarea>
    </div>
    <div style="margin-top:14px;">
      <button class="btn btn-sm btn-green" type="submit">Post</button>
    </div>
  </form>

  {% if posts %}
    <div class="grid grid-1" style="gap:14px;">
      {% for p in posts %}
        <div class="card">
          <div class="meta">
            <strong>{{ p['author_name'] }}</strong>
            {% if p['author_region'] %} · {{ p['author_region'] }}{% endif %}
            · {{ p['created_at'] }}
          </div>
          <p style="margin-top:8px;">{{ p['body'] }}</p>
        </div>
      {% endfor %}
    </div>
  {% else %}
    <div class="card">
      <h3>No posts yet</h3>
      <p class="muted">Be the first farmer to post something here.</p>
    </div>
  {% endif %}
</section>

{% endblock %}
''')
    print("  [ok] templates/community.html created")

print("\\nDone. Restart your Flask app to see the changes.")
