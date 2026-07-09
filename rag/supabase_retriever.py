"""Cloud retrieval: semantic search over the Supabase pgvector knowledge base.

This is the Supabase counterpart to ``rag/retriever.py``. It embeds the farmer's
question with the Hugging Face embedding model, then asks Postgres for the most
similar knowledge-base chunks via the ``match_kb_chunks`` function.

It exposes the same ``search_grouped(query, k, max_docs)`` shape as the local
engine — returning ``(hits, sources, meta)`` — so ``rag/assistant.py`` can use
either backend interchangeably.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import config
from . import hf_client


@dataclass
class SupaChunk:
    """One retrieved knowledge-base section (matches the local Chunk API)."""
    doc_id: str
    category: str
    doc_title: str
    heading: str
    text: str
    score: float = 0.0
    tokens: list = field(default_factory=list, repr=False)

    @property
    def title(self) -> str:
        return f"{self.doc_title} — {self.heading}" if self.heading else self.doc_title

    def snippet(self, limit: int = 320) -> str:
        body = re.sub(r"\s+", " ", self.text).strip()
        return body if len(body) <= limit else body[:limit].rsplit(" ", 1)[0] + "…"


def available() -> bool:
    return config.supabase_ready() and hf_client.available()


def _band(similarity: float) -> str:
    if similarity >= 0.55:
        return "high"
    if similarity >= 0.40:
        return "medium"
    return "low"


def search_grouped(query: str, k: int = 6, max_docs: int = 4):
    """Semantic search. Returns (hits, sources, meta) like the local engine."""
    query = (query or "").strip()
    if not query:
        return [], [], {"confidence": 0.0, "band": "none", "hybrid": False,
                        "backend": "supabase"}

    import supa
    embedding = hf_client.embed_query(query)
    resp = supa.service().rpc(
        "match_kb_chunks",
        {"query_embedding": embedding, "match_count": k},
    ).execute()
    rows = resp.data or []

    hits: list[SupaChunk] = []
    for r in rows:
        hits.append(SupaChunk(
            doc_id=r["doc_id"],
            category=r["category"],
            doc_title=r["title"],
            heading=r.get("heading") or "",
            text=r["content"],
            score=round(float(r.get("similarity") or 0.0), 4),
        ))

    sources: list[dict] = []
    seen: set[str] = set()
    for c in hits:
        if c.doc_id not in seen:
            seen.add(c.doc_id)
            sources.append({"doc_id": c.doc_id, "title": c.doc_title, "category": c.category})
        if len(sources) >= max_docs:
            break

    top = hits[0].score if hits else 0.0
    meta = {
        "confidence": round(top, 3),
        "band": _band(top) if hits else "none",
        "semantic": round(top, 3),
        "coverage": None,          # not applicable to pure vector search
        "hybrid": False,
        "backend": "supabase",
    }
    return hits, sources, meta
