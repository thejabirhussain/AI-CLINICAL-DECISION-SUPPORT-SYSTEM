"""Held-out test set B: synthetic lab reports in fonts the fine-tuned model never sees (Times, Courier),
with varied analytes, values and column layouts. Ground truth is written next to each PDF.

    .venv/bin/python make_testset_b.py --n 20 --out data/testset_b
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import pymupdf

from common import CATALOG, flag, fmt, ref_text, sample_value

LAYOUTS = [
    ("Test", "Result", "Units", "Reference", "Flag"),
    ("Analyte", "Value", "Unit", "Reference Range", "Flag"),
    ("Test", "Result", "Units", "Reference", ""),  # result always precedes reference: the study's row parser takes the first number
    ("Investigation", "Result", "Units", "Normal Range", ""),
]
FONTS = [("serif", "Times"), ("monospace", "Courier")]
LABS = ["Northgate Clinical Laboratory", "St. Elm Pathology", "Harbour City Diagnostics", "Mercy Valley Lab Services"]


def make(i: int, out: Path, rng: random.Random) -> dict:
    font_css, font_name = FONTS[i % len(FONTS)]
    cols = LAYOUTS[i % len(LAYOUTS)]
    analytes = rng.sample(CATALOG, rng.randint(12, 18))
    rows, truth = [], []
    for a in analytes:
        v = sample_value(a, rng)
        f = flag(a, v)
        cell = {"Test": a.name, "Analyte": a.name, "Investigation": a.name,
                "Result": fmt(a, v), "Value": fmt(a, v),
                "Units": a.unit, "Unit": a.unit,
                "Reference": ref_text(a), "Reference Range": ref_text(a), "Normal Range": ref_text(a),
                "Flag": f, "": ""}
        rows.append("<tr>" + "".join(f"<td>{cell[c]}</td>" for c in cols if c) + "</tr>")
        truth.append({"name": a.name, "value": v, "decimals": a.decimals, "lo": a.lo, "hi": a.hi,
                      "plaus": list(a.plaus), "flag": f})
    head = "<tr>" + "".join(f"<th>{c}</th>" for c in cols if c) + "</tr>"
    html = f"""
<div class="banner">SYNTHETIC TEST DOCUMENT {i:03d} &#8212; NOT A REAL PATIENT</div>
<h1>{LABS[i % len(LABS)]}</h1>
<p>Patient: Test Subject {i:03d} &#160;&#160; Collected: 1{i % 9}/0{1 + i % 8}/2026 &#160;&#160; Requested by: Internal Medicine</p>
<h2>Laboratory Results</h2>
<table class="labs">{head}{''.join(rows)}</table>
<p>Results should be interpreted in the clinical context. Values outside the reference range are flagged.</p>
"""
    css = f"""
* {{ font-family: {font_css}; }}
body {{ font-size: {rng.choice([9, 9.5, 10])}pt; color: #111; }}
.banner {{ font-size: 7.5pt; font-weight: bold; text-align: center; }}
h1 {{ font-size: 13pt; margin: 6px 0 2px 0; }}
h2 {{ font-size: 10.5pt; margin: 8px 0 3px 0; border-bottom: 1px solid #999; }}
table.labs {{ border-collapse: collapse; width: 100%; }}
table.labs th {{ text-align: left; padding: 2px 6px; border-bottom: 1px solid #555; }}
table.labs td {{ padding: 2px 6px; border-bottom: 1px solid #ddd; }}
"""
    pdf = out / f"report_{i:03d}.pdf"
    story = pymupdf.Story(html=html, user_css=css)
    writer = pymupdf.DocumentWriter(str(pdf))
    rect = pymupdf.paper_rect("letter")
    more = True
    while more:
        dev = writer.begin_page(rect)
        more, _ = story.place(rect + (48, 42, -48, -42))
        story.draw(dev)
        writer.end_page()
    writer.close()
    meta = {"pdf": pdf.name, "font": font_name, "layout": list(cols), "analytes": truth}
    (out / f"report_{i:03d}.json").write_text(json.dumps(meta, indent=1))
    return meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--out", default="data/testset_b")
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    metas = [make(i, out, rng) for i in range(args.n)]
    n_vals = sum(len(m["analytes"]) for m in metas)
    print(f"{len(metas)} reports, {n_vals} analyte values, fonts: {sorted({m['font'] for m in metas})}")


if __name__ == "__main__":
    main()
