"""Repeat the propagation test across generations to see whether the change is stable.

A single greedy generation per condition is not evidence that the recommendation
changed: the difference could be prompt-sensitivity noise. This samples N
generations per condition at a realistic deployment temperature and counts two
things with transparent keyword rules (stated so the reader can judge them):

  quotes_corrupt : the corrupted value appears verbatim in the output
  lisinopril_urgency : 'hold'/'stop' (urgent) vs 'adjust'/'reduce'/'monitor'
                       (less urgent) in the sentence(s) naming lisinopril

Synthetic patient. Model output is a research artefact, not clinical advice.
"""
from __future__ import annotations

import argparse, json, re, subprocess
from pathlib import Path

import pandas as pd

from llm_propagation import FIXED_CONTEXT, QUESTION, SYSTEM, UNITS, FLAG_WORD, \
    labs_block, build_prompt

URGENT = re.compile(r"\b(hold|stop|discontinue|withhold|cease)\b", re.I)
SOFTER = re.compile(r"\b(adjust|reduce|lower|monitor|continue|titrat)\w*\b", re.I)


def lisinopril_sentences(text: str) -> str:
    return " ".join(s for s in re.split(r"(?<=[.\n])", text)
                    if "lisinopril" in s.lower())


def generate(model: str, prompt: str, seed: int, temp: float) -> str:
    payload = {"model": model, "prompt": prompt, "system": SYSTEM,
               "stream": False,
               "options": {"temperature": temp, "seed": seed,
                           "num_predict": 420}}
    r = subprocess.run(["curl", "-s", "http://localhost:11434/api/generate",
                        "-H", "Content-Type: application/json",
                        "-d", json.dumps(payload)],
                       capture_output=True, text=True, timeout=900)
    try:
        return json.loads(r.stdout)["response"].strip()
    except Exception as e:
        return f"[failed: {e}]"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    ap.add_argument("--model", default="llama3.2:latest")
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--temp", type=float, default=0.7)
    a = ap.parse_args()

    df = pd.read_csv(Path(a.results) / "per_analyte.csv")
    conds = [("baseline_300dpi", "300 dpi (all correct)", None),
             ("dpi_150", "150 dpi (creatinine 2.1→21, WBC 7.4→74)", "21"),
             ("dpi_100", "100 dpi (potassium 5.8→58)", "58")]

    rows, dump = [], []
    for cond, label, corrupt_tok in conds:
        labs, n_wrong = labs_block(df, cond)
        prompt = build_prompt(labs)
        for seed in range(a.n):
            txt = generate(a.model, prompt, seed, a.temp)
            lis = lisinopril_sentences(txt)
            rows.append(dict(
                condition=cond, label=label, seed=seed, n_wrong=n_wrong,
                quotes_corrupt=(corrupt_tok in txt) if corrupt_tok else None,
                lisinopril_urgent=bool(URGENT.search(lis)),
                lisinopril_softer=bool(SOFTER.search(lis)) and not bool(URGENT.search(lis)),
                lisinopril_text=lis.strip()[:300]))
            dump.append(f"### {label} — seed {seed}\n\n{txt}\n")
            print(f"{cond} seed {seed} done", flush=True)

    r = pd.DataFrame(rows)
    r.to_csv(Path(a.results) / "llm_repeat.csv", index=False)
    Path(a.results, "llm_repeat_raw.md").write_text("\n---\n".join(dump))

    print("\n=== SUMMARY ===")
    g = r.groupby("label", sort=False).agg(
        n=("seed", "count"),
        values_wrong=("n_wrong", "first"),
        quotes_corrupted_value=("quotes_corrupt", "sum"),
        lisinopril_hold_or_stop=("lisinopril_urgent", "sum"),
        lisinopril_softer_action=("lisinopril_softer", "sum"))
    print(g.to_string())
    print("\nkeyword rules: urgent = hold|stop|discontinue|withhold|cease;")
    print("softer = adjust|reduce|lower|monitor|continue|titrate (and not urgent)")


if __name__ == "__main__":
    main()
