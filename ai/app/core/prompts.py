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
    style_instruction: str = "",
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

    prompt = f"""PATIENT DATA / CONTEXT:
{patient_context if patient_context else ""}

KNOWLEDGE BASE CONTEXT:
{ctx_block}

HISTORY (most recent first at bottom):
{history_block}

CONVERSATION SUMMARY (if provided):
{summary_block}

USER QUESTION:
{user_query}

ASSISTANT INSTRUCTIONS:
- You MUST strictly answer the specific USER QUESTION. If the retrieved KNOWLEDGE BASE contains broader, tangential information (e.g., treatment lists when only a definition is asked), ignore it. Do not over-answer or summarize everything retrieved.
- Interpret the clinical context and provide reasoning *before* making recommendations.
- Integrate citations subtly and professionally into the natural flow of your explanation (e.g., "According to the provided guidelines [1]..."). DO NOT append a manual "References" or "Sources" section at the bottom.
- Highlight risk stratification, red flags, and contraindications where clinically relevant.
- Provide actionable next steps suitable for real-world clinical decision-making.
- Use the provided KNOWLEDGE BASE CONTEXT for all medical reasoning and guidelines.
- If the question refers to PATIENT DATA, prioritize that information for specifics, but ground the approach in the KNOWLEDGE BASE.
- If no PATIENT DATA / CONTEXT is provided, frame uncertainty professionally mid-sentence (e.g., "In the absence of additional clinical details..." or "Assuming an otherwise healthy adult..."). DO NOT use boilerplate defensive disclaimers complaining about missing data.
- If the KNOWLEDGE BASE lacks verifiable information, state: "I don't have verifiable information in the clinical knowledge base for that query."
- DO NOT hallucinate.
- Tone: Professional, confident, and helpful for a practicing physician. Do not sound like a machine.
- Writing Style: Use shorter, sharper sentences. Present a clear clinically prioritized narrative. Prioritize common causes first before rare associations. Use bullet points sparingly and only when necessary for readability. Do not repeat citations excessively.
- Respond in GitHub-Flavored Markdown (GFM).

REQUIRED RESPONSE STYLE AND SCOPE ENFORCEMENT:
{style_instruction}
"""

    return prompt

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


