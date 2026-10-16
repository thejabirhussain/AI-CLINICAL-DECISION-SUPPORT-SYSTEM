# Fault injection in the document-image ingestion path

A controlled study of what happens to a patient's laboratory values between a
scanned document and a generated clinical recommendation.

**Why this exists.** The paper drafts in this repository once reported retrieval
precision, response relevance and hallucination rates that were never measured.
This directory is the opposite: a small experiment with machine-readable ground
truth, committed per-observation results, and a gate that refuses to report
anything if the instrument is not calibrated.

## Results

| | |
|---|---|
| 832 analyte observations | 13 analytes x 64 runs across 32 degradation conditions |
| 13/13 at 300 dpi | the calibration gate; nothing is reported unless this passes |
| 98.3% / 15% | at 150 dpi: characters read correctly / laboratory values wrong |
| 28 of 43 (65%) | corrupted values that kept the true value's abnormal flag |
| 26 of 43 (60%) | corruptions that were pure decimal-place shifts |
| 9 of 28 | silent corruptions the new plausibility check catches; 19 remain |

Resolution dominates. At 300 dpi, blur to sigma 2.0, JPEG to quality 15,
rotation to 5 degrees and sensor noise to sigma 20 each produced perfect
extraction. A blurry 300 dpi scan is safer than a sharp 100 dpi one.

Worked examples, all reproducible: potassium 5.8 read as 58.0, flagged "High"
either way. Troponin I 0.07 read as 7.0, "Critical" either way. Haemoglobin 9.4
read as 94.0 turns anaemia into polycythaemia. Ferritin 9 read as 15 lands
inside the reference range, so the flag disappears entirely.

## Reproducing

Needs `tesseract` on PATH, plus `pymupdf pillow numpy pandas matplotlib rapidfuzz`.

```bash
python ocr_fault_injection.py --pdf ../demo/patient_report_maria_alvarez.pdf --outdir results
python make_figures.py --results results --outdir figures
```

The LLM propagation tests additionally need Ollama running locally:

```bash
python llm_propagation.py --results results      # one generation per condition
python llm_repeat.py --n 6 --temp 0.7            # repeats, to test stability
```

`llm_repeat.py` exists because the single-generation result looked like a clean
story and was not: across six generations the apparent change in recommendation
urgency was noise, and that claim was withdrawn. What survives is that the
corrupted value is quoted verbatim in the generated text in 5 of 6 generations
at 100 dpi.

## Scope

One synthetic document, 13 analytes, one layout, one OCR engine (Tesseract
5.5.1). Synthetic degradations, not sampled real scans. Extraction measured with
a deterministic row parser, not the deployed LLM extractor. Flags follow the
system's own hardcoded reference ranges, which are not age- or sex-aware. The
plausibility envelopes in `ocr_fault_injection.py` are a conservative
construction for this study, not a clinical standard. No clinician has judged
whether any corruption would change management.

Patient data is synthetic throughout: `../demo/make_demo_report.py` renders the
report from a hardcoded list, and that list is the ground truth.
