"""
apply_price_compare_layout_patch.py
--------------------------------------
Run this once from inside your `farmconnect` folder (after the
apply_price_compare_patch.py has already been applied):

    python3 apply_price_compare_layout_patch.py

It repositions the price comparison message so it sits beside the price
input (not underneath it) in a bigger, card-styled box.

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


print("Patching templates/new_listing.html ...")
patch(
    "templates/new_listing.html",
    old='''      <div class="field">
        <label for="price_per_kg">Your price per kg</label>
        <input id="price_per_kg" name="price_per_kg" type="number" min="0.01" step="0.01"
               value="{{ form.get('price_per_kg', '') }}" required>
        <div id="priceCompare" class="hint" style="display:none;margin-top:8px;"></div>
      </div>''',
    new='''      <div class="field">
        <label for="price_per_kg">Your price per kg</label>
        <div style="display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap;">
          <input id="price_per_kg" name="price_per_kg" type="number" min="0.01" step="0.01"
                 value="{{ form.get('price_per_kg', '') }}" required style="flex:1;min-width:140px;">
          <div id="priceCompare" class="card" style="display:none;flex:1;min-width:240px;
               font-size:1.1rem;line-height:1.4;padding:16px 18px;
               background:var(--paper-2);border-style:dashed;"></div>
        </div>
      </div>''',
    label="price comparison box moved beside input, enlarged",
)

print("\nDone. Restart the app to see the changes (no database reset needed).")
print("  python3 app.py")
