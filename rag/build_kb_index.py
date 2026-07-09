"""Regenerate rag/KB_INDEX.md from the knowledge base on disk.

The index is a human-facing catalogue of every document, grouped by category,
with live document and word counts. It lives outside ``knowledge_base/`` so it
is not itself retrieved. Run it whenever documents are added or renamed:

    python -m rag.build_kb_index      # from the project root
    python rag/build_kb_index.py

It reads each Markdown file's H1 title (falling back to a title-cased filename),
counts words, and writes KB_INDEX.md with a summary table and per-category lists.
"""
from __future__ import annotations

import re
from pathlib import Path

KB_DIR = Path(__file__).parent / "knowledge_base"
INDEX_FILE = Path(__file__).parent / "KB_INDEX.md"

# Friendly display names + emoji per category, for the summary table.
CATEGORY_LABELS = {
    "crops": "🌽 Crops",
    "diseases": "🦠 Diseases",
    "pests": "🐛 Pests",
    "weeds": "🌿 Weeds",
    "livestock": "🐄 Livestock",
    "soil": "🪨 Soil",
    "fertilisers": "🧪 Fertilisers",
    "irrigation": "💧 Irrigation",
    "weather": "🌦️ Weather & Climate",
    "planting_calendars": "📅 Planting Calendars",
    "harvesting": "🌾 Harvesting",
    "storage": "📦 Storage",
    "sustainability": "♻️ Sustainability",
    "marketplace": "🛒 Marketplace",
    "pricing": "💰 Pricing",
    "regulations": "📋 Regulations",
    "emergency_guides": "🚨 Emergency Guides",
    "troubleshooting": "🔧 Troubleshooting",
    "faqs": "❓ FAQs",
    "ai_guidelines": "🤖 AI Guidelines",
}

_H1_RE = re.compile(r"^#\s+(.*)$", re.MULTILINE)


def _title(md: str, path: Path) -> str:
    m = _H1_RE.search(md)
    if m:
        return m.group(1).strip()
    return path.stem.replace("_", " ").title()


def build() -> str:
    docs: dict[str, list[tuple[str, str]]] = {}
    total_words = 0
    total_docs = 0
    for path in sorted(KB_DIR.rglob("*.md")):
        rel = path.relative_to(KB_DIR).as_posix()
        category = rel.split("/")[0] if "/" in rel else "general"
        md = path.read_text(encoding="utf-8")
        total_words += len(md.split())
        total_docs += 1
        docs.setdefault(category, []).append((_title(md, path), rel))

    # Order categories by the label map first, then any extras alphabetically.
    ordered = [c for c in CATEGORY_LABELS if c in docs]
    ordered += sorted(c for c in docs if c not in CATEGORY_LABELS)

    lines: list[str] = []
    lines.append("# FarmConnect AI — Knowledge Base Index\n")
    lines.append(
        f"This Retrieval-Augmented Generation (RAG) knowledge base contains "
        f"**{total_docs} documents** (**~{total_words:,} words**) across "
        f"**{len(docs)} categories**, written as authoritative reference material "
        f"for African smallholder farmers and buyers. It is indexed automatically by "
        f"`rag/retriever.py` (hybrid BM25 + TF-IDF search) and grounds every answer "
        f"FarmConnect AI gives.\n"
    )
    lines.append(
        "> This index is generated for humans. It lives outside `knowledge_base/` so it "
        "is not itself indexed for retrieval. Regenerate it with `python -m rag.build_kb_index` "
        "whenever documents are added.\n"
    )
    lines.append("## Contents at a glance\n")
    lines.append("| Category | Documents |")
    lines.append("|---|---|")
    for c in ordered:
        label = CATEGORY_LABELS.get(c, c.replace("_", " ").title())
        lines.append(f"| {label} | {len(docs[c])} |")
    lines.append(f"| **Total** | **{total_docs}** |\n")

    for c in ordered:
        label = CATEGORY_LABELS.get(c, c.replace("_", " ").title())
        lines.append(f"## {label}\n")
        for title, rel in sorted(docs[c], key=lambda t: t[0].lower()):
            lines.append(f"- **{title}** — `{rel}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    content = build()
    INDEX_FILE.write_text(content, encoding="utf-8")
    # A short console summary.
    docs = sum(1 for _ in KB_DIR.rglob("*.md"))
    words = sum(len(p.read_text(encoding="utf-8").split()) for p in KB_DIR.rglob("*.md"))
    print(f"Wrote {INDEX_FILE} — {docs} documents, ~{words:,} words.")


if __name__ == "__main__":
    main()
