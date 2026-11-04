"""Numeric verification layer: decide, per extracted value, whether to accept it or route it to human review.

The presented study showed the existing plausibility check catches only 9 of 28 corruptions, and the failure analysis
here shows why a row-local check cannot work: at low resolution Tesseract drops the decimal point in the printed
reference range too ("0.6-1.2" -> "06-12"), so value and range shift together. Every check below therefore uses
knowledge from outside the OCR text, or a second independent reading:

  plausible   value inside the study's "possible in a living human" envelope (the existing check, kept as baseline)
  precision   analytes conventionally reported with a decimal point (K, creatinine, Hb, HbA1c, WBC, troponin, ...)
              must carry one; an integer token for them is the signature of a dropped decimal point
  magnitude   value far outside the analyte's reference window while value / 10^k lands back inside it; only for
              analytes whose physiological maximum is < 50x the upper reference limit, so true extremes are not flagged
  structure   the extracted number is not the start of a reference range (unreadable result cell)
  agreement   a second engine with a different model reads the same value

Nothing is auto-corrected: a failed check means "show this value to a human", never "replace it".

    .venv/bin/python verify.py --primary labnum_rescale --secondary rapidocr
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from common import BY_NAME, study

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
KEY = ["testset", "doc", "condition", "seed", "analyte"]


def raw_token(line: str, value: float) -> str | None:
    for tok in str(line).split():
        m = study.NUM_TOKEN.match(tok)
        if m and abs(float(m.group(1).replace(",", ".")) - value) < 1e-9:
            return m.group(1)
    return None


def check_precision(analyte: str, line: str, value: float) -> bool:
    a = BY_NAME[analyte]
    if a.decimals == 0:
        return True
    tok = raw_token(line, value)
    return tok is None or "." in tok or "," in tok


def check_magnitude(analyte: str, value: float) -> bool:
    a = BY_NAME[analyte]
    lo, hi = a.lo, a.hi
    if a.plaus[1] >= 50 * hi:
        return True               # wide dynamic range (troponin, ferritin, CRP, ALT): a true extreme looks like a shift
    # High side only: OCR loses faint decimal points (x10, x100) but almost never invents one, and genuine extreme
    # lows (lactate 0.1, eGFR 3) are common in sick patients.
    window = (lo / 4, hi * 4)
    if value <= window[1]:
        return True
    for k in (1, 2, 3):
        if window[0] <= value / 10 ** k <= window[1]:
            return False          # a decimal shift explains the value better than biology does
    return True


RANGE_AFTER = re.compile(r"^\s*(?:[-–=~]\s*|to\s+)\d")


def check_structure(line: str, value: float) -> bool:
    """When the result cell is unreadable the row parser falls through to the reference range ("0.8 - 1.2") and
    returns its lower bound. A number directly followed by a range separator and another number is a range."""
    s = str(line)
    for m in re.finditer(r"[-+]?\d+(?:[.,]\d+)?", s):
        if abs(float(m.group().replace(",", ".")) - value) < 1e-9:
            return not RANGE_AFTER.match(s[m.end():])
    return True


def check_plausible(analyte: str, value: float) -> bool:
    lo, hi = BY_NAME[analyte].plaus
    return lo <= value <= hi


CHECKS = {
    "plausible": lambda r: check_plausible(r.analyte, r.extracted),
    "precision": lambda r: check_precision(r.analyte, r.line, r.extracted),
    "magnitude": lambda r: check_magnitude(r.analyte, r.extracted),
    "structure": lambda r: check_structure(r.line, r.extracted),
    "agreement": lambda r: pd.notna(r.extracted_2) and abs(r.extracted_2 - r.extracted) < 1e-9,
}
POLICIES = {
    "none": [],
    "plausibility (existing)": ["plausible"],
    "+ precision": ["plausible", "precision"],
    "+ precision + magnitude": ["plausible", "precision", "magnitude"],
    "+ structure": ["plausible", "precision", "magnitude", "structure"],
    "+ cross-engine agreement": ["plausible", "precision", "magnitude", "structure", "agreement"],
}


def load(engine: str, testset: str) -> pd.DataFrame:
    return pd.read_csv(RES / f"rows_{engine.replace(':', '-')}_{testset}.csv")


def evaluate(primary: str, secondary: str | None, testset: str) -> pd.DataFrame:
    df = load(primary, testset)
    if secondary:
        s = load(secondary, testset)[KEY + ["extracted"]].rename(columns={"extracted": "extracted_2"})
        df = df.merge(s, on=KEY, how="left")
    got = df[df.status != "missing"].copy()            # missing values are already visible, never silent
    for name, fn in CHECKS.items():
        if name == "agreement" and not secondary:
            continue
        got[name] = got.apply(fn, axis=1)
    out = []
    for pol, checks in POLICIES.items():
        if "agreement" in checks and not secondary:
            continue
        flagged = ~got[checks].all(axis=1) if checks else pd.Series(False, index=got.index)
        wrong = got.status == "corrupted"
        silent = wrong & (got.silent == True)  # noqa: E712  (column holds NaN for non-corrupted rows)
        accepted_wrong = wrong & ~flagged
        out.append({
            "testset": testset, "primary": primary, "secondary": secondary or "", "policy": pol,
            "values": len(df), "extracted": len(got), "corrupted": int(wrong.sum()),
            "caught": int((wrong & flagged).sum()),
            "recall_%": round(100 * (wrong & flagged).sum() / max(1, wrong.sum()), 1),
            "silent": int(silent.sum()), "silent_caught": int((silent & flagged).sum()),
            "false_alarm_%": round(100 * (~wrong & flagged).sum() / max(1, (~wrong).sum()), 1),
            "review_rate_%": round(100 * flagged.mean(), 1),
            "undetected_wrong": int(accepted_wrong.sum()),
            "undetected_per_1000_accepted": round(1000 * accepted_wrong.sum() / max(1, (~flagged).sum()), 1),
        })
    return pd.DataFrame(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--primary", required=True)
    ap.add_argument("--secondary", default="")
    ap.add_argument("--testset", default="A,B")
    args = ap.parse_args()
    res = pd.concat([evaluate(args.primary, args.secondary or None, t) for t in args.testset.split(",")])
    pd.set_option("display.width", 250)
    print(res.drop(columns=["primary", "secondary"]).to_string(index=False))
    tag = f"{args.primary}__{args.secondary or 'single'}".replace(":", "-")
    res.to_csv(RES / f"verify_{tag}.csv", index=False)


if __name__ == "__main__":
    main()
