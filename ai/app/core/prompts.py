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
    response_mode: str = "detailed",
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

    prompt = f"""
You are an advanced, evidence-based Clinical Decision Support Engine. 

=== UPLOADED PATIENT DATA / CONTEXT ===
{patient_context if patient_context else "No patient data uploaded."}

=== MEDICAL KNOWLEDGE BASE CONTEXT (GUIDELINES) ===
{ctx_block}

=== CONVERSATION HISTORY (Most recent at bottom) ===
{history_block}

=== CONVERSATION SUMMARY ===
{summary_block}

=== CLINICIAN QUESTION ===
{user_query}

CRITICAL REASONING INSTRUCTIONS:
1. Act as a highly trained physician consultant. You are answering a colleague.
2. If PATIENT DATA is provided, you MUST analyze it specifically. Pay close attention to any tags labeled (FLAG: High/Low/Critical).
3. If MEDICAL KNOWLEDGE BASE CONTEXT is relevant to the question or the patient data, strictly ground your reasoning in it. Do not invent medical guidelines.
4. Maintain logical consistency with the CONVERSATION HISTORY. If the clinician is asking a 10th follow-up question about the same lab result, remember your previous conclusions.
"""

    if response_mode in ["medium", "detailed"]:
        prompt += f"""
REQUIRED RESPONSE STRUCTURE:
You must format your response EXACTLY using the following markdown headers. Do not deviate.

### 🧠 Clinical Interpretation
(Provide a clear, context-aware analysis of the data and the question. Connect the dots between history, labs, and symptoms.)

### ⚠️ Risk Flags & Warnings
(Highlight any critical values, absolute contraindications, or severe interaction risks. If none, state "No immediate standard risk flags identified.")

### 📚 Evidence Basis
(Briefly explain how the medical guidelines/literature support your interpretation. Cite naturally, e.g., "According to [Ref 1]...")

### 📋 Actionable Next Steps
(Provide 2-4 practical, concrete next steps for the clinician. What should they order, prescribe, or monitor next?)

RESPOND ONLY WITH THE SECTIONS ABOVE.
"""

    prompt += f"\n{style_instruction}\n"
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


