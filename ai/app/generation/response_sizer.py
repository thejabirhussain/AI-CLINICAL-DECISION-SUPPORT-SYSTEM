from dataclasses import dataclass
import re


@dataclass
class ResponsePolicy:
    level: str
    max_tokens: int
    top_n: int
    style_instruction: str


_SIMPLE_CUES = {
    "what is", "define", "definition", "date", "deadline", "where", "when", "who",
    "url", "link", "phone", "number", "amount", "fee", "cost", "due", "rate",
}

_ANALYTICAL_CUES = {
    "how", "why", "explain", "steps", "calculate", "eligibility", "example",
    "examples", "impact", "benefit", "pros", "cons", "difference", "compare",
}

_COMPLEX_CUES = {
    "comprehensive", "detailed", "end-to-end", "guide", "strategy", "multiple parts",
    "multi part", "multi-part", "in-depth", "tradeoffs", "limitations", "edge cases",
}

# Domain-specific cues
_FORM_CUES = {
    "form ", "schedule ", "pub ", "publication ", "instructions", "line ", "box ",
}

_GUIDANCE_CUES = {
    "should i", "must i", "do i need", "can i", "compliance", "penalty", "penalties",
    "file", "filing", "report", "claim", "deduct", "deduction", "credit", "eligibility",
}

_SCENARIO_CUES = {
    "scenario", "case", "suppose", "assume", "if i", "if we", "what happens if",
}


def _count_cues(q: str, cues: set[str]) -> int:
    return sum(1 for c in cues if c in q)


def classify_query(query: str) -> dict:
    """Classify a query into a rich type and return an associated response policy.

    Returns a dict: {"type": <slug>, "response_mode": <short|medium|detailed>, "policy": ResponsePolicy}
    """
    q = query.strip().lower()

    length = len(q)
    num_questions = q.count("?")
    num_sentences = max(1, q.count(".") + q.count("?") + q.count("!"))

    simple_hits = _count_cues(q, _SIMPLE_CUES)
    analytical_hits = _count_cues(q, _ANALYTICAL_CUES)
    complex_hits = _count_cues(q, _COMPLEX_CUES)
    form_hits = _count_cues(q, _FORM_CUES)
    guidance_hits = _count_cues(q, _GUIDANCE_CUES)
    scenario_hits = _count_cues(q, _SCENARIO_CUES)

    list_like = bool(re.search(r"\b(?:list|enumerate|top|bullet|checklist)\b", q))
    step_like = bool(re.search(r"\b(?:step-by-step|step by step|steps)\b", q))
    multi_part = bool(re.search(r"\b(?:and|or)\b", q)) and num_questions >= 1

    # Scenario-based multi-step reasoning
    if scenario_hits >= 1 or (" vs " in q) or ("compare" in q and ("and" in q or " vs " in q)):
        policy = ResponsePolicy(
            level="complex",
            max_tokens=1400,
            top_n=5,
            style_instruction=(
                "Provide a structured scenario analysis with assumptions, steps, and outcomes. "
                "Use sections: Assumptions, Reasoning, Outcome, Caveats. Cite 3-5 sources."
            ),
        )
        return {"type": "scenario_analysis", "response_mode": "detailed", "policy": policy}

    # Tax guidance / deep analysis
    if guidance_hits >= 2 or (guidance_hits >= 1 and analytical_hits >= 1) or "guidance" in q:
        policy = ResponsePolicy(
            level="complex",
            max_tokens=1200,
            top_n=5,
            style_instruction=(
                "Provide compliance-oriented guidance with steps, eligibility, timing, and penalties. "
                "Use short sections and bullets. Cite 3-5 sources."
            ),
        )
        return {"type": "tax_guidance", "response_mode": "detailed", "policy": policy}

    # Form-specific breakdown
    if form_hits >= 1 and ("form" in q or "schedule" in q or "publication" in q or "instructions" in q):
        policy = ResponsePolicy(
            level="analytical",
            max_tokens=800,
            top_n=4,
            style_instruction=(
                "Provide a form-specific breakdown: purpose, who should file, key lines, common mistakes. "
                "Use bullets and cite 2-4 sources."
            ),
        )
        return {"type": "form_breakdown", "response_mode": "medium", "policy": policy}

    # Step-by-step reasoning
    if step_like and (analytical_hits >= 1 or guidance_hits >= 1):
        policy = ResponsePolicy(
            level="complex",
            max_tokens=1000,
            top_n=4,
            style_instruction=(
                "Provide a numbered step-by-step procedure with brief rationales per step. Cite 2-4 sources."
            ),
        )
        return {"type": "step_by_step", "response_mode": "detailed", "policy": policy}

    # Simple / Direct fact
    if (length < 80 and num_questions <= 1 and analytical_hits == 0 and complex_hits == 0) or simple_hits >= 1:
        policy = ResponsePolicy(
            level="simple",
            max_tokens=250,
            top_n=2,
            style_instruction=(
                "Answer briefly in 2-4 concise sentences or 3-5 bullets. "
                "Include only the essential fact(s) and one source section."
            ),
        )
        return {"type": "short_answer", "response_mode": "short", "policy": policy}

    # Medium explanation
    if (length < 240 and (analytical_hits >= 1 or num_sentences >= 2 or list_like)) and complex_hits == 0 and not multi_part:
        policy = ResponsePolicy(
            level="analytical",
            max_tokens=600,
            top_n=3,
            style_instruction=(
                "Provide a medium-length explanation in clear paragraphs and bullets. "
                "Aim for 5-8 sentences total. Include key caveats and cite 2-3 sources."
            ),
        )
        return {"type": "medium_explanation", "response_mode": "medium", "policy": policy}

    # Long / detailed
    policy = ResponsePolicy(
        level="complex",
        max_tokens=1200,
        top_n=5,
        style_instruction=(
            "Provide a thorough, structured answer with short sections and bullets. "
            "Cover sub-questions, edge cases, and steps. Aim for 10-16 sentences. "
            "Cite 3-5 sources."
        ),
    )
    return {"type": "long_detailed", "response_mode": "detailed", "policy": policy}


def select_response_policy(query: str) -> ResponsePolicy:
    """Backward-compatible API: returns the policy only."""
    return classify_query(query)["policy"]
