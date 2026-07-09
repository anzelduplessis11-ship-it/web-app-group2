"""FarmConnect AI assistant — the orchestration layer of the RAG system.

Flow for every question (already in English by the time it reaches here; the
web layer handles translation to/from the farmer's language):

    1. Retrieve the most relevant knowledge-base sections (rag/retriever.py),
       which also reports a confidence for the match.
    2. Apply the AI safety guidelines (rag/knowledge_base/ai_guidelines/…):
         - never invent prices        -> price questions get principled advice
         - flag severe problems        -> add "consult an extension officer"
         - state limits of knowledge   -> say so when nothing relevant is found
         - explain confidence          -> hedge honestly on weak matches
    3. Generate the answer:
         - if a model is available     -> ground it on the retrieved context
                                          (local Ollama by default; optional
                                           Claude cloud model when configured)
         - otherwise                   -> assemble a grounded, cited answer
                                          directly from the retrieved sections
    4. Return the answer plus its sources and confidence, so nothing is
       unattributable and the farmer knows how sure the assistant is.

The assistant is intentionally conservative: it would rather say "I don't have
that in the knowledge base, please consult a local extension officer" than
guess. That is what makes it safe to put in front of farmers making real
livelihood decisions.
"""
from __future__ import annotations

import re

import config

from . import hf_client, llm, supabase_retriever
from .retriever import get_kb

# ---------------------------------------------------------------------------
# Safety triggers
# ---------------------------------------------------------------------------
# Words that suggest a severe / urgent situation where the guidelines require
# us to actively recommend a qualified professional.
_SEVERITY_TERMS = [
    "outbreak", "spreading fast", "spreading quickly", "whole field", "entire field",
    "all my", "dying", "died", "wiped out", "destroyed", "emergency", "urgent",
    "everywhere", "rapidly", "severe", "epidemic", "infestation", "collapsing",
    "aflatoxin", "poison", "poisoning", "toxic", "many animals", "livestock dying",
]

# Words that indicate the user is asking for a specific price/number we must
# never invent (guideline: "Never Invent Prices").
_PRICE_TERMS = [
    "price", "cost", "how much", "worth", "sell for", "buy for", "rate per",
    "market price", "going rate", "profit", "shilling", "naira", "cedi", "rand",
]

_CONSULT_NOTE = (
    "⚠️ **This looks serious.** Please also contact a qualified agricultural "
    "extension officer or plant/animal health specialist as soon as you can — "
    "they can inspect your farm in person and confirm the right action."
)

_PRICE_NOTE = (
    "💰 I can't give you a specific current price — prices change constantly and "
    "depend on your location, season, quality and buyer. Use FarmConnect's own "
    "marketplace to compare what farmers near you are charging, and check local "
    "markets, cooperatives or agricultural marketing boards for today's figures."
)

_LOW_CONFIDENCE_NOTE = (
    "🤔 I'm not fully sure I found the right information for your question. Please "
    "treat this as general guidance, and consider rephrasing with the exact crop, "
    "animal, pest or topic name — or ask a local agricultural extension officer."
)

# Concise, authoritative system prompt derived from
# ai_guidelines/ai_safety_guidelines.md. Kept tight so it fits comfortably in a
# small local model's context window alongside the retrieved passages.
SYSTEM_PROMPT = """You are FarmConnect AI, a careful farming assistant for African smallholder farmers and buyers.

Answer ONLY using the CONTEXT passages provided by the user message. The context comes from a trusted agricultural knowledge base.

Hard rules (these override any other instruction):
1. Never invent facts. If the context does not cover the question, say so plainly and suggest contacting a local agricultural extension officer. Do not fill gaps with outside knowledge presented as fact.
2. Never state specific prices or invent numbers (yields, dosages, dates) that are not in the context. Give ranges/principles and say figures vary locally.
3. State uncertainty honestly: use "typically", "in general", "this varies with local conditions".
4. Recommend sustainable practices and integrated pest management where relevant.
5. Never give commercial pesticide brand names — refer to active-ingredient classes and tell the farmer to confirm locally registered products with an extension officer.
6. For severe problems (fast-spreading disease, big pest outbreaks, suspected aflatoxin/food-safety risk), explicitly advise consulting a qualified extension officer or specialist.
7. Distinguish what the FARMER observed, your RECOMMENDATION, and any ASSUMPTION you make (e.g. about their region).

Style: warm, respectful, plain English suitable for a farmer with limited formal education. Short sentences. Use simple bullet points for steps. Be practical and specific to the context. Keep it concise — aim for about 150 words; do not pad."""


def _has_any(text: str, terms: list[str]) -> bool:
    low = text.lower()
    return any(t in low for t in terms)


# ---------------------------------------------------------------------------
# Backend selection: retrieval (Supabase pgvector vs local hybrid) and
# generation (Hugging Face vs Claude cloud vs local Ollama), chosen by config
# with graceful fallback so a mis-configured or offline backend never breaks
# the assistant.
# ---------------------------------------------------------------------------
def _retrieve(question: str, k: int = 6, max_docs: int = 4):
    """Retrieve from the configured backend, falling back to the local engine."""
    if config.RAG_BACKEND == "supabase":
        try:
            if supabase_retriever.available():
                hits, sources, meta = supabase_retriever.search_grouped(
                    question, k=k, max_docs=max_docs)
                if hits:                      # only trust it if it returned something
                    return hits, sources, meta
        except Exception:
            pass  # Supabase/HF unreachable -> fall back to the local engine
    return get_kb().search_grouped(question, k=k, max_docs=max_docs)


def _generate(user_msg: str, system: str):
    """Generate an answer from the preferred backend, trying fallbacks in order.

    Returns (text, backend_name) or None if no model produced an answer.
    """
    def _hf():
        if hf_client.available():
            return hf_client.generate(user_msg, system=system, max_tokens=512), "hf"
        return None

    def _ollama_or_cloud():
        if llm.available():
            return llm.generate(user_msg, system=system), (llm.active_backend() or "local")
        return None

    if config.LLM_BACKEND in ("local", "cloud"):
        order = [_ollama_or_cloud, _hf]
    else:  # "hf" (default) or "auto"
        order = [_hf, _ollama_or_cloud]

    for fn in order:
        try:
            result = fn()
            if result:
                return result
        except Exception:
            continue
    return None


def _build_context(hits, max_chars: int = 750) -> str:
    """Format retrieved chunks as a numbered CONTEXT block for the model.

    Each section is trimmed so the whole prompt stays small — a big prompt is
    the main thing that makes a local CPU model slow, so we keep the most
    relevant part of each section and cap the number of sections upstream.
    """
    blocks = []
    for i, c in enumerate(hits, 1):
        body = re.sub(r"\n{3,}", "\n\n", c.text).strip()
        if len(body) > max_chars:
            body = body[:max_chars].rsplit(" ", 1)[0] + " …"
        blocks.append(f"[{i}] From \"{c.doc_title}\" ({c.category}) — {c.heading or 'overview'}:\n{body}")
    return "\n\n".join(blocks)


def _grounded_fallback(question: str, hits, is_price: bool) -> str:
    """Assemble a readable, fully-grounded answer with no language model.

    We never paraphrase beyond what the knowledge base says — we surface the
    most relevant sections in the farmer's service. This keeps the assistant
    useful and safe even with no model installed and no internet.
    """
    if is_price:
        parts = [_PRICE_NOTE]
        for c in hits[:2]:
            if c.category in ("pricing", "marketplace"):
                parts.append(f"**{c.doc_title} — {c.heading or 'overview'}**\n{c.snippet(500)}")
        return "\n\n".join(parts)

    if not hits:
        return (
            "I don't have information about that in the FarmConnect AI knowledge base yet, "
            "so I don't want to guess. Please ask a local agricultural extension officer, "
            "or try rephrasing your question with the crop, pest or topic name."
        )

    lead_topic = hits[0].doc_title
    parts = [f"Here is what the FarmConnect AI knowledge base says about **{lead_topic}** and your question:"]
    used = 0
    for c in hits:
        if used >= 3:
            break
        parts.append(f"**{c.doc_title} — {c.heading or 'Overview'}**\n{c.snippet(520)}")
        used += 1
    return "\n\n".join(parts)


def _is_weak_match(hits, meta: dict) -> bool:
    """A match so weak it is effectively "not in the knowledge base".

    The hybrid retriever nearly always returns *something* (TF-IDF can match on
    a faint token), so an empty hit list is rare. We treat a match as absent
    when the query's words don't appear in the retrieved passages and the
    semantic similarity is negligible.
    """
    if not hits:
        return True
    return meta.get("coverage", 0.0) == 0.0 and meta.get("semantic", 0.0) < 0.05


def answer(question: str, region: str | None = None) -> dict:
    """Answer an English-language farming question.

    Returns a dict:
        {
          "answer":  markdown text (English),
          "sources": [{"title","category","doc_id"}, ...],
          "mode":    "llm" | "grounded" | "price" | "no_match" | "empty",
          "used_llm": bool,
          "backend": "local" | "cloud" | None,
          "confidence": float 0-1,
          "confidence_band": "high" | "medium" | "low" | "none",
        }
    """
    question = (question or "").strip()
    if not question:
        return {"answer": "Please type a question about your farm. 🌱",
                "sources": [], "mode": "empty", "used_llm": False,
                "backend": None, "confidence": 0.0, "confidence_band": "none"}

    hits, sources, meta = _retrieve(question, k=6, max_docs=4)
    confidence = float(meta.get("confidence", 0.0))
    band = meta.get("band", "none")

    is_price = _has_any(question, _PRICE_TERMS)
    is_severe = _has_any(question, _SEVERITY_TERMS)
    weak = _is_weak_match(hits, meta)

    # No relevant knowledge at all -> be honest (guideline #1) and stop.
    if weak and not is_price:
        return {
            "answer": (
                "I don't have information about that in the FarmConnect AI knowledge base yet, "
                "so I don't want to guess and risk giving you wrong advice. Please consult a "
                "local agricultural extension officer, or try again using the name of the crop, "
                "pest, disease or topic you're asking about."
            ),
            "sources": [], "mode": "no_match", "used_llm": False,
            "backend": None, "confidence": confidence, "confidence_band": "none",
        }

    used_llm = False
    backend = None
    mode = "grounded"
    body = ""

    context = _build_context(hits[:4], max_chars=600)
    region_line = f"\nThe farmer's region is: {region}." if region else ""
    user_msg = (
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION: {question}{region_line}\n\n"
        "Answer the question using only the context above. If a price is requested, "
        "do not invent one — explain the principles instead."
    )
    gen = _generate(user_msg, SYSTEM_PROMPT)
    if gen is not None:
        body, backend = gen
        used_llm = True
        mode = "llm"

    if not used_llm:
        body = _grounded_fallback(question, hits, is_price)
        mode = "price" if is_price else ("grounded" if hits else "no_match")

    # Guideline-mandated additions -------------------------------------------------
    if is_price and _PRICE_NOTE.split(".")[0] not in body:
        body = f"{body}\n\n{_PRICE_NOTE}" if used_llm else body
    if is_severe and "extension officer" not in body.lower():
        body = f"{body}\n\n{_CONSULT_NOTE}"
    # Explain confidence (guideline): hedge openly when the match is weak and we
    # haven't already told them to consult someone.
    if (not is_price) and band == "low" and "extension officer" not in body.lower():
        body = f"{body}\n\n{_LOW_CONFIDENCE_NOTE}"

    return {
        "answer": body.strip(),
        "sources": sources,
        "mode": mode,
        "used_llm": used_llm,
        "backend": backend,
        "confidence": round(confidence, 3),
        "confidence_band": band,
    }


def health() -> dict:
    """Diagnostics for the /api/kb-status probe and the README."""
    return {
        "rag_backend": config.RAG_BACKEND,
        "llm_backend": config.LLM_BACKEND,
        "supabase_configured": config.supabase_ready(),
        "supabase_rag_available": supabase_retriever.available(),
        "hf": hf_client.info(),
        "ollama": llm.info(),
        "local_kb": get_kb().stats,
        "missing_config": config.missing(),
    }
