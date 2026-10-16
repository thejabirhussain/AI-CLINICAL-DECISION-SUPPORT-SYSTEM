"""
Controlled fault injection in a document-image -> OCR -> structured-extraction
clinical pipeline.

Measures how image degradation propagates into extracted laboratory values and
into the abnormal-value flags that a downstream LLM is instructed to quote.

Ground truth comes from demo/make_demo_report.py, which renders the synthetic
report from a hardcoded list of 13 analytes. The report is synthetic and
banner-labelled "NOT A REAL PERSON": no patient data is used anywhere.

Requires: pymupdf, pillow, numpy, pandas  +  the `tesseract` binary on PATH.

Usage:
    python ocr_fault_injection.py --pdf path/to/patient_report_maria_alvarez.pdf \
                                  --outdir results/
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd
import pymupdf
from PIL import Image, ImageFilter

# ---------------------------------------------------------------------------
# Ground truth — copied verbatim from demo/make_demo_report.py
# ---------------------------------------------------------------------------
# (name, value, unit, document_reference_range, document_flag)
LABS_TRUTH = [
    ("Glucose (fasting)", 248.0, "mg/dL", "70 - 99", "H"),
    ("HbA1c", 9.2, "%", "4.0 - 5.6", "H"),
    ("Hemoglobin", 9.4, "g/dL", "12.0 - 15.5", "L"),
    ("Ferritin", 9.0, "ng/mL", "15 - 200", "L"),
    ("WBC", 7.4, "10^9/L", "4.5 - 11.0", ""),
    ("Platelets", 262.0, "10^9/L", "150 - 450", ""),
    ("Sodium", 133.0, "mEq/L", "135 - 145", "L"),
    ("Potassium", 5.8, "mEq/L", "3.5 - 5.0", "H"),
    ("BUN", 42.0, "mg/dL", "7 - 20", "H"),
    ("Creatinine", 2.1, "mg/dL", "0.6 - 1.2", "H"),
    ("eGFR", 26.0, "mL/min/1.73m2", "> 60", "L"),
    ("Troponin I", 0.07, "ng/mL", "0.00 - 0.04", "H"),
    ("LDL cholesterol", 142.0, "mg/dL", "< 100", "H"),
]

# ---------------------------------------------------------------------------
# The system's own flagging logic, transcribed from
# ai/app/ingestion/clinical_parser.py:26-50 and :126-170.
# Transcribed, not imported, so this script runs without the FastAPI app.
# NOTE: these are the ranges the system hardcodes. They are NOT the ranges
# printed on the document, and they are not age- or sex-aware.
# ---------------------------------------------------------------------------
SYSTEM_RANGES = {
    "glucose":     (70, 99),
    "hba1c":       (4.0, 5.6),
    "hemoglobin":  (12.0, 17.5),   # sex-independent in the original code
    "wbc":         (4.5, 11.0),
    "platelets":   (150, 450),
    "sodium":      (135, 145),
    "potassium":   (3.5, 5.0),
    "creatinine":  (0.6, 1.2),
    "bun":         (7, 20),
    "egfr":        (60, 200),
    "ferritin":    (15, 200),
    "ldl":         (0, 99),
    "troponin":    (0.0, 0.04),
}

# Conservative "possible in a living human" envelopes. These are MY construction
# for this study, deliberately generous, and are NOT a clinical standard. They
# exist only to ask: would a plausibility check have caught this corruption?
PLAUSIBLE = {
    "glucose":     (10, 1500),
    "hba1c":       (2, 20),
    "hemoglobin":  (2, 25),
    "wbc":         (0.1, 500),
    "platelets":   (1, 2000),
    "sodium":      (90, 190),
    "potassium":   (1.0, 10.0),
    "creatinine":  (0.1, 30),
    "bun":         (1, 300),
    "egfr":        (0, 200),
    "ferritin":    (0.1, 10000),
    "ldl":         (5, 600),
    "troponin":    (0.0, 100),
}

RANGE_KEY = {
    "Glucose (fasting)": "glucose", "HbA1c": "hba1c", "Hemoglobin": "hemoglobin",
    "Ferritin": "ferritin", "WBC": "wbc", "Platelets": "platelets",
    "Sodium": "sodium", "Potassium": "potassium", "BUN": "bun",
    "Creatinine": "creatinine", "eGFR": "egfr", "Troponin I": "troponin",
    "LDL cholesterol": "ldl",
}


def system_flag(key: str, value: float) -> str:
    """Reproduce clinical_parser._detect_abnormal_labs for one analyte."""
    lo, hi = SYSTEM_RANGES[key]
    if value < lo:
        return "L"
    if value > hi:
        return "C" if key == "troponin" else "H"   # troponin gets Critical
    return ""


def truth_flag_under_system(key: str, value: float) -> str:
    return system_flag(key, value)


# ---------------------------------------------------------------------------
# Degradation
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Condition:
    name: str
    family: str
    level: float
    dpi: int = 300
    blur: float = 0.0
    jpeg: int = 0          # 0 = no JPEG round trip
    rotate: float = 0.0
    noise: float = 0.0
    seed: int = 0


def build_conditions() -> list[Condition]:
    c: list[Condition] = [Condition("baseline_300dpi", "baseline", 0, dpi=300)]
    for d in (200, 150, 120, 100, 85, 72):
        c.append(Condition(f"dpi_{d}", "resolution", d, dpi=d))
    for s in (0.5, 1.0, 1.5, 2.0, 3.0):
        c.append(Condition(f"blur_{s}", "blur", s, blur=s))
    for q in (90, 70, 50, 30, 15):
        c.append(Condition(f"jpeg_q{q}", "jpeg", q, jpeg=q))
    for r in (0.25, 0.5, 1.0, 2.0, 5.0):
        c.append(Condition(f"rotate_{r}", "rotation", r, rotate=r))
    for n in (5, 10, 20, 30, 50):
        for seed in range(5):                       # 5 seeds -> real error bars
            c.append(Condition(f"noise_{n}", "noise", n, noise=n, seed=seed))
    # realistic composites
    c.append(Condition("scan_good", "composite", 1, dpi=300, jpeg=90))
    c.append(Condition("scan_office", "composite", 2, dpi=200, jpeg=75, noise=5))
    for seed in range(5):
        c.append(Condition("photo_phone", "composite", 3, dpi=150, blur=1.0,
                           jpeg=50, rotate=1.0, noise=10, seed=seed))
    for seed in range(5):
        c.append(Condition("fax_poor", "composite", 4, dpi=100, blur=1.5,
                           noise=20, seed=seed))
    for seed in range(5):
        c.append(Condition("photo_bad", "composite", 5, dpi=100, blur=2.0,
                           jpeg=25, rotate=2.0, noise=25, seed=seed))
    return c


def render(doc, page_index: int, cond: Condition, workdir: Path) -> Path:
    pix = doc[page_index].get_pixmap(dpi=cond.dpi)
    raw = workdir / f"{cond.name}_s{cond.seed}_p{page_index}_raw.png"
    pix.save(raw)
    im = Image.open(raw).convert("L")

    if cond.rotate:
        im = im.rotate(cond.rotate, resample=Image.BICUBIC,
                       expand=True, fillcolor=255)
    if cond.blur:
        im = im.filter(ImageFilter.GaussianBlur(cond.blur))
    if cond.noise:
        rng = np.random.default_rng(cond.seed)
        a = np.asarray(im, dtype=np.float32)
        a = a + rng.normal(0.0, cond.noise, a.shape)
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    if cond.jpeg:
        tmp = workdir / f"{cond.name}_s{cond.seed}_p{page_index}.jpg"
        im.save(tmp, "JPEG", quality=cond.jpeg)
        im = Image.open(tmp).convert("L")

    out = workdir / f"{cond.name}_s{cond.seed}_p{page_index}.png"
    im.save(out)
    raw.unlink(missing_ok=True)
    return out


def degrade_and_ocr(doc, pages: list[int], cond: Condition,
                    workdir: Path, psm: int) -> str:
    """Degrade and OCR every page the laboratory table spans, then concatenate.

    The table in this report crosses a page break (Creatinine ends page 1,
    eGFR begins page 2), so a single-page render silently loses three analytes.
    """
    parts = []
    for pi in pages:
        png = render(doc, pi, cond, workdir)
        parts.append(ocr(png, psm))
        png.unlink(missing_ok=True)
    return "\n".join(parts)


def ocr(png: Path, psm: int = 6) -> str:
    r = subprocess.run(
        ["tesseract", str(png), "stdout", "--psm", str(psm),
         "-c", "preserve_interword_spaces=1"],
        capture_output=True, text=True,
    )
    return r.stdout


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------
NUM_TOKEN = re.compile(r"^[^\d\-+]*([-+]?\d+(?:[.,]\d+)?)")


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _as_number(token: str) -> float | None:
    """Parse a leading number out of a whitespace token ('4.5-' -> 4.5)."""
    m = NUM_TOKEN.match(token)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def find_lab_value(text: str, lab_name: str) -> tuple[float | None, str, str]:
    """Locate the table row for `lab_name` and return its Result field.

    Tokenises each line, fuzzy-matches the label against the first 1-4 tokens,
    then takes the first numeric token after the label. Candidate lines must
    contain at least one number after the label; rows carrying two or more
    numbers (Result plus Reference range) are preferred, which keeps prose
    sentences such as "Potassium was elevated on admission" from matching.

    Returns (value_or_None, matched_line, failure_reason).
    """
    target = norm(lab_name)
    best = None          # (has_two_nums, ratio, value, line)
    label_seen = False

    for line in text.splitlines():
        toks = line.split()
        if not toks:
            continue
        for k in range(1, min(4, len(toks)) + 1):
            cand = norm("".join(toks[:k]))
            if not cand:
                continue
            ratio = difflib.SequenceMatcher(None, target, cand).ratio()
            if ratio < 0.62:
                continue
            label_seen = True
            rest = toks[k:]
            nums = [v for v in (_as_number(t) for t in rest) if v is not None]
            if not nums:
                continue
            key = (len(nums) >= 2, ratio)
            if best is None or key > best[0]:
                best = (key, nums[0], line)

    if best is None:
        return None, "", ("label_not_found" if not label_seen
                          else "label_found_no_value")
    return best[1], best[2], ""


WS = re.compile(r"\s+")


def flatten(t: str) -> str:
    """Collapse all whitespace runs to one space.

    PyMuPDF's get_text() emits one table cell per line while Tesseract emits
    one table ROW per line, so comparing the two raw gives a ~30% error rate
    on a render whose every value is read correctly. Normalising whitespace
    makes the measure reflect characters rather than layout.
    """
    return WS.sub(" ", t).strip()


def cer(ref: str, hyp: str) -> float:
    """Character error rate on whitespace-normalised text."""
    a, b = flatten(ref), flatten(hyp)
    if not a:
        return 0.0 if not b else 1.0
    try:
        from rapidfuzz.distance import Levenshtein
        return Levenshtein.distance(a, b) / len(a)
    except ImportError:
        pass
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1,
                         prev[j - 1] + (ca != cb))
        prev = cur
    return prev[-1] / len(a)


def decimal_shift(truth: float, got: float) -> int | None:
    """If got == truth * 10**k for a small non-zero integer k, return k."""
    if truth == 0 or got == 0:
        return None
    for k in (-3, -2, -1, 1, 2, 3):
        if abs(got - truth * (10 ** k)) < 1e-6 * max(1.0, abs(truth * 10 ** k)):
            return k
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--outdir", default="results")
    ap.add_argument("--psm", type=int, default=6)
    ap.add_argument("--skip-cer", action="store_true",
                    help="skip character error rate (the slow metric)")
    args = ap.parse_args()

    out = Path(args.outdir)
    work = out / "images"
    work.mkdir(parents=True, exist_ok=True)
    dumps = out / "ocr"
    dumps.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(args.pdf)
    pages = list(range(doc.page_count))
    ref_text = "\n".join(doc[i].get_text() for i in pages)
    print(f"{doc.page_count} page(s); digital reference text = "
          f"{len(ref_text)} chars", flush=True)

    rows, per_cond = [], []
    conds = build_conditions()
    for n, cond in enumerate(conds, 1):
        text = degrade_and_ocr(doc, pages, cond, work, args.psm)
        (dumps / f"{cond.name}_s{cond.seed}.txt").write_text(text)
        c = None if args.skip_cer else cer(ref_text, text)

        n_correct = n_corrupt = n_missing = n_silent = n_impossible = n_decshift = 0
        for name, tval, unit, docrange, docflag in LABS_TRUTH:
            key = RANGE_KEY[name]
            got, line, why = find_lab_value(text, name)
            tflag = truth_flag_under_system(key, tval)

            if got is None:
                status, gflag, ds = why, None, None
                n_missing += 1
            elif abs(got - tval) < 1e-9:
                status, gflag, ds = "correct", tflag, None
                n_correct += 1
            else:
                status = "corrupted"
                gflag = system_flag(key, got)
                ds = decimal_shift(tval, got)
                n_corrupt += 1
                if gflag == tflag:
                    n_silent += 1          # alarm state unchanged -> invisible
                lo, hi = PLAUSIBLE[key]
                if not (lo <= got <= hi):
                    n_impossible += 1      # nothing in the pipeline rejects this
                if ds:
                    n_decshift += 1

            rows.append(dict(
                condition=cond.name, family=cond.family, level=cond.level,
                seed=cond.seed, dpi=cond.dpi, blur=cond.blur, jpeg=cond.jpeg,
                rotate=cond.rotate, noise=cond.noise,
                analyte=name, truth=tval, extracted=got, status=status,
                truth_flag=tflag, extracted_flag=gflag,
                decimal_shift=ds, ocr_line=line.strip()[:120],
            ))

        per_cond.append(dict(
            condition=cond.name, family=cond.family, level=cond.level,
            seed=cond.seed, dpi=cond.dpi, cer=c,
            n_correct=n_correct, n_corrupted=n_corrupt, n_missing=n_missing,
            n_silent_corruption=n_silent, n_impossible=n_impossible,
            n_decimal_shift=n_decshift,
            value_accuracy=n_correct / len(LABS_TRUTH),
        ))

        if cond.name == "baseline_300dpi" and n_correct < len(LABS_TRUTH):
            bad = [r["analyte"] for r in rows[-len(LABS_TRUTH):]
                   if r["status"] != "correct"]
            print("\n*** CALIBRATION FAILURE ***", file=sys.stderr)
            print("The extractor does not recover all 13 analytes from the "
                  "undegraded 300 dpi render.", file=sys.stderr)
            print("Any degradation result would measure extractor bugs, not "
                  "OCR behaviour.", file=sys.stderr)
            print("Failing analytes:", bad, file=sys.stderr)
            for r in rows[-len(LABS_TRUTH):]:
                if r["status"] != "correct":
                    print(f"  {r['analyte']:<20s} truth={r['truth']} "
                          f"got={r['extracted']} status={r['status']} "
                          f"line={r['ocr_line']!r}", file=sys.stderr)
            return 2

        print(f"[{n:3d}/{len(conds)}] {cond.name:<18s} seed={cond.seed} "
              f"cer={'-' if c is None else f'{c:.3f}'} "
              f"correct={n_correct:2d}/13 corrupt={n_corrupt:2d} "
              f"missing={n_missing:2d} silent={n_silent:2d} "
              f"impossible={n_impossible:2d}", flush=True)

    df = pd.DataFrame(rows)
    dc = pd.DataFrame(per_cond)
    df.to_csv(out / "per_analyte.csv", index=False)
    dc.to_csv(out / "per_condition.csv", index=False)

    summary = (dc.groupby(["family", "condition"], sort=False)
                 .agg(dpi=("dpi", "first"),
                      level=("level", "first"),
                      runs=("seed", "count"),
                      cer_mean=("cer", "mean"),
                      value_acc_mean=("value_accuracy", "mean"),
                      value_acc_min=("value_accuracy", "min"),
                      corrupted=("n_corrupted", "mean"),
                      missing=("n_missing", "mean"),
                      silent=("n_silent_corruption", "mean"),
                      impossible=("n_impossible", "mean"),
                      dec_shift=("n_decimal_shift", "mean"))
                 .reset_index())
    summary.to_csv(out / "summary.csv", index=False)

    print("\n" + "=" * 100)
    print(summary.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print("=" * 100)

    corr = df[df.status == "corrupted"]
    print(f"\nTotal analyte observations : {len(df)}")
    print(f"correct   : {(df.status=='correct').sum()}")
    print(f"corrupted : {len(corr)}")
    print(f"label_not_found      : {(df.status=='label_not_found').sum()}")
    print(f"label_found_no_value : {(df.status=='label_found_no_value').sum()}")
    if len(corr):
        silent = corr[corr.truth_flag == corr.extracted_flag]
        print(f"\nOf {len(corr)} corrupted values, {len(silent)} "
              f"({100*len(silent)/len(corr):.1f}%) left the flag unchanged "
              f"-> invisible to the flagging layer")
        ds = corr[corr.decimal_shift.notna()]
        print(f"{len(ds)} corruptions were pure decimal-place shifts")
        print("\nmost corrupted analytes:")
        print(corr.analyte.value_counts().head(8).to_string())
        print("\nexamples of silent corruption:")
        cols = ["condition", "analyte", "truth", "extracted",
                "truth_flag", "extracted_flag", "decimal_shift"]
        print(silent[cols].drop_duplicates(subset=["analyte", "extracted"])
              .head(12).to_string(index=False))
    (out / "metadata.json").write_text(json.dumps(dict(
        pdf=args.pdf, pages=pages, psm=args.psm,
        n_conditions=len(conds), n_analytes=len(LABS_TRUTH),
        tesseract=subprocess.run(["tesseract", "--version"],
                                 capture_output=True, text=True)
        .stdout.splitlines()[0],
    ), indent=2))
    print(f"\nwrote {out}/per_analyte.csv, per_condition.csv, summary.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
