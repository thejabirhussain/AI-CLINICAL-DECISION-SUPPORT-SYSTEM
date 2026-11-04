"""Evaluate OCR engines on numeric extraction, not just characters.

Test A = the presented study's document under its 32 degradation conditions (64 runs).
Test B = 20 held-out synthetic reports in unseen fonts (Times, Courier) under 7 conditions.

Rendering, row parsing, CER, decimal-shift and "silent corruption" definitions come from
../poster-experiment/ocr_fault_injection.py, unchanged. Raw OCR text is cached under results/cache so the
verification layer (verify.py) can be scored without re-running OCR.

    .venv/bin/python evaluate.py --engine tess_fast --testset A
"""
from __future__ import annotations

import argparse
import json
import math
import tempfile
import time
from pathlib import Path

import pandas as pd
import pymupdf

import common
from common import study

HERE = Path(__file__).resolve().parent
CACHE = HERE / "results" / "cache"
MARIA = HERE.parent / "demo" / "patient_report_maria_alvarez.pdf"
TESTSET_B = HERE / "data" / "testset_b"
B_CONDITIONS = {("baseline_300dpi", 0), ("dpi_150", 0), ("dpi_120", 0), ("dpi_100", 0),
                ("scan_office", 0), ("photo_phone", 0), ("fax_poor", 0)}


def rescale_factor(png: Path) -> int:
    """Estimate scan dpi from page width (US letter, 8.5 in) and upscale to >= ~300 dpi before OCR."""
    from PIL import Image
    dpi = Image.open(png).width / 8.5
    return max(1, min(4, math.ceil(300 / dpi - 0.05)))


def run_engine(engine: str, png: Path, work: Path) -> str:
    if engine.endswith("_rescale"):
        f = rescale_factor(png)
        if f > 1:
            png = common.upscale(png, f, work / (png.stem + f"_x{f}.png"))
        engine = engine[: -len("_rescale")]
    if engine == "tess_fast":
        return common.tesseract(png)                                  # stock homebrew eng (tessdata_fast)
    if engine == "tess_best":
        return common.tesseract(png, "eng_best", common.MODELS)
    if engine.startswith("labnum"):
        return common.tesseract(png, engine, common.MODELS)            # our fine-tuned models (labnum, labnum2)
    if engine == "rapidocr":
        return common.rapidocr(png)
    if engine.startswith("vlm"):
        return common.ollama_vlm(png, engine.split(":", 1)[1] if ":" in engine else "qwen2.5vl:3b")
    raise ValueError(engine)


def documents(testset: str):
    if testset == "A":
        truth = []
        for name, v, unit, rng_, f in study.LABS_TRUTH:
            key = study.RANGE_KEY[name]
            lo, hi = study.SYSTEM_RANGES[key]
            truth.append({"name": name, "value": v, "lo": lo, "hi": hi, "plaus": list(study.PLAUSIBLE[key]),
                          "troponin": key == "troponin"})
        yield "maria", MARIA, [0, 1], truth
    else:
        for meta in sorted(TESTSET_B.glob("report_*.json")):
            m = json.loads(meta.read_text())
            yield meta.stem, TESTSET_B / m["pdf"], [0], m["analytes"]


def conditions(testset: str):
    conds = study.build_conditions()
    return conds if testset == "A" else [c for c in conds if (c.name, c.seed) in B_CONDITIONS]


def flag_of(a: dict, v: float) -> str:
    if v < a["lo"]:
        return "L"
    if v > a["hi"]:
        return "C" if a.get("troponin") else "H"
    return ""


def score(text: str, truth: list[dict]) -> list[dict]:
    rows = []
    for a in truth:
        got, line, why = study.find_lab_value(text, a["name"])
        tflag = flag_of(a, a["value"])
        r = {"analyte": a["name"], "truth": a["value"], "extracted": got, "line": line}
        if got is None:
            r.update(status="missing", truth_flag=tflag, extracted_flag=None)
        elif abs(got - a["value"]) < 1e-9:
            r.update(status="correct", truth_flag=tflag, extracted_flag=tflag)
        else:
            gflag = flag_of(a, got)
            lo, hi = a["plaus"]
            r.update(status="corrupted", truth_flag=tflag, extracted_flag=gflag,
                     silent=gflag == tflag,                      # alarm state unchanged -> invisible
                     flag_flip=gflag != tflag,                    # clinically significant: abnormality changed
                     implausible=not (lo <= got <= hi),
                     decimal_shift=study.decimal_shift(a["value"], got))
        rows.append(r)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--testset", choices=["A", "B"], required=True)
    ap.add_argument("--only", default="", help="comma-separated condition names to run (default: all)")
    ap.add_argument("--max-docs", type=int, default=0)
    args = ap.parse_args()
    only = set(filter(None, args.only.split(",")))

    cache = CACHE / args.engine / args.testset
    cache.mkdir(parents=True, exist_ok=True)
    rows, t0 = [], time.time()
    docs = list(documents(args.testset))
    if args.max_docs:
        docs = docs[: args.max_docs]
    for doc_id, pdf, pages, truth in docs:
        doc = pymupdf.open(pdf)
        ref_text = "\n".join(doc[p].get_text() for p in pages)
        for cond in conditions(args.testset):
            if only and cond.name not in only:
                continue
            cf = cache / f"{doc_id}__{cond.name}__s{cond.seed}.txt"
            if cf.exists():
                text = cf.read_text()
            else:
                with tempfile.TemporaryDirectory() as td:
                    work = Path(td)
                    text = "\n".join(run_engine(args.engine, study.render(doc, p, cond, work), work) for p in pages)
                cf.write_text(text)
            c = study.cer(ref_text, text)
            for r in score(text, truth):
                r.update(engine=args.engine, testset=args.testset, doc=doc_id, condition=cond.name,
                         family=cond.family, dpi=cond.dpi, seed=cond.seed, cer=c)
                rows.append(r)
    df = pd.DataFrame(rows)
    out = HERE / "results" / f"rows_{args.engine.replace(':', '-')}_{args.testset}.csv"
    df.to_csv(out, index=False)
    n = len(df)
    corr = df[df.status == "corrupted"]
    print(f"{args.engine} / test {args.testset}: {n} values in {time.time() - t0:.0f}s | "
          f"value acc {100 * (df.status == 'correct').mean():.1f}% | corrupted {len(corr)} "
          f"(silent {int(corr.silent.sum()) if len(corr) else 0}, decimal-shift {int(corr.decimal_shift.notna().sum()) if len(corr) else 0}) | "
          f"missing {(df.status == 'missing').sum()} | median CER {100 * df.drop_duplicates(['doc', 'condition', 'seed']).cer.median():.2f}%")


if __name__ == "__main__":
    main()
