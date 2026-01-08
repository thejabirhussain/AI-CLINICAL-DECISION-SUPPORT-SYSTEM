"""Prompt templates for RAG generation."""

import json
from typing import Any, Optional

from app.core.schemas import VectorChunk


def build_rag_prompt(
    chunks: list[dict[str, Any]],
    user_query: str,
    history: Optional[list[dict[str, str]]] = None,
    summary: Optional[str] = None,
    patient_context: Optional[str] = None,
) -> str:
    """Build RAG prompt with context chunks, patient data, and optional conversation history."""
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
        ctx_lines.append(json.dumps(ctx_obj))

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
You are a Clinical Decision Support Assistant.
You must cite sources (Guidelines, Journals) and never invent medical facts.

PATIENT DATA / CONTEXT:
{patient_context if patient_context else "No specific patient data provided."}

KNOWLEDGE BASE CONTEXT:
{ctx_block}

HISTORY (most recent first at bottom):
{history_block}

CONVERSATION SUMMARY (if provided):
{summary_block}

USER QUESTION:
{user_query}

ASSISTANT INSTRUCTIONS:
- Use the provided KNOWLEDGE BASE CONTEXT to answer the question.
- If the question refers to the PATIENT DATA, prioritize that information for the specific case details, but use KNOWLEDGE BASE for medical reasoning/guidelines.
- If the KNOWLEDGE BASE does not allow for a verifiable answer, say: "I don't have verifiable information in the clinical knowledge base for that query."
- DO NOT hallucinate.
- Respond in GitHub-Flavored Markdown (GFM).
- **MANDATORY DISCLAIMER**: "This is a decision support output based on available guidelines. It is not a substitute for professional clinical judgment."
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


