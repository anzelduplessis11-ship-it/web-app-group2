"""FarmConnect — Retrieval-Augmented Generation package.

    from rag import answer, health
    result = answer("why are my maize leaves turning yellow?")

The heavy lifting lives in three modules:
    retriever.py  — offline BM25 search over the Markdown knowledge base
    llm.py        — optional local language model (Ollama) client
    assistant.py  — orchestration + AI safety guidelines
"""
from .assistant import answer, health
from .retriever import get_kb

__all__ = ["answer", "health", "get_kb"]
