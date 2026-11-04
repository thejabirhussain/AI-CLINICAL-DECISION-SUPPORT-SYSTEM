"""Shared pieces for the numeric-OCR study.

Builds on ../poster-experiment (the presented "silent corruption" study): its degradation conditions, row parser,
CER and decimal-shift definitions are imported unchanged so results stay comparable.
"""
from __future__ import annotations

import base64
import io
import json
import os
import random
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "poster-experiment"))
import ocr_fault_injection as study  # noqa: E402  (reused as-is)

MODELS = HERE / "models"

# ---------------------------------------------------------------------------
# Analyte catalogue: name, unit, decimals, printed reference range (lo, hi), plausible envelope.
# Ranges are typical adult values used to render and flag synthetic reports; not a clinical standard.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Analyte:
    name: str
    unit: str
    decimals: int
    lo: float
    hi: float
    plaus: tuple[float, float]


CATALOG = [
    Analyte("Glucose (fasting)", "mg/dL", 0, 70, 99, (10, 1500)),
    Analyte("HbA1c", "%", 1, 4.0, 5.6, (2, 20)),
    Analyte("Hemoglobin", "g/dL", 1, 12.0, 15.5, (2, 25)),
    Analyte("Hematocrit", "%", 1, 36.0, 46.0, (5, 75)),
    Analyte("Ferritin", "ng/mL", 0, 15, 200, (0.1, 10000)),
    Analyte("WBC", "10^9/L", 1, 4.5, 11.0, (0.1, 500)),
    Analyte("Platelets", "10^9/L", 0, 150, 450, (1, 2000)),
    Analyte("Sodium", "mEq/L", 0, 135, 145, (90, 190)),
    Analyte("Potassium", "mEq/L", 1, 3.5, 5.0, (1.0, 10.0)),
    Analyte("Chloride", "mEq/L", 0, 98, 107, (60, 150)),
    Analyte("Bicarbonate", "mEq/L", 0, 22, 29, (5, 50)),
    Analyte("BUN", "mg/dL", 0, 7, 20, (1, 300)),
    Analyte("Creatinine", "mg/dL", 2, 0.60, 1.20, (0.1, 30)),
    Analyte("eGFR", "mL/min/1.73m2", 0, 60, 200, (0, 200)),
    Analyte("Calcium", "mg/dL", 1, 8.5, 10.5, (3, 20)),
    Analyte("Magnesium", "mg/dL", 1, 1.7, 2.2, (0.3, 6)),
    Analyte("ALT", "U/L", 0, 7, 56, (1, 5000)),
    Analyte("AST", "U/L", 0, 10, 40, (1, 5000)),
    Analyte("Bilirubin (total)", "mg/dL", 1, 0.1, 1.2, (0.05, 40)),
    Analyte("Albumin", "g/dL", 1, 3.5, 5.0, (0.5, 7)),
    Analyte("TSH", "mIU/L", 2, 0.40, 4.00, (0.005, 150)),
    Analyte("INR", "", 1, 0.8, 1.2, (0.5, 15)),
    Analyte("CRP", "mg/L", 1, 0.0, 5.0, (0.0, 600)),
    Analyte("Troponin I", "ng/mL", 2, 0.00, 0.04, (0.0, 100)),
    Analyte("LDL cholesterol", "mg/dL", 0, 0, 99, (5, 600)),
    Analyte("Lactate", "mmol/L", 1, 0.5, 2.2, (0.1, 30)),
]
BY_NAME = {a.name: a for a in CATALOG}


def fmt(a: Analyte, v: float) -> str:
    return f"{v:.{a.decimals}f}"


def ref_text(a: Analyte) -> str:
    if a.lo == 0 and a.decimals == 0:
        return f"< {a.hi:.0f}"
    if a.hi >= 200 and a.name == "eGFR":
        return f"> {a.lo:.0f}"
    return f"{fmt(a, a.lo)} - {fmt(a, a.hi)}"


def flag(a: Analyte, v: float) -> str:
    if v < a.lo:
        return "L"
    if v > a.hi:
        return "H"
    return ""


def sample_value(a: Analyte, rng: random.Random) -> float:
    """Half normal, half abnormal; rounded to the analyte's printed precision."""
    span = a.hi - a.lo if a.hi > a.lo else max(a.hi, 1)
    r = rng.random()
    if r < 0.5:
        v = rng.uniform(a.lo, a.hi)
    elif r < 0.75:
        v = rng.uniform(a.hi, a.hi + span * 1.5)
    else:
        v = rng.uniform(max(a.plaus[0], a.lo - span * 0.8), a.lo)
    v = max(v, a.plaus[0])
    return round(v, a.decimals)


# ---------------------------------------------------------------------------
# OCR engines. Each returns plain text for one page image.
# ---------------------------------------------------------------------------
def tesseract(png: Path, model: str = "eng", tessdata: Path | None = None, psm: int = 6) -> str:
    cmd = ["tesseract", str(png), "stdout", "--psm", str(psm), "-c", "preserve_interword_spaces=1", "-l", model]
    if tessdata:
        cmd[1:1] = ["--tessdata-dir", str(tessdata)]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def tesseract_tsv(png: Path, model: str = "eng", tessdata: Path | None = None, psm: int = 6) -> str:
    cmd = ["tesseract", str(png), "stdout", "--psm", str(psm), "-c", "preserve_interword_spaces=1", "-l", model, "tsv"]
    if tessdata:
        cmd[1:1] = ["--tessdata-dir", str(tessdata)]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


_rapid = None


def rapidocr(png: Path) -> str:
    """PP-OCR (det + rec) through ONNX Runtime; rebuilds lines from boxes so rows read left to right."""
    global _rapid
    if _rapid is None:
        from rapidocr_onnxruntime import RapidOCR
        _rapid = RapidOCR()
    res, _ = _rapid(str(png))
    if not res:
        return ""
    items = sorted(((min(p[1] for p in b), min(p[0] for p in b), max(p[1] for p in b), t) for b, t, _ in res))
    lines, cur, cur_y = [], [], None
    for y0, x0, y1, t in items:
        mid = (y0 + y1) / 2
        if cur_y is None or abs(mid - cur_y) > (y1 - y0) * 0.6:
            if cur:
                lines.append(" ".join(t for _, t in sorted(cur)))
            cur, cur_y = [], mid
        cur.append((x0, t))
    if cur:
        lines.append(" ".join(t for _, t in sorted(cur)))
    return "\n".join(lines)


VLM_PROMPT = ("Transcribe all text in this image exactly as printed, line by line, keeping table rows on one line. "
              "Copy every number exactly, including decimal points. Do not correct, summarise or add anything.")


def ollama_vlm(png: Path, model: str = "qwen2.5vl:3b", max_side: int = 1600) -> str:
    # A 300 dpi letter page (2550x3300) overflows the default context as image tokens and the reply comes back
    # truncated ("SYN"), so cap the longest side as VLM pipelines normally do, and give the reply room.
    im = Image.open(png).convert("RGB")
    if max(im.size) > max_side:
        im.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    img = base64.b64encode(buf.getvalue()).decode()
    body = json.dumps({"model": model, "prompt": VLM_PROMPT, "images": [img], "stream": False,
                       "options": {"temperature": 0, "num_predict": 2500, "num_ctx": 8192}}).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r).get("response", "")


def upscale(png: Path, factor: int, out: Path) -> Path:
    im = Image.open(png)
    im.resize((im.width * factor, im.height * factor), Image.LANCZOS).save(out)
    return out
