"""
apply_community_photos_patch.py
---------------------------------
Run this once from inside your `farmconnect` folder (after the community
board patch has already been applied):

    python3 apply_community_photos_patch.py

It will:
  1. Add a photo_path column to the community_posts table in db.py
  2. Add os/uuid imports, an upload folder, and a filetype checker to app.py
  3. Update the /community route to accept and save an uploaded photo
  4. Update templates/community.html to show a file input and display
     uploaded photos in the feed

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
# 1. db.py — photo_path column on community_posts
# ---------------------------------------------------------------------------
print("Patching db.py ...")
patch(
    "db.py",
    old='''        CREATE TABLE IF NOT EXISTS community_posts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id  INTEGER NOT NULL REFERENCES users(id),
            body       TEXT    NOT NULL,
            created_at TEXT    NOT NULL DEFAULT (datetime('now'))
        );''',
    new='''        CREATE TABLE IF NOT EXISTS community_posts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id  INTEGER NOT NULL REFERENCES users(id),
            body       TEXT    NOT NULL,
            photo_path TEXT,
            created_at TEXT    NOT NULL DEFAULT (datetime('now'))
        );''',
    label="community_posts table: photo_path column",
)

# ---------------------------------------------------------------------------
# 2. app.py — imports + upload folder + filetype checker
# ---------------------------------------------------------------------------
print("Patching app.py ...")
patch(
    "app.py",
    old='''from functools import wraps
from datetime import datetime''',
    new='''import os
import uuid
from functools import wraps
from datetime import datetime''',
    label="os/uuid imports",
)

patch(
    "app.py",
    old='''# Close the database connection after every request.
app.teardown_appcontext(db.close_db)''',
    new='''# Close the database connection after every request.
app.teardown_appcontext(db.close_db)

# Where community-post photos get saved, and which file types we allow.
COMMUNITY_UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads", "community")
ALLOWED_PHOTO_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
os.makedirs(COMMUNITY_UPLOAD_FOLDER, exist_ok=True)


def allowed_photo(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_PHOTO_EXTENSIONS''',
    label="upload folder + allowed_photo() helper",
)

# ---------------------------------------------------------------------------
# 3. app.py — /community route handles photo upload
# ---------------------------------------------------------------------------
patch(
    "app.py",
    old='''@app.route("/community", methods=["GET", "POST"])
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
    return render_template("community.html", posts=posts)''',
    new='''@app.route("/community", methods=["GET", "POST"])
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
    return render_template("community.html", posts=posts)''',
    label="/community route handles photo upload",
)

# ---------------------------------------------------------------------------
# 4. templates/community.html — file input + photo display
# ---------------------------------------------------------------------------
print("Patching templates/community.html ...")
patch(
    "templates/community.html",
    old='''  <form method="post" class="card" style="margin:18px 0;">
    <div class="field" style="margin:0;">
      <label for="body">Share something with other farmers</label>
      <textarea id="body" name="body" rows="3" required
        placeholder="e.g. Anyone else seeing good rain in Kano this week?"></textarea>
    </div>
    <div style="margin-top:14px;">
      <button class="btn btn-sm btn-green" type="submit">Post</button>
    </div>
  </form>''',
    new='''  <form method="post" enctype="multipart/form-data" class="card" style="margin:18px 0;">
    <div class="field" style="margin:0;">
      <label for="body">Share something with other farmers</label>
      <textarea id="body" name="body" rows="3"
        placeholder="e.g. Anyone else seeing good rain in Kano this week?"></textarea>
    </div>
    <div class="field">
      <label for="photo">Add a photo (optional)</label>
      <input id="photo" name="photo" type="file"
        accept="image/png,image/jpeg,image/gif,image/webp">
    </div>
    <div style="margin-top:14px;">
      <button class="btn btn-sm btn-green" type="submit">Post</button>
    </div>
  </form>''',
    label="community.html photo upload field",
)

patch(
    "templates/community.html",
    old='''      {% for p in posts %}
        <div class="card">
          <div class="meta">
            <strong>{{ p['author_name'] }}</strong>
            {% if p['author_region'] %} · {{ p['author_region'] }}{% endif %}
            · {{ p['created_at'] }}
          </div>
          <p style="margin-top:8px;">{{ p['body'] }}</p>
        </div>
      {% endfor %}''',
    new='''      {% for p in posts %}
        <div class="card">
          <div class="meta">
            <strong>{{ p['author_name'] }}</strong>
            {% if p['author_region'] %} · {{ p['author_region'] }}{% endif %}
            · {{ p['created_at'] }}
          </div>
          {% if p['body'] %}<p style="margin-top:8px;">{{ p['body'] }}</p>{% endif %}
          {% if p['photo_path'] %}
            <img src="{{ url_for('static', filename='uploads/community/' + p['photo_path']) }}"
                 alt="Photo from {{ p['author_name'] }}"
                 style="margin-top:10px;max-width:100%;border-radius:10px;">
          {% endif %}
        </div>
      {% endfor %}''',
    label="community.html photo display in feed",
)

print("\nDone. Reset the database (schema changed) and restart the app:")
print("  rm data/farmconnect.db")
print("  python3 app.py")
