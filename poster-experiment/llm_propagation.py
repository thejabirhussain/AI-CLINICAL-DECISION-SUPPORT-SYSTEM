"""Does a corrupted laboratory value change the generated clinical recommendation?

Closes the last link of the pipeline. Takes the laboratory values actually
extracted at three image-quality levels, formats them the way the system's
SessionManager.format_context_for_prompt does, builds the prompt the way
core/prompts.build_rag_prompt does, and generates with a local model.

The knowledge-base block is deliberately empty (the system's documented
"no relevant entries" path) so that the ONLY thing differing between runs is
the laboratory values. Everything else - demographics, history, medications,
allergies, the question - is held fixed.

Synthetic patient throughout. Model output is a research artefact
demonstrating error propagation. It is not clinical advice.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pandas as pd

FIXED_CONTEXT = """\
Patient: synthetic demonstration record (not a real person)
Age / Sex: 64-year-old female
Active problems: type 2 diabetes mellitus (12 years, poorly controlled);
  chronic kidney disease stage 4 (baseline creatinine 1.8); essential
  hypertension; iron deficiency anaemia; hyperlipidaemia; osteoarthritis
Allergies: sulfa drugs (rash); penicillin (hives)
Current medications:
  - Metformin 1000 mg PO twice daily
  - Lisinopril 20 mg PO daily
  - Amlodipine 10 mg PO daily
  - Atorvastatin 40 mg PO daily
  - Ibuprofen 400 mg PO three times daily PRN
  - Ferrous sulfate 325 mg PO daily
Vitals: BP 158/92 mmHg, HR 88, SpO2 96% RA, weight 82 kg, BMI 31"""

QUESTION = ("Review this patient's current medications against the laboratory "
            "results. Which drugs should be stopped, held or dose-adjusted, "
            "and why? Be specific and concise.")

SYSTEM = ("You are an experienced, evidence-informed Clinical Decision Support "
          "Assistant.\nYou must provide practical, bedside-relevant guidance and "
          "never invent medical facts.\nIf the knowledge base does not cover "
          "something, say it is based on general clinical knowledge.")

UNITS = {
    "Glucose (fasting)": "mg/dL", "HbA1c": "%", "Hemoglobin": "g/dL",
    "Ferritin": "ng/mL", "WBC": "10^9/L", "Platelets": "10^9/L",
    "Sodium": "mEq/L", "Potassium": "mEq/L", "BUN": "mg/dL",
    "Creatinine": "mg/dL", "eGFR": "mL/min/1.73m2", "Troponin I": "ng/mL",
    "LDL cholesterol": "mg/dL",
}
FLAG_WORD = {"H": "FLAG: High", "L": "FLAG: Low", "C": "FLAG: Critical", "": ""}


def labs_block(df: pd.DataFrame, condition: str, seed: int = 0) -> tuple[str, int]:
    """Format the labs the pipeline would have at this image quality."""
    rows = df[(df.condition == condition) & (df.seed == seed)]
    lines, n_wrong = [], 0
    for _, r in rows.iterrows():
        if pd.isna(r.extracted):
            lines.append(f"  {r.analyte}: NOT READ")
            continue
        v = r.extracted
        v_s = f"{v:g}"
        flag = FLAG_WORD.get(str(r.extracted_flag) if pd.notna(r.extracted_flag)
                             else "", "")
        lines.append(f"  {r.analyte}: {v_s} {UNITS[r.analyte]} {flag}".rstrip())
        if abs(v - r.truth) > 1e-9:
            n_wrong += 1
    return "\n".join(lines), n_wrong


def build_prompt(labs: str) -> str:
    """Mirrors core/prompts.build_rag_prompt, empty knowledge-base path."""
    return f"""
You are an advanced, evidence-based Clinical Decision Support Engine.

=== UPLOADED PATIENT DATA / CONTEXT ===
{FIXED_CONTEXT}

Laboratory results:
{labs}

=== MEDICAL KNOWLEDGE BASE CONTEXT (GUIDELINES) ===
No relevant knowledge base entries were found for this question. Do not cite any
references; state that the answer is based on general clinical knowledge.

=== CLINICIAN QUESTION ===
{QUESTION}

CRITICAL REASONING INSTRUCTIONS:
1. Act as a highly trained physician consultant. You are answering a colleague.
2. If PATIENT DATA is provided, you MUST analyze it specifically. Pay close
   attention to any tags labeled (FLAG: High/Low/Critical).
3. Quote patient values EXACTLY as listed (test name, value, unit and flag);
   never swap values between tests.
4. For medication questions, check EACH current medication against kidney
   function (eGFR/creatinine), potassium, the other medications and the
   allergies, and state a concrete recommendation for each drug that is a
   concern.
Answer in under 220 words.
"""


def generate(model: str, prompt: str) -> str:
    payload = {
        "model": model, "prompt": prompt, "system": SYSTEM, "stream": False,
        "options": {"temperature": 0.0, "seed": 0, "num_predict": 420},
    }
    r = subprocess.run(
        ["curl", "-s", "http://localhost:11434/api/generate",
         "-H", "Content-Type: application/json", "-d", json.dumps(payload)],
        capture_output=True, text=True, timeout=600,
    )
    try:
        return json.loads(r.stdout)["response"].strip()
    except Exception as e:
        return f"[generation failed: {e}] {r.stdout[:300]} {r.stderr[:300]}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    ap.add_argument("--model", default="llama3.2:latest")
    ap.add_argument("--out", default="results/llm_propagation.md")
    a = ap.parse_args()

    df = pd.read_csv(Path(a.results) / "per_analyte.csv")
    conditions = [("baseline_300dpi", "300 dpi — all 13 values read correctly"),
                  ("dpi_150", "150 dpi — 2 of 13 values wrong"),
                  ("dpi_100", "100 dpi — 4 of 13 values wrong")]

    out = ["# Does a corrupted value change the recommendation?",
           "",
           f"Model: `{a.model}`, temperature 0, seed 0. Knowledge base empty, so "
           "the laboratory values are the only thing that differs between runs. "
           "Synthetic patient. **Model output shown as a research artefact "
           "demonstrating error propagation — not clinical advice.**", ""]

    for cond, label in conditions:
        labs, n_wrong = labs_block(df, cond)
        print(f"generating: {cond} ({n_wrong} wrong)", flush=True)
        ans = generate(a.model, build_prompt(labs))
        out += [f"## {label}", "",
                f"Values wrong at this quality: **{n_wrong} / 13**", "",
                "<details><summary>Laboratory values given to the model</summary>",
                "", "```", labs, "```", "</details>", "",
                "**Generated recommendation:**", "", "> " +
                ans.replace("\n", "\n> "), "", "---", ""]

    Path(a.out).write_text("\n".join(out))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
