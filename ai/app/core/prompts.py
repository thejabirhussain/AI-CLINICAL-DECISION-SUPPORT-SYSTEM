"""Prompt templates for RAG generation."""

import orjson
from typing import Any

from app.core.schemas import VectorChunk


def build_rag_prompt(chunks: list[dict[str, Any]], user_query: str) -> str:
    """Build RAG prompt with context chunks."""
    # Format chunks as JSONL
    ctx_lines = []
    for chunk in chunks:
        ctx_obj = {
            "url": chunk.get("url", ""),
            "title": chunk.get("title", ""),
            "section_heading": chunk.get("section_heading"),
            "char_start": chunk.get("char_start", 0),
            "char_end": chunk.get("char_end", 0),
            "excerpt": chunk.get("text", "")[:500],
        }
        ctx_lines.append(orjson.dumps(ctx_obj).decode("utf-8"))

    ctx_block = "\n".join(ctx_lines)

    prompt = f"""SYSTEM:
You are a factual assistant that answers only from the provided IRS.gov knowledge snippets. You must cite sources and never invent facts.

CONTEXT:
{ctx_block}

USER:
{user_query}

ASSISTANT INSTRUCTIONS:
- Use only the provided context. If it does not support an answer, say: "I don't have verifiable information in the knowledge base for that query." Offer top similar sources with excerpts.

- Respond in GitHub-Flavored Markdown (GFM).
- Begin your answer with a level-3 heading containing the user question exactly:
  "### {user_query}"
- Use concise paragraphs and bullet lists for steps and key points.
- Bold key labels or terms (e.g., **Eligibility**, **Amount**, **Deadline**).

- After the answer, include a section titled "### Sources" with bullet items in this format:
  - [<page_title>] — <section_heading if available> — <url> — excerpt: "..." (char_start–char_end)

- If sources conflict, present both and mark uncertainty.
- Include relevant IRS form numbers if present in context.

- If the question asks for legal/tax filing advice, prepend:

  "I am not a lawyer; for legal or tax-filing advice consult a qualified tax professional or the IRS."
"""

    return prompt


def build_no_results_prompt(query: str, closest_matches: list[dict[str, Any]]) -> str:
    """Build prompt for when no results are found."""
    matches_text = ""
    if closest_matches:
        matches_text = "\n\nClosest matches in knowledge base:\n"
        for i, match in enumerate(closest_matches[:5], 1):
            matches_text += f"{i}. {match.get('title', 'Unknown')} - {match.get('url', '')}\n"
            matches_text += f"   Excerpt: {match.get('text', '')[:200]}...\n"

    return f"I don't have verifiable information in the knowledge base for that query.{matches_text}"


