"""Ingest the Markdown knowledge base into Supabase (pgvector) for cloud RAG.

For every document under ``rag/knowledge_base/`` this:
  1. splits it into heading-level (and, for long sections, windowed) chunks,
  2. embeds each chunk with the Hugging Face embedding model,
  3. upserts the document row and replaces its chunks in Supabase.

Idempotent: a document whose content is unchanged since the last run is skipped
(compared by content hash) unless you pass ``--force``.

Usage:
    python ingest_kb.py                # ingest new/changed documents
    python ingest_kb.py --force        # re-embed and re-ingest everything
    python ingest_kb.py --category crops   # limit to one category

Requires SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY and HF_TOKEN in the environment
(.env). See .env.example.
"""
from __future__ import annotations

import argparse
import hashlib
import sys

import config
from rag.retriever import KB_DIR, _split_sections, _window_long_body
from rag import hf_client


def _chunks_for(md: str, title: str):
    """Yield (heading, body, embed_text) for each chunk of a document."""
    _, sections = _split_sections(md)
    for heading, body in sections:
        if not body.strip():
            continue
        for window in _window_long_body(body):
            # Embed the body enriched with title + heading for better matching;
            # store the plain body as the retrievable/citable content.
            embed_text = f"{title}. {heading}. {window}".strip(". ")
            yield heading, window, embed_text


def ingest(force: bool = False, only_category: str | None = None) -> None:
    gaps = [g for g in config.missing() if g in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "HF_TOKEN")]
    if gaps:
        sys.exit(f"Missing required settings: {', '.join(gaps)}. Fill them in .env (see .env.example).")

    import supa
    client = supa.service()

    # Existing hashes, to skip unchanged documents.
    existing: dict[str, str] = {}
    try:
        rows = client.table("kb_documents").select("doc_id,content_hash").execute().data or []
        existing = {r["doc_id"]: r.get("content_hash") for r in rows}
    except Exception as e:
        sys.exit(f"Could not reach Supabase: {e}")

    paths = sorted(KB_DIR.rglob("*.md"))
    total_docs = total_chunks = skipped = 0

    for path in paths:
        rel = path.relative_to(KB_DIR).as_posix()
        category = rel.split("/")[0] if "/" in rel else "general"
        if only_category and category != only_category:
            continue
        md = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
        if not force and existing.get(rel) == digest:
            skipped += 1
            continue

        # Title = first H1, else prettified filename.
        title = path.stem.replace("_", " ").title()
        for line in md.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break

        chunks = list(_chunks_for(md, title))
        if not chunks:
            continue

        embeddings = hf_client.embed_texts([c[2] for c in chunks])

        client.table("kb_documents").upsert({
            "doc_id": rel,
            "category": category,
            "title": title,
            "word_count": len(md.split()),
            "content_hash": digest,
        }).execute()
        # Replace this document's chunks.
        client.table("kb_chunks").delete().eq("doc_id", rel).execute()
        rows = [{
            "doc_id": rel,
            "category": category,
            "title": title,
            "heading": heading,
            "content": body,
            "embedding": emb,
        } for (heading, body, _), emb in zip(chunks, embeddings)]
        # Insert in modest batches to keep requests small.
        for i in range(0, len(rows), 50):
            client.table("kb_chunks").insert(rows[i:i + 50]).execute()

        total_docs += 1
        total_chunks += len(rows)
        print(f"  ✓ {rel}  ({len(rows)} chunks)")

    print(f"\nDone. Ingested {total_docs} documents ({total_chunks} chunks); "
          f"skipped {skipped} unchanged.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest the FarmConnect AI knowledge base into Supabase.")
    ap.add_argument("--force", action="store_true", help="Re-embed and re-ingest every document.")
    ap.add_argument("--category", help="Only ingest one category (e.g. crops).")
    args = ap.parse_args()
    ingest(force=args.force, only_category=args.category)


if __name__ == "__main__":
    main()
