"""Hugging Face Inference client for FarmConnect AI.

Provides the two model calls the cloud RAG pipeline needs, both through Hugging
Face's serverless Inference API (no local GPU/RAM required):

* :func:`embed_query` / :func:`embed_texts` — sentence embeddings from a
  feature-extraction model (default ``all-MiniLM-L6-v2``, 384 dims). Used to
  turn documents and questions into vectors for the Supabase pgvector store.
* :func:`generate` — a grounded answer from a serverless instruct model
  (default ``Qwen/Qwen2.5-7B-Instruct``) via chat completion.

Everything degrades gracefully: if the token is missing or the SDK is not
installed, :func:`available` returns ``False`` and the assistant falls back to
another backend (see ``rag/assistant.py``).
"""
from __future__ import annotations

import config

_client = None


def available() -> bool:
    if not config.hf_ready():
        return False
    try:
        import huggingface_hub  # noqa: F401
    except Exception:
        return False
    return True


def _get_client():
    global _client
    if _client is None:
        from huggingface_hub import InferenceClient
        # Passing the token here; model is chosen per-call so one client serves
        # both the embedding and the chat model.
        try:
            _client = InferenceClient(provider=config.HF_PROVIDER, api_key=config.HF_TOKEN)
        except TypeError:
            # Older huggingface_hub without the provider/api_key kwargs.
            _client = InferenceClient(token=config.HF_TOKEN)
    return _client


def _to_vector(raw) -> list[float]:
    """Normalise a feature-extraction result to a flat list[float].

    Sentence-transformer endpoints usually return a pooled 1-D vector; some
    return 2-D token embeddings, which we mean-pool into a single vector.
    """
    import numpy as np
    arr = np.asarray(raw, dtype="float32")
    if arr.ndim == 2:
        arr = arr.mean(axis=0)
    elif arr.ndim == 3:            # (batch, tokens, dim)
        arr = arr.mean(axis=1)[0]
    return arr.astype(float).ravel().tolist()


def embed_query(text: str) -> list[float]:
    """Embed a single string (a question or a chunk) -> 384-dim vector."""
    client = _get_client()
    out = client.feature_extraction(text, model=config.HF_EMBED_MODEL)
    return _to_vector(out)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed several strings. Falls back to per-item calls if batch is unsupported."""
    client = _get_client()
    try:
        out = client.feature_extraction(texts, model=config.HF_EMBED_MODEL)
        import numpy as np
        arr = np.asarray(out, dtype="float32")
        if arr.ndim == 2 and len(texts) == arr.shape[0]:
            return [row.astype(float).tolist() for row in arr]
    except Exception:
        pass
    return [embed_query(t) for t in texts]


def generate(prompt: str, system: str | None = None,
             max_tokens: int = 512, temperature: float = 0.2) -> str:
    """Grounded chat completion from the serverless instruct model."""
    client = _get_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat_completion(
        messages=messages,
        model=config.HF_CHAT_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    text = (resp.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("Empty response from Hugging Face model.")
    return text


def info() -> dict:
    return {
        "available": available(),
        "chat_model": config.HF_CHAT_MODEL,
        "embed_model": config.HF_EMBED_MODEL,
        "provider": config.HF_PROVIDER,
    }
