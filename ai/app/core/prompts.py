"""Prompt templates for RAG generation."""

import orjson
from typing import Any, Optional

from app.core.schemas import VectorChunk


def build_rag_prompt(
    chunks: list[dict[str, Any]],
    user_query: str,
    history: Optional[list[dict[str, str]]] = None,
    summary: Optional[str] = None,
) -> str:
    """Build RAG prompt with context chunks and optional conversation history."""
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

    history_lines = []
    if history:
        # Use up to last 10 turns for better memory
        recent = history[-10:]
        for turn in recent:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            history_lines.append(f"{role}: {content}")
    history_block = "\n".join(history_lines)

    summary_block = summary or ""

    prompt = f"""SYSTEM:
You are a Clinical Decision Support Assistant designed to help healthcare professionals by providing accurate, evidence-based medical information from the provided knowledge base.
You must cited sources (Guidelines, Journals) and never invent medical facts.

CONTEXT:
{ctx_block}

HISTORY (most recent first at bottom):
{history_block}

CONVERSATION SUMMARY (if provided):
{summary_block}

USER:
{user_query}

ASSISTANT INSTRUCTIONS:
- Use only the provided context. If it does not support an answer, say: "I don't have verifiable information in the clinical knowledge base for that query."
- DO NOT hallucinate diagnoses or treatments.
- Respond in GitHub-Flavored Markdown (GFM).
- Begin your answer with a level-3 heading containing the user question:
  "### {user_query}"

- Structure your response for clinical clarity:
  - **Clinical Summary**: Brief overview based on evidence.
  - **Evidence/Guidelines**: Key points from the retrieved documents.
  - **Recommendations/Next Steps**: If applicable and supported by context.
  - **Risk Factors/Red Flags**: If mentioned in the context.

- Bold important medical terms, drug names, and doses (e.g., **Aspirin 81mg**, **Hypertension**).

- Citations:
  - Refer to the specific guideline or source title in the text (e.g., "According to the **ACC/AHA Guidelines**...").
  - Do NOT include a separate "Sources" section (handled by UI).

- Pronouns and References: Use HISTORY and SUMMARY to resolve context.

- MANDATORY DISCLAIMER:
  If the question implies a specific patient diagnosis or treatment plan, always prepend or append:
  > "This is a decision support output based on available guidelines. It is not a substitute for professional clinical judgment."
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


