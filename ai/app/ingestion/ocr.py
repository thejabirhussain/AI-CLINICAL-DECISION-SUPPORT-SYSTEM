"""OCR for uploaded images and scanned PDFs.

Choices come from the numeric-ocr evaluation in this repo (exact lab-value accuracy, not character accuracy):
  * rescale to ~300 dpi before recognition: the largest single gain at phone/fax/low-dpi resolutions, because
    Tesseract's LSTM loses thin decimal points when x-height falls below ~20 px;
  * psm 6 (uniform block) with preserved inter-word spaces, so table rows stay on one line for the row parser;
  * a lab-numerics fine-tune of Tesseract's best English model when present (OCR_MODEL / OCR_TESSDATA_DIR),
    falling back to the stock model.
"""

from __future__ import annotations

import logging
import math
import os
import re
from pathlib import Path
from typing import Tuple

import pytesseract
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

TESSDATA_DIR = Path(os.getenv("OCR_TESSDATA_DIR", Path(__file__).parent / "tessdata"))
FINETUNED = os.getenv("OCR_MODEL", "")
TARGET_DPI = 300
LETTER_WIDTH_IN = 8.5


def _model() -> Tuple[str, str]:
    """(language, extra tesseract flags) for the best available model."""
    if (TESSDATA_DIR / f"{FINETUNED}.traineddata").exists():
        return FINETUNED, f'--tessdata-dir "{TESSDATA_DIR}"'
    return "eng", ""


def estimate_dpi(image: Image.Image) -> float:
    """Embedded dpi when the scanner wrote one, else assume a full-width US-letter page."""
    dpi = image.info.get("dpi")
    if dpi and dpi[0] and 50 <= float(dpi[0]) <= 1200:
        return float(dpi[0])
    return image.width / LETTER_WIDTH_IN


def prepare(image: Image.Image) -> Tuple[Image.Image, int]:
    image = ImageOps.exif_transpose(image).convert("L")
    factor = max(1, min(4, math.ceil(TARGET_DPI / estimate_dpi(image) - 0.05)))
    if factor > 1:
        image = image.resize((image.width * factor, image.height * factor), Image.LANCZOS)
    return image, factor


def ocr_image(image: Image.Image) -> Tuple[str, dict]:
    lang, flags = _model()
    prepared, factor = prepare(image)
    text = pytesseract.image_to_string(prepared, lang=lang, config=f"--psm 6 -c preserve_interword_spaces=1 {flags}")
    # Column padding can be dozens of spaces; three keep columns apart without pushing rows past the LLM's window
    text = re.sub(r"[ \t]{3,}", "   ", text)
    return text, {"source": "ocr", "ocr_model": lang, "upscale": factor}


def ocr_pdf(pdf_bytes: bytes, dpi: int = TARGET_DPI) -> Tuple[str, dict]:
    """Scanned PDFs carry no text layer; render each page and OCR it."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages, meta = [], {}
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
        img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
        img.info["dpi"] = (dpi, dpi)
        text, meta = ocr_image(img)
        pages.append(f"[Page {i}]\n{text}")
    doc.close()
    return "\n".join(pages), {**meta, "source": "ocr_pdf", "page_count": len(pages)}
