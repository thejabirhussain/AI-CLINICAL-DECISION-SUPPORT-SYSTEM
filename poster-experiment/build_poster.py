"""Build the A2 poster.

A2 portrait, 420 x 594 mm. Keeps the supplied template's identity - Calibri,
its blue, a header band, rounded panels, QR and references at the foot - but
replaces its type scale (body text was 8.97 pt, unreadable at A2) and its
1-3 mm column gutter.

Usage: python build_poster.py --figures figures/ --out poster/
"""
from __future__ import annotations

import argparse
from pathlib import Path

import qrcode
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Pt

MM = 36000                      # EMU per mm
PAGE_W, PAGE_H = 420, 594
MARGIN = 14
COL_W, GUTTER = 190, 12
C1_X, C2_X = MARGIN, MARGIN + COL_W + GUTTER

INK = RGBColor(0x0B, 0x0B, 0x0B)
INK2 = RGBColor(0x52, 0x51, 0x4E)
BLUE = RGBColor(0x2F, 0x55, 0x97)
RULE = RGBColor(0x44, 0x72, 0xC4)
RED = RGBColor(0xB3, 0x25, 0x1F)
PANEL = RGBColor(0xF4, 0xF6, 0xFA)
PANEL_E = RGBColor(0xC9, 0xD2, 0xE0)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
CREAM = RGBColor(0xFC, 0xFC, 0xFB)

REPO = "https://github.com/thejabirhussain/AI-CLINICAL-DECISION-SUPPORT-SYSTEM"

TITLE = "Silent Corruption in Clinical AI"
SUBTITLE = ("At 150 dpi, 98.3% of characters are read correctly "
            "— and 15% of laboratory values are wrong")
AUTHOR = "Mohammed Jabir Hussain Shaik"
AFFIL = ("MSc Artificial Intelligence, School of Electronics, Electrical "
         "Engineering and Computer Science, Queen's University Belfast"
         "   ·   mshaik01@qub.ac.uk")

PROBLEM = [
    "Clinical AI increasingly ingests patient records as **images** \u2014 "
    "scans, faxes, phone photographs \u2014 not structured data.",
    "Every stage from pixel to generated sentence is lossy: OCR, extraction, "
    "abnormal-value flagging, prompt assembly.",
    "RAG systems are evaluated on retrieval and answer quality \u2014 almost "
    "never on whether the patient's own numbers survived.",
    "A wrong but still *plausible* value crosses the same threshold as the "
    "truth, so the alarm the clinician sees is identical.",
    "If nothing can say \u201cthis reading is suspect\u201d, a decimal point "
    "lost in a scan becomes a clinical recommendation.",
]

METHOD = [
    "Built a RAG clinical decision support prototype: React, FastAPI, Qdrant, "
    "Tesseract OCR, LLM generation. Code is public.",
    "Injected **controlled image faults** into a synthetic discharge summary "
    "with machine-readable ground truth for 13 analytes.",
    "32 conditions \u2014 resolution, blur, JPEG, rotation, noise, composites "
    "\u2014 5 seeds where stochastic. **832 observations.**",
    "Added a **calibration gate**: no result unless the clean render gives "
    "13/13. My first run failed it \u2014 my own parser's bug.",
    "Measured at three levels: characters, extracted values against truth, "
    "and the flag the clinician would be shown.",
]

FINDINGS = [
    ("Text quality does not predict value safety.",
     "At 150 dpi — a routine scanner setting — 98.3% of characters "
     "are correct and 15% of values are wrong. Resolution dominates: at "
     "300 dpi, blur to σ 2.0, JPEG to q15, rotation to 5° and noise "
     "to σ 20 were each harmless."),
    ("65% of corruptions are invisible.",
     "Of 43 wrong values, 28 produced the **same** abnormal-value flag as the "
     "truth. Potassium 5.8 → 58.0 mEq/L is still “High”; "
     "troponin 0.07 → 7.0 is still “Critical”. 60% were pure "
     "decimal-place shifts."),
    ("It reaches the generated output.",
     "The corrupted value is quoted verbatim in the generated recommendation "
     "in 5 of 6 generations at 100 dpi and 4 of 6 at 150 dpi \u2014 the prompt "
     "instructs the model to quote values exactly. Whether the *recommendation* "
     "itself changes was **not stable** across generations; that needs a larger, "
     "properly powered comparison."),
]

TAKEHOME = ("Grounding tells you where a number came from. It does not tell you "
            "whether it was read correctly.")

LIMITS = (
    "One synthetic document, 13 analytes, one layout, one OCR engine "
    "(Tesseract 5.5.1). Degradations are synthetic approximations, not real "
    "scans. Extraction used a deterministic row parser; the deployed LLM "
    "extractor is untested. Flags follow the system's own hardcoded ranges, "
    "which are not age- or sex-aware. Plausibility envelopes are my own "
    "construction, not a clinical standard. Generation used one 3B local "
    "model, six samples per condition. No clinician has judged whether any "
    "corruption would change management. This is a preliminary fault-injection "
    "study on a research prototype \u2014 not a validated or deployable system."
)

REFS = [
    "Gao, Y. et al. Retrieval-Augmented Generation for Large Language Models: "
    "A Survey. arXiv:2312.10997, 2023.",
    "Amugongo, L. M. et al. Retrieval augmented generation for large language "
    "models in healthcare: a systematic review. PLOS Digital Health 4(6): "
    "e0000877, 2025.",
    "Lu, Y., Zhao, X., Wang, J. ClinicalRAG: Enhancing Clinical Decision "
    "Support through Heterogeneous Knowledge Retrieval. Workshop on "
    "Knowledgeable Language Models, ACL 2024.",
    "Ben Abacha, A., Demner-Fushman, D. A question-entailment approach to "
    "question answering. BMC Bioinformatics 20:511, 2019.  (MedQuAD)",
]


# --------------------------------------------------------------------------
def box(slide, x, y, w, h, fill=PANEL, line=PANEL_E, radius=0.03):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                Emu(int(x * MM)), Emu(int(y * MM)),
                                Emu(int(w * MM)), Emu(int(h * MM)))
    sh.adjustments[0] = radius
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line; sh.line.width = Pt(0.9)
    sh.shadow.inherit = False
    return sh


def textbox(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Emu(int(x * MM)), Emu(int(y * MM)),
                                  Emu(int(w * MM)), Emu(int(h * MM)))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return tf


def rich(para, text, size, color=INK, bold=False, italic=False,
         font="Calibri", space_after=0, line=1.12):
    """Write text into a paragraph, honouring **bold** and *italic* markers."""
    para.line_spacing = line
    para.space_after = Pt(space_after)
    import re
    for chunk in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text):
        if not chunk:
            continue
        b, i, body = bold, italic, chunk
        if chunk.startswith("**") and chunk.endswith("**"):
            b, body = True, chunk[2:-2]
        elif chunk.startswith("*") and chunk.endswith("*"):
            i, body = True, chunk[1:-1]
        r = para.add_run(); r.text = body
        r.font.size = Pt(size); r.font.bold = b; r.font.italic = i
        r.font.name = font; r.font.color.rgb = color
    return para


def heading(slide, x, y, w, text, size=30):
    tf = textbox(slide, x, y, w, 12)
    rich(tf.paragraphs[0], text, size, BLUE, bold=True)
    ln = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                Emu(int(x * MM)), Emu(int((y + 11.5) * MM)),
                                Emu(int(w * MM)), Emu(int(0.7 * MM)))
    ln.fill.solid(); ln.fill.fore_color.rgb = RULE
    ln.line.fill.background(); ln.shadow.inherit = False
    return y + 15.5


def bullets(slide, x, y, w, h, items, size=17, gap=5.0):
    tf = textbox(slide, x, y, w, h)
    for n, it in enumerate(items):
        p = tf.paragraphs[0] if n == 0 else tf.add_paragraph()
        rich(p, "•  " + it, size, INK, space_after=gap, line=1.08)
    return tf


def picture(slide, path, x, y, w):
    from PIL import Image
    iw, ih = Image.open(path).size
    h = w * ih / iw
    slide.shapes.add_picture(str(path), Emu(int(x * MM)), Emu(int(y * MM)),
                             Emu(int(w * MM)), Emu(int(h * MM)))
    return h


def caption(slide, x, y, w, label, text, size=12.5):
    tf = textbox(slide, x, y, w, 10)
    p = tf.paragraphs[0]
    rich(p, f"**{label}**  {text}", size, INK2, line=1.12)
    return 9.0


# --------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--figures", default="figures")
    ap.add_argument("--out", default="poster")
    a = ap.parse_args()
    figs, out = Path(a.figures), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    qr_png = out / "qr_repo.png"
    q = qrcode.QRCode(box_size=14, border=1,
                      error_correction=qrcode.constants.ERROR_CORRECT_M)
    q.add_data(REPO); q.make(fit=True)
    q.make_image(fill_color="black", back_color="white").save(qr_png)

    prs = Presentation()
    prs.slide_width = Emu(PAGE_W * MM)
    prs.slide_height = Emu(PAGE_H * MM)
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0,
                                Emu(PAGE_W * MM), Emu(PAGE_H * MM))
    bg.fill.solid(); bg.fill.fore_color.rgb = CREAM
    bg.line.fill.background(); bg.shadow.inherit = False

    # ---------- header ----------
    HDR_H = 94
    box(slide, MARGIN, MARGIN, PAGE_W - 2 * MARGIN, HDR_H,
        fill=WHITE, line=PANEL_E, radius=0.02)
    qr_side = 40
    slide.shapes.add_picture(str(qr_png),
                             Emu(int((PAGE_W - MARGIN - 8 - qr_side) * MM)),
                             Emu(int((MARGIN + 9) * MM)),
                             Emu(int(qr_side * MM)), Emu(int(qr_side * MM)))
    tf = textbox(slide, PAGE_W - MARGIN - 8 - qr_side, MARGIN + 51, qr_side, 8)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    rich(p, "code, data & harness", 10.5, INK2, line=1.1)

    tw = PAGE_W - 2 * MARGIN - qr_side - 30
    tf = textbox(slide, MARGIN + 10, MARGIN + 9, tw, 30)
    rich(tf.paragraphs[0], TITLE, 50, INK, bold=True, line=1.0)
    tf = textbox(slide, MARGIN + 10, MARGIN + 29, tw, 22)
    rich(tf.paragraphs[0], SUBTITLE, 21, RED, bold=True, line=1.12)
    tf = textbox(slide, MARGIN + 10, MARGIN + 57, tw, 26)
    rich(tf.paragraphs[0], AUTHOR, 19, INK, bold=True, space_after=2.5)
    rich(tf.add_paragraph(), AFFIL, 14.5, INK2, line=1.14)

    BODY_TOP = MARGIN + HDR_H + 10
    BODY_BOT = 530

    # ---------- column 1 ----------
    y = BODY_TOP
    H1 = 107
    box(slide, C1_X, y, COL_W, H1)
    yy = heading(slide, C1_X + 7, y + 6, COL_W - 14, "Why this matters", 26)
    bullets(slide, C1_X + 7, yy, COL_W - 14, H1 - 24, PROBLEM, size=16, gap=4.4)
    y += H1 + 9

    H2 = 107
    box(slide, C1_X, y, COL_W, H2)
    yy = heading(slide, C1_X + 7, y + 6, COL_W - 14, "What I did", 26)
    bullets(slide, C1_X + 7, yy, COL_W - 14, H2 - 24, METHOD, size=16, gap=4.4)
    y += H2 + 10

    h = picture(slide, figs / "fig2_resolution.png", C1_X, y, COL_W)
    y += h + 2
    y += caption(slide, C1_X, y, COL_W, "Figure 2.",
                 "Error at two levels against scan resolution; both are "
                 "fractions on one axis. 13 analytes per point. Blur, JPEG, "
                 "rotation and noise at 300 dpi were each harmless until a "
                 "cliff (see repository).") + 9

    HL = BODY_BOT - y
    box(slide, C1_X, y, COL_W, HL, fill=WHITE, line=PANEL_E)
    tf = textbox(slide, C1_X + 7, y + 6, COL_W - 14, HL - 12)
    rich(tf.paragraphs[0], "What this does not show", 17, INK, bold=True,
         space_after=2.4)
    rich(tf.add_paragraph(), LIMITS, 10.4, INK2, line=1.14)

    # ---------- column 2 ----------
    y = BODY_TOP
    FW = 180
    h = picture(slide, figs / "fig1_architecture.png",
                C2_X + (COL_W - FW) / 2, y, FW)
    y += h + 2
    y += caption(slide, C2_X, y, COL_W, "Figure 1.",
                 "The measured pipeline. Vision at the top, language at the "
                 "bottom, five lossy stages between \u2014 and no check that a "
                 "value is physiologically possible.") + 8

    h = picture(slide, figs / "fig3_taxonomy.png", C2_X, y, COL_W)
    y += h + 2
    y += caption(slide, C2_X, y, COL_W, "Figure 3.",
                 "What the flagging layer did with each of the 43 corrupted "
                 "values.") + 9

    H3 = BODY_BOT - y
    box(slide, C2_X, y, COL_W, H3)
    yy = heading(slide, C2_X + 7, y + 6, COL_W - 14, "What I found", 26)
    tf = textbox(slide, C2_X + 7, yy, COL_W - 14, H3 - 24)
    for n, (hd, bd) in enumerate(FINDINGS):
        p = tf.paragraphs[0] if n == 0 else tf.add_paragraph()
        rich(p, f"{n + 1}.  {hd}", 16, RED, bold=True, space_after=1.2)
        rich(tf.add_paragraph(), bd, 14.8, INK, space_after=5.0, line=1.08)

    # ---------- footer ----------
    FY = BODY_BOT + 8
    box(slide, MARGIN, FY, PAGE_W - 2 * MARGIN, 17,
        fill=RGBColor(0xFF, 0xF2, 0xF1), line=RED, radius=0.08)
    tf = textbox(slide, MARGIN + 8, FY + 3.5, PAGE_W - 2 * MARGIN - 16, 12)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    rich(p, TAKEHOME, 18.5, RED, bold=True, italic=True, line=1.08)

    FY2 = FY + 22
    tf = textbox(slide, MARGIN, FY2, COL_W, 24)
    rich(tf.paragraphs[0], "**References**", 11, INK, space_after=1.2)
    for r in REFS[:2]:
        rich(tf.add_paragraph(), r, 9.4, INK2, space_after=1.2, line=1.08)
    tf = textbox(slide, C2_X, FY2 + 4.6, COL_W, 24)
    for r in REFS[2:]:
        p = tf.paragraphs[0] if r is REFS[2] else tf.add_paragraph()
        rich(p, r, 9.4, INK2, space_after=1.2, line=1.08)

    tf = textbox(slide, MARGIN, PAGE_H - MARGIN + 1, PAGE_W - 2 * MARGIN, 7)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    rich(p, "Synthetic patient data throughout \u2014 no real patient "
            "information was used.   \u00b7   Vision and Language Symposium, "
            "Queen's University Belfast", 10.5, INK2)

    pptx = out / "poster_A2.pptx"
    prs.save(pptx)
    print(f"wrote {pptx}")


if __name__ == "__main__":
    main()
