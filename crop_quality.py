"""
crop_quality.py
----------------
Photo upload + AI quality inspection for marketplace listings.

When a farmer attaches a photo to a listing, we:

  1. Downscale it (max 1280px, JPEG) — faster uploads, smaller AI payloads,
     and less storage.
  2. Ask a free vision model (Llama 4 Scout via the farmer's existing
     Hugging Face + Groq setup) two things:
       - does the photo actually show the declared crop? (gatekeeper)
       - how good does it look, 0-10? (freshness, ripeness, uniformity,
         damage) plus a one-line note for buyers.
  3. Store the photo in Supabase Storage (bucket "listing-photos"), which
     survives redeploys — unlike the web server's own disk on Render.

Everything degrades gracefully: if the AI is unreachable the photo is still
accepted (score stays empty and buyers see "not yet rated"); if storage is
unreachable the caller gets a clear error to show the farmer.
"""
from __future__ import annotations

import base64
import io
import json
import re
import uuid

import config
import supa

# Vision model used for the quality check. Must support images on the
# configured HF_PROVIDER (Llama 4 Scout works on Groq's free tier).
VISION_MODEL = config._get("HF_VISION_MODEL", "meta-llama/Llama-4-Scout-17B-16E-Instruct")

BUCKET = "listing-photos"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024   # reject anything above 10 MB outright
MAX_SIDE = 1280                       # downscale longest side to this

_PROMPT = (
    "You are a strict crop quality inspector for an African farmers marketplace. "
    "The farmer says this photo shows: {crop}. "
    'Reply with ONLY a JSON object, no other text: '
    '{{"is_match": true or false (does the photo really show {crop}?), '
    '"score": a number 0-10 rating the visible quality (freshness, ripeness, '
    'uniformity, absence of damage or rot; use null if is_match is false), '
    '"note": "one short, honest sentence telling a buyer what they are seeing"}}'
)


def allowed_photo(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def prepare_image(raw: bytes) -> bytes:
    """Downscale + re-encode as JPEG. Raises ValueError on unreadable images."""
    from PIL import Image
    try:
        img = Image.open(io.BytesIO(raw))
        img = img.convert("RGB")
    except Exception:
        raise ValueError("That file doesn't look like a readable photo.")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85)
    return out.getvalue()


def _parse_json(text: str) -> dict | None:
    """Extract the JSON object from a model reply (tolerates code fences)."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def rate_photo(jpeg_bytes: bytes, crop: str) -> dict | None:
    """Ask the vision model to verify + rate the photo.

    Returns {"is_match": bool, "score": float|None, "note": str} or None if
    the model is unavailable/unparseable (caller then accepts the photo
    without a rating rather than blocking the farmer).
    """
    if not config.hf_ready():
        return None
    try:
        from huggingface_hub import InferenceClient
        client = InferenceClient(provider=config.HF_PROVIDER, api_key=config.HF_TOKEN)
        uri = "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes).decode()
        resp = client.chat_completion(
            messages=[{"role": "user", "content": [
                {"type": "text", "text": _PROMPT.format(crop=crop)},
                {"type": "image_url", "image_url": {"url": uri}},
            ]}],
            model=VISION_MODEL, max_tokens=150, temperature=0.1,
        )
        data = _parse_json(resp.choices[0].message.content or "")
        if data is None or "is_match" not in data:
            return None
        score = data.get("score")
        if score is not None:
            score = max(0.0, min(10.0, float(score)))
        return {
            "is_match": bool(data["is_match"]),
            "score": score,
            "note": str(data.get("note") or "").strip()[:300],
        }
    except Exception:
        return None


def upload_photo(jpeg_bytes: bytes) -> str:
    """Store the photo in Supabase Storage and return its public URL."""
    path = f"{uuid.uuid4().hex}.jpg"
    storage = supa.service().storage.from_(BUCKET)
    storage.upload(path, jpeg_bytes, {"content-type": "image/jpeg"})
    return storage.get_public_url(path)
