from dataclasses import dataclass
import re


@dataclass
class ResponsePolicy:
    level: str
    max_tokens: int
    top_n: int
    style_instruction: str



# Enhanced Medical Cues
_SIMPLE_CUES = {
    "what is", "define", "definition", "date", "deadline", "where", "when", "who",
    "url", "link", "phone", "number", "amount", "fee", "cost", "due", "rate",
    "dose", "dosage", "frequency", "side effect", "symptom", "indication",
}

_ANALYTICAL_CUES = {
    "how", "why", "explain", "steps", "calculate", "eligibility", "example",
    "examples", "impact", "benefit", "pros", "cons", "difference", "compare",
    "mechanism", "pathophysiology", "risk factors", "contraindication",
}

_COMPLEX_CUES = {
    "comprehensive", "detailed", "end-to-end", "guide", "strategy", "multiple parts",
    "multi part", "multi-part", "in-depth", "tradeoffs", "limitations", "edge cases",
    "diagnostic criteria", "treatment plan", "management", "guidelines", "protocol",
}

# Domain-specific cues
_CLINICAL_GUIDANCE_CUES = {
    "approach to", "manage", "treat", "diagnose", "workup", "evaluation",
    "recommendation", "first line", "second line", "therapy",
}

_SCENARIO_CUES = {
    "scenario", "case", "suppose", "assume", "if i", "if we", "what happens if",
    "patient with", "h/o", "history of", "presents with",
}


def _count_cues(q: str, cues: set[str]) -> int:
    return sum(1 for c in cues if c in q)


def classify_query(query: str) -> dict:
    """Classify a query into a rich type and return an associated response policy."""
    q = query.strip().lower()

    length = len(q)
    num_questions = q.count("?")
    num_sentences = max(1, q.count(".") + q.count("?") + q.count("!"))

    simple_hits = _count_cues(q, _SIMPLE_CUES)
    analytical_hits = _count_cues(q, _ANALYTICAL_CUES)
    complex_hits = _count_cues(q, _COMPLEX_CUES)
    clinical_hits = _count_cues(q, _CLINICAL_GUIDANCE_CUES)
    scenario_hits = _count_cues(q, _SCENARIO_CUES)

    # 1. Complex Clinical Scenario / Case Study
    if scenario_hits >= 1 or (clinical_hits >= 1 and complex_hits >= 1):
        policy = ResponsePolicy(
            level="complex",
            max_tokens=1500,
            top_n=6,
            style_instruction=(
                "Tier 4 Response - Complex Case Strategy. Write a flowing consultant's note. DO NOT use rigid bold headers. "
                "Start with clinical interpretation, stratify risk and probabilities, explicitly highlight red flags naturally in the text, "
                "and conclude with clear, actionable management steps and monitoring guidance."
            ),
        )
        return {"type": "clinical_scenario", "response_mode": "detailed", "policy": policy}

    # 2. Detailed Treatment/Diagnostic Guidance
    if clinical_hits >= 1 or analytical_hits >= 2:
        policy = ResponsePolicy(
            level="complex",
            max_tokens=1200,
            top_n=5,
            style_instruction=(
                "Tier 3 Response - Structured Clinical Breakdown. Write a fluid consultant's note. DO NOT use rigid bold headers. "
                "Provide clinical context, prioritize common considerations first, mention contraindications where relevant, "
                "and offer practical, evidence-based management guidance."
            ),
        )
        return {"type": "clinical_guidance", "response_mode": "detailed", "policy": policy}

    # 3. Simple Fact / Lookup
    # Short query looking for specific item (dose, definition)
    if (length < 100 and num_questions <= 1 and clinical_hits == 0 and complex_hits == 0) or simple_hits >= 1:
        policy = ResponsePolicy(
            level="simple",
            max_tokens=300,
            top_n=3,
            style_instruction=(
                "Tier 1 Response - Simple Fact. Provide a concise, clear, clinically useful explanation in a few sentences. "
                "Answer EXACTLY what is asked and nothing more. DO NOT summarize tangential context (e.g., treatments, complications) if not explicitly requested. "
                "DO NOT over-medicalize or introduce rare disease associations. DO NOT use rigid headers."
            ),
        )
        return {"type": "short_answer", "response_mode": "short", "policy": policy}

    # 4. Medium Explanation (Default fall-through for moderate queries)
    policy = ResponsePolicy(
        level="analytical",
        max_tokens=800,
        top_n=4,
        style_instruction=(
            "Tier 2 Response - Management/Guidance. Write a flowing clinical explanation. DO NOT use rigid bold headers. "
            "Bridge pathophysiological or guideline theory with practical bedside application. "
            "Suggest investigations rationally and sound confident and precise."
        ),
    )
    return {"type": "medium_explanation", "response_mode": "medium", "policy": policy}


def select_response_policy(query: str) -> ResponsePolicy:
    """Backward-compatible API: returns the policy only."""
    return classify_query(query)["policy"]
