"""Training lines for fine-tuning Tesseract's LSTM on low-resolution clinical numerics.

Each sample is one text line (PNG + .gt.txt) rendered in a SANS-SERIF font at a scan resolution between 72 and
300 dpi, with optional blur, sensor noise, JPEG and slight rotation: the degradations where the presented study
found decimal points disappearing. Times, Courier and Georgia are never used, so test set B measures generalisation
to unseen fonts. Values are random, so no test value can be memorised.

    .venv/bin/python make_train_lines.py --n 6000 --out data/train_lines
"""
from __future__ import annotations

import argparse
import io
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from common import CATALOG, flag, fmt, ref_text, sample_value

SUP = "/System/Library/Fonts/Supplemental/"
TRAIN_FONTS = [
    (SUP + "Arial.ttf", 0), (SUP + "Arial Bold.ttf", 0), (SUP + "Arial Narrow.ttf", 0),
    (SUP + "Verdana.ttf", 0), (SUP + "Tahoma.ttf", 0), (SUP + "Trebuchet MS.ttf", 0),
    ("/System/Library/Fonts/Helvetica.ttc", 0), ("/System/Library/Fonts/Helvetica.ttc", 1),
]
# v2: serif and monospace families too. v1 (sans only) learned to read the wide cell around a monospace "." as a
# word break ("7 . 8"), a split-decimal corruption on Courier. None of these is a Times/Courier/Georgia variant.
SERIF_MONO = [
    (SUP + "Palatino.ttc" if Path(SUP + "Palatino.ttc").exists() else "/System/Library/Fonts/Palatino.ttc", 0),
    (SUP + "Baskerville.ttc", 0), (SUP + "Charter.ttc", 0), (SUP + "Iowan Old Style.ttc", 0),
    (SUP + "PTSerif.ttc", 0), (SUP + "Hoefler Text.ttc", 0), (SUP + "Cochin.ttc", 0),
    ("/System/Library/Fonts/Menlo.ttc", 0), ("/System/Library/Fonts/Monaco.ttf", 0), (SUP + "Andale Mono.ttf", 0),
    (SUP + "PTMono.ttc", 0), ("/System/Library/Fonts/SFNSMono.ttf", 0),
]
# '^' is not in eng's unicharset, so lstmtraining skips any line containing it; use a common LIS spelling instead
UNIT = {"10^9/L": "x10E9/L"}
FONTS = TRAIN_FONTS
HELD_OUT = ("Times", "Courier", "Georgia")  # never used here; test set B is rendered in Times and Courier
assert not any(h.lower() in f.lower() for f, _ in TRAIN_FONTS for h in HELD_OUT)
assert not any(h.lower() in f.lower() for f, _ in SERIF_MONO for h in HELD_OUT)

DPIS = [72, 80, 85, 90, 100, 110, 120, 135, 150, 175, 200, 250, 300]
WORDS = ("patient admitted with progressive fatigue shortness of breath chest pain history of type diabetes "
         "hypertension chronic kidney disease anemia medication review follow up with primary care nephrology "
         "cardiology repeat labs in three days discharge summary laboratory results reference range collected "
         "requested by internal medicine allergies none known current medications twice daily as needed").split()
MEDS = ["Metformin 1000 mg PO twice daily", "Lisinopril 20 mg PO daily", "Amlodipine 10 mg PO daily",
        "Atorvastatin 40 mg PO daily", "Ibuprofen 400 mg PO three times daily", "Ferrous sulfate 325 mg PO daily",
        "Apixaban 5 mg PO twice daily", "Furosemide 40 mg IV once", "Insulin glargine 18 units at night"]


def lab_row(rng: random.Random) -> str:
    a = rng.choice(CATALOG)
    v = sample_value(a, rng)
    parts = [a.name, fmt(a, v), UNIT.get(a.unit, a.unit), ref_text(a)]
    if rng.random() < 0.6:
        parts.append(flag(a, v))
    sep = rng.choice(["  ", "   ", "    "])
    return sep.join(p for p in parts if p)


def numeric_line(rng: random.Random) -> str:
    k = rng.random()
    if k < 0.3:
        return f"BP {rng.randint(85, 190)}/{rng.randint(45, 110)} mmHg, HR {rng.randint(45, 140)}, SpO2 {rng.randint(85, 100)}% on room air"
    if k < 0.5:
        return f"Weight {rng.uniform(40, 140):.1f} kg, BMI {rng.uniform(16, 45):.1f}, Temp {rng.uniform(35.5, 40.2):.1f} C"
    if k < 0.7:
        return f"Collected: {rng.randint(1, 12):02d}/{rng.randint(1, 28):02d}/2026  {rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}"
    a = rng.choice(CATALOG)
    vals = [fmt(a, sample_value(a, rng)) for _ in range(rng.randint(2, 4))]
    return f"{a.name} trend: " + " -> ".join(vals) + f" {UNIT.get(a.unit, a.unit)}"


def prose_line(rng: random.Random) -> str:
    if rng.random() < 0.3:
        return rng.choice(MEDS)
    n = rng.randint(5, 11)
    s = " ".join(rng.choice(WORDS) for _ in range(n))
    return s[0].upper() + s[1:] + rng.choice([".", "", "."])


def render(text: str, rng: random.Random) -> Image.Image:
    font_path, idx = rng.choice(FONTS)
    dpi = rng.choice(DPIS)
    pt = rng.uniform(8.5, 11.5)
    px = max(6, round(pt * dpi / 72))
    font = ImageFont.truetype(font_path, px, index=idx)
    l, t, r, b = font.getbbox(text)
    pad = max(3, px // 3)
    im = Image.new("L", (r - l + 2 * pad, b - t + 2 * pad), 255)
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=font, fill=rng.randint(0, 40))
    if rng.random() < 0.15:
        im = im.rotate(rng.uniform(-0.6, 0.6), resample=Image.BICUBIC, expand=True, fillcolor=255)
    if rng.random() < 0.4:
        im = im.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 1.2)))
    if rng.random() < 0.4:
        a = np.asarray(im, dtype=np.float32) + np.random.default_rng(rng.randint(0, 1 << 30)).normal(0, rng.uniform(3, 15), (im.height, im.width))
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    if rng.random() < 0.4:
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=rng.randint(30, 95))
        im = Image.open(io.BytesIO(buf.getvalue())).convert("L")
    return im


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6000)
    ap.add_argument("--out", default="data/train_lines")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--fonts", choices=["sans", "all"], default="all", help="sans = v1 font set; all = v2")
    args = ap.parse_args()
    global FONTS
    FONTS = TRAIN_FONTS if args.fonts == "sans" else TRAIN_FONTS + SERIF_MONO
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    for i in range(args.n):
        k = rng.random()
        text = lab_row(rng) if k < 0.6 else numeric_line(rng) if k < 0.78 else prose_line(rng)
        render(text, rng).save(out / f"l{i:05d}.png")
        (out / f"l{i:05d}.gt.txt").write_text(text + "\n")
    print(f"wrote {args.n} lines to {out}")


if __name__ == "__main__":
    main()
