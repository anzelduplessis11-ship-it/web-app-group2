"""
apply_price_compare_patch.py
------------------------------
Run this once from inside your `farmconnect` folder:

    python3 apply_price_compare_patch.py

It updates templates/new_listing.html only (no db.py or app.py changes
needed) so that:
  - The fair-price suggestion is fetched automatically once crop/livestock,
    region, and quantity are all filled in (not just on button click)
  - As the farmer types their own price, a neutral message appears showing
    whether it's above, below, or about the same as the current market
    average — no button click required

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

# ---------------------------------------------------------------------------
# 1. Add a spot under the price field for the neutral comparison message
# ---------------------------------------------------------------------------
patch(
    "templates/new_listing.html",
    old='''      <div class="field">
        <label for="price_per_kg">Your price per kg</label>
        <input id="price_per_kg" name="price_per_kg" type="number" min="0.01" step="0.01"
               value="{{ form.get('price_per_kg', '') }}" required>
      </div>''',
    new='''      <div class="field">
        <label for="price_per_kg">Your price per kg</label>
        <input id="price_per_kg" name="price_per_kg" type="number" min="0.01" step="0.01"
               value="{{ form.get('price_per_kg', '') }}" required>
        <div id="priceCompare" class="hint" style="display:none;margin-top:8px;"></div>
      </div>''',
    label="price comparison message slot",
)

# ---------------------------------------------------------------------------
# 2. Replace the pricing script: auto-fetch + live comparison
# ---------------------------------------------------------------------------
patch(
    "templates/new_listing.html",
    old='''{% if pricing_available %}
<script>
// When the farmer clicks "Suggest a fair price", ask the server (which asks
// the AI model) and show the result as a price tag they can accept.
const btn = document.getElementById('suggestBtn');
const box = document.getElementById('suggestBox');

btn.addEventListener('click', async () => {
  const crop = document.getElementById('crop').value;
  const region = document.getElementById('region').value;
  const quantity = document.getElementById('quantity_kg').value;

  if (!crop || !region || !quantity) {
    box.innerHTML = '<p class="flash error">Choose a crop, region and quantity first.</p>';
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Thinking…';
  try {
    const res = await fetch('{{ url_for("api_suggest_price") }}', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ crop, region, quantity_kg: quantity }),
    });
    const data = await res.json();
    if (!res.ok) {
      box.innerHTML = '<p class="flash error">' + (data.error || 'Could not get a price.') + '</p>';
    } else {
      box.innerHTML =
        '<span class="tag"><span class="amount">' + data.suggested.toFixed(2) +
        '</span><span class="unit">suggested per kg</span></span>' +
        '<div class="tag-range">Fair range: ' + data.fair_low.toFixed(2) +
        ' – ' + data.fair_high.toFixed(2) + ' per kg</div>' +
        '<div style="margin-top:10px;"><button type="button" class="btn btn-sm btn-green" id="usePrice">Use ' +
        data.suggested.toFixed(2) + '</button></div>';
      document.getElementById('usePrice').addEventListener('click', () => {
        document.getElementById('price_per_kg').value = data.suggested.toFixed(2);
      });
    }
  } catch (e) {
    box.innerHTML = '<p class="flash error">Something went wrong. Please try again.</p>';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Suggest a fair price';
  }
});
</script>
{% endif %}''',
    new='''{% if pricing_available %}
<script>
// Ask the server for a suggested fair price, store the result, and show it.
// Runs when the farmer clicks the button, AND automatically whenever
// crop/livestock, region, and quantity are all filled in.
const btn = document.getElementById('suggestBtn');
const box = document.getElementById('suggestBox');
const priceInput = document.getElementById('price_per_kg');
const compareBox = document.getElementById('priceCompare');
let lastSuggestion = null;

function currentProduct() {
  const isLivestock = document.getElementById('cat-livestock').checked;
  return isLivestock
    ? document.getElementById('livestock').value
    : document.getElementById('crop').value;
}

async function fetchSuggestion(showLoading) {
  const crop = currentProduct();
  const region = document.getElementById('region').value;
  const quantity = document.getElementById('quantity_kg').value;

  if (!crop || !region || !quantity) {
    if (showLoading) {
      box.innerHTML = '<p class="flash error">Choose a crop, region and quantity first.</p>';
    }
    return;
  }

  if (showLoading) {
    btn.disabled = true;
    btn.textContent = 'Thinking…';
  }
  try {
    const res = await fetch('{{ url_for("api_suggest_price") }}', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ crop, region, quantity_kg: quantity }),
    });
    const data = await res.json();
    if (!res.ok) {
      lastSuggestion = null;
      compareBox.style.display = 'none';
      if (showLoading) {
        box.innerHTML = '<p class="flash error">' + (data.error || 'Could not get a price.') + '</p>';
      }
    } else {
      lastSuggestion = data;
      box.innerHTML =
        '<span class="tag"><span class="amount">' + data.suggested.toFixed(2) +
        '</span><span class="unit">suggested per kg</span></span>' +
        '<div class="tag-range">Fair range: ' + data.fair_low.toFixed(2) +
        ' – ' + data.fair_high.toFixed(2) + ' per kg</div>' +
        '<div style="margin-top:10px;"><button type="button" class="btn btn-sm btn-green" id="usePrice">Use ' +
        data.suggested.toFixed(2) + '</button></div>';
      document.getElementById('usePrice').addEventListener('click', () => {
        priceInput.value = data.suggested.toFixed(2);
        priceInput.dispatchEvent(new Event('input'));
      });
      updatePriceCompare();
    }
  } catch (e) {
    if (showLoading) {
      box.innerHTML = '<p class="flash error">Something went wrong. Please try again.</p>';
    }
  } finally {
    if (showLoading) {
      btn.disabled = false;
      btn.textContent = 'Suggest a fair price';
    }
  }
}

// Shows a neutral (not red/green, not alarming) message comparing the
// farmer's own typed price to the current market average.
function updatePriceCompare() {
  const price = parseFloat(priceInput.value);
  if (!lastSuggestion || !price || price <= 0) {
    compareBox.style.display = 'none';
    return;
  }
  const suggested = lastSuggestion.suggested;
  const diffPct = ((price - suggested) / suggested) * 100;
  let message;
  if (Math.abs(diffPct) < 3) {
    message = 'Your price is right around the current market average (' +
      suggested.toFixed(2) + ' per kg).';
  } else if (diffPct > 0) {
    message = 'Your price is about ' + diffPct.toFixed(0) +
      '% above the current market average (' + suggested.toFixed(2) + ' per kg).';
  } else {
    message = 'Your price is about ' + Math.abs(diffPct).toFixed(0) +
      '% below the current market average (' + suggested.toFixed(2) + ' per kg).';
  }
  compareBox.textContent = message;
  compareBox.style.display = '';
}

btn.addEventListener('click', () => fetchSuggestion(true));
priceInput.addEventListener('input', updatePriceCompare);

['crop', 'livestock', 'region', 'quantity_kg'].forEach(function (id) {
  document.getElementById(id).addEventListener('change', function () {
    fetchSuggestion(false);
  });
});
</script>
{% endif %}''',
    label="auto-fetch + live neutral price comparison script",
)

print("\nDone. Restart the app to see the changes (no database reset needed this time).")
print("  python3 app.py")
