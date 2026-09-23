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
    for i, chunk in enumerate(chunks, 1):
        ctx_obj = {
            "ref": i,
            "url": chunk.get("url", ""),
            "title": chunk.get("title", ""),
            "section_heading": chunk.get("section_heading"),
            "char_start": chunk.get("char_start", 0),
            "char_end": chunk.get("char_end", 0),
            "excerpt": chunk.get("text", "")[:500],
        }
        ctx_lines.append(json.dumps(ctx_obj))

    ctx_block = "\n".join(ctx_lines) or (
        "No relevant knowledge base entries were found for this question. "
        "Do not cite any references; state that the answer is based on general clinical knowledge."
    )

    history_lines = []
    if history:
        # Use up to last 10 turns for better memory
        recent = history[-10:]
        for turn in recent:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            # Earlier answers are left out: small local models copy them verbatim instead of answering the new question.
            if role == "assistant":
                continue
            history_lines.append(f"{role}: {content}")
    history_block = "\n".join(history_lines)

    summary_block = summary or ""

    prompt = f"""
You are an advanced, evidence-based Clinical Decision Support Engine. 

=== UPLOADED PATIENT DATA / CONTEXT ===
{patient_context if patient_context else "No patient data uploaded."}

=== MEDICAL KNOWLEDGE BASE CONTEXT (GUIDELINES) ===
{ctx_block}

=== EARLIER QUESTIONS IN THIS CONVERSATION (Most recent at bottom) ===
{history_block}

=== CONVERSATION SUMMARY ===
{summary_block}

=== CLINICIAN QUESTION ===
{user_query}

CRITICAL REASONING INSTRUCTIONS:
1. Act as a highly trained physician consultant. You are answering a colleague.
2. If PATIENT DATA is provided, you MUST analyze it specifically. Pay close attention to any tags labeled (FLAG: High/Low/Critical).
3. If MEDICAL KNOWLEDGE BASE CONTEXT is relevant to the question or the patient data, strictly ground your reasoning in it. Do not invent medical guidelines.
   Only cite [Ref N] numbers that appear in the knowledge base context above.
   Distinguish current MEDICATIONS from ALLERGIES: never suggest stopping a drug the patient is only allergic to.
4. Quote patient values EXACTLY as listed in the patient data (test name, value, unit and flag); never swap values between tests.
5. Answer the CLINICIAN QUESTION that was asked now, directly, in your first sentence. Do not restate the whole lab list unless asked.
6. For medication questions, check EACH current medication against kidney function (eGFR/creatinine), potassium, the other medications and the allergies, and state a concrete recommendation for each drug that is a concern. If the clinician is asking a 10th follow-up question about the same lab result, remember your previous conclusions.
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
(Briefly explain how the medical guidelines/literature support your interpretation. Cite knowledge base entries by their "ref" number, e.g., "According to [Ref 1]...". If there are no knowledge base entries, say the reasoning is based on general clinical knowledge.)

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


