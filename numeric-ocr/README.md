# Numeric OCR: from "silent corruption" to verified lab values

This folder extends the study presented at the Vision and Language Symposium ("Silent Corruption in Clinical AI",
`../poster-experiment/`). That study showed that OCR can read a lab report with 98% of characters correct while
15% of the lab *values* are wrong, and that most wrong values keep the same abnormal flag, so nothing downstream
notices. Here we ask: which OCR approach gets the numbers right, how far does fine-tuning Tesseract 5.5 help, and
what catches the errors that remain?

The study's rendering, degradation conditions, row parser, CER and decimal-shift definitions are imported unchanged
from `../poster-experiment/ocr_fault_injection.py`, and the harness reproduces the poster's numbers exactly
(300 dpi 100%, 150 dpi 84.6%, 120 dpi 76.9%, 100 dpi 61.5%, 72 dpi 23.1% values exact; the existing plausibility
check catches 9 of 28 silent corruptions).

## Metrics: why not just CER

| Metric | Question it answers |
|---|---|
| value accuracy | Was the number extracted exactly? (the clinical unit of correctness) |
| corrupted | A number was extracted, and it is wrong |
| silent | Corrupted, and the abnormal flag is the same as the true value's, so no alarm changes |
| flag flip | Corrupted, and normal/abnormal changed (a clinically significant error) |
| decimal shift | Wrong by an exact power of ten |
| missing | No value found for the row (visible, not silent) |
| median CER | Character error rate; median because noise pages make Tesseract emit pages of garbage (CER up to 1,055%) and the mean is meaningless |
| recall / false alarms / review rate | For the verification layer: share of wrong values sent to review, share of correct values sent to review, and total review load |

## Test sets

* **Test A**: the study's own document (`../demo/patient_report_maria_alvarez.pdf`, 13 analytes) under all 64
  degradation runs of the study (resolution, blur, JPEG, noise, rotation, scan/photo/fax composites).
* **Test B**: 20 held-out synthetic reports (`make_testset_b.py`, 284 values, 12–18 analytes each, four column
  layouts), rendered in **Times and Courier, fonts never used in training**, under 7 conditions
  (300/150/120/100 dpi, office scan, phone photo, poor fax).

Training data (`make_train_lines.py`) uses random values, so no test value can be memorised.

## Engines compared

| Engine | What it is |
|---|---|
| `tess_fast` | Stock Tesseract 5.5 English (homebrew `tessdata_fast`), the pipeline the study measured |
| `tess_best` | Tesseract 5.5 `tessdata_best` (float LSTM, the base for fine-tuning) |
| `*_rescale` | Same model after upscaling the page to ≥ 300 dpi (Lanczos), estimated from page width |
| `labnum` (v1) | `tess_best` fine-tuned on 6,000 sans-serif lab lines (72–300 dpi, blur/noise/JPEG/rotation) |
| `labnum2` (v2) | Same recipe on 8,000 lines in sans, serif **and** monospace families (still no Times/Courier/Georgia) |
| `rapidocr` | PP-OCR detection + recognition via ONNX Runtime (different architecture, used as a second reader) |
| `vlm-qwen2.5vl-3b` | Qwen2.5-VL 3B through Ollama, prompted for verbatim transcription (subset of conditions) |

Fine-tuning (`finetune_tesseract.sh`) is the standard tesstrain recipe done by hand: line images + WordStr box
files → `.lstmf` → `lstmtraining --continue_from eng.lstm --learning_rate 1e-4` for 10,000 iterations →
`--stop_training`. The model is 15 MB and runs at the same speed as stock `tessdata_best`.

## Failure taxonomy (what the data showed)

1. **Lost decimal point.** At low resolution the dot is a few pixels and disappears: creatinine 2.1 → 21, WBC
   7.4 → 74. The dot in the reference range disappears too ("0.6-1.2" → "06-12"), so value and range shift
   together and a row-local check cannot see it.
2. **Range fall-through.** When the result cell is unreadable (`‘Ave?`, `Wik`, `aril`), a row parser falls through
   to the first number left, the reference range's lower bound: INR 1.1 → 0.8, glucose 77 → 70.
3. **Digit substitution.** 31 → 32, 195 → 198, 121 → 127. Plausible, same flag, invisible to any rule.
4. **Split decimal (introduced by a narrow fine-tune).** v1, trained only on proportional fonts, read the wide
   cell around a monospace "." as a word break: Courier `7.8` → `7 . 8`, parsed as 7. Courier accuracy fell from
   100% (stock best) to 54%. Test B exists to catch exactly this kind of over-fitting; v2 adds serif and
   monospace families to the training mix.
5. **VLM rewriting.** Qwen2.5-VL never dropped a decimal, but on fax-quality pages it produced fluent, plausible
   values that are not on the page, and moved them toward normal: HbA1c 9.2 → "5.2 %, range 4.5–5.8, N";
   hemoglobin 9.4 (L) → 13.4; potassium 5.8 (H) → 3.6 with an invented unit and range; it also invented flags
   on clean pages and changed g/dL to g/L. Every one of these passes a plausibility check.

## Verification layer (`verify.py`, and in the app `ai/app/ingestion/numeric_verification.py`)

Nothing is auto-corrected. A failed check means "show this value to a human against the source", never "replace it".

| Check | Catches | Uses |
|---|---|---|
| plausibility (existing) | impossible values | study envelopes |
| precision | lost decimal point | analytes labs always print with a decimal (K, creatinine, Hb, HbA1c, WBC, troponin, …) |
| magnitude | lost decimal point | value far above the window and ÷10ᵏ fits; high side only, narrow-range analytes only, so true extremes (troponin in MI, eGFR 3) are not flagged |
| structure | range fall-through | the number is directly followed by a range separator and another number |
| agreement | digit substitution, VLM/LLM rewriting | a second, differently built reader must extract the same value |
| source row (app only) | LLM rewriting | the LLM's extracted value must equal the deterministic parser's value on the source row |

## Results

Exact value accuracy (A = 832 values, B = 1,988 values; "≤150 dpi" = the resolution sweep at 150 dpi and below,
the study's failure regime; VLM on a subset: 12 of A's conditions, 8 reports × 3 conditions of B).

| Engine | All · A | All · B | ≤150 dpi · A | ≤150 dpi · B | Silent · A / B | Decimal shifts · B |
|---|---|---|---|---|---|---|
| Stock Tesseract 5.5 | 69.2% | 75.1% | 60.0% | 84.2% | 28 / 60 | 109 |
| Stock + rescale | 73.2% | 81.4% | 98.5% | 98.8% | 19 / 41 | 11 |
| Tesseract best | 66.8% | 73.1% | 41.5% | 76.5% | 41 / 54 | 132 |
| Tesseract best + rescale | 71.4% | 83.9% | 92.3% | 99.3% | 39 / 29 | 20 |
| Fine-tuned v2 + rescale | 75.4% | 75.5% | 100% | 90.7% | 14 / 101 | 56 |
| PP-OCR (RapidOCR) | 80.8% | 77.9% | 95.4% | 94.2% | 20 / 40 | 1 |
| Qwen2.5-VL 3B (subset) | 85.0% | 100% | 93.8% | n/a | 9 / 0 | 0 |

* Rescaling to 300 dpi is the largest single gain (low-dpi accuracy 60% → 98.5%, decimal shifts 109 → 11).
* Fine-tuned v2 is the best engine on the study document (100% at ≤150 dpi, zero decimal shifts) and on unseen
  Times (85.3%), but on unseen Courier it still splits digits across monospace gaps (66.3% vs 79.9% stock).
  The app therefore defaults to stock + rescale; the fine-tune is available via `OCR_MODEL` for known templates.
* No single engine wins everywhere, so the verification layer is what makes the pipeline safe:

| Checks (primary = stock Tesseract) | Silent caught · A | Wrong caught · B | False alarms · B | Review rate · B |
|---|---|---|---|---|
| Plausibility (existing) | 9 / 28 | 51.3% | 0.8% | 6.6% |
| + precision + structure | 23 / 28 | 87.0% | 0.9% | 10.7% |
| + agreement with RapidOCR | 28 / 28 | 100% | 9.4% | 19.8% |

With RapidOCR agreement every accepted value in both test sets was correct; with the fine-tuned model as primary,
agreement still catches 266 of 268 wrong values on B. Full tables: `results/verify_*.csv`, `results/rows_*.csv`.

## Reproduce

```bash
python3.11 -m venv .venv && .venv/bin/pip install pymupdf pillow numpy pandas rapidfuzz matplotlib rapidocr_onnxruntime tabulate
curl -L -o models/eng_best.traineddata https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata
.venv/bin/python make_testset_b.py
.venv/bin/python make_train_lines.py --n 8000 --out data/train_lines_v2 --fonts all
env NAME=labnum2 LINES=data/train_lines_v2 WORK=models/train_v2 ./finetune_tesseract.sh 10000
.venv/bin/python evaluate.py --engine labnum2_rescale --testset A     # and B; any engine from the table
.venv/bin/python verify.py --primary labnum2_rescale --secondary rapidocr
.venv/bin/python report.py
```

## Limits

* Test documents are synthetic and rendered digitally before degradation; real scans add skew, shadows, stamps and
  handwriting. The degradations reproduce the study's conditions, not every real-world artefact.
* One VLM (3B, local) on a subset of pages; larger VLMs read better but the rewriting failure mode is reported for
  larger models too (Amazon "Do VLMs read or rewrite?", NeurIPS 2025 KIE-HVQA).
* Analyte conventions (which tests carry a decimal, reference windows) are typical adult US values, not a clinical
  standard; a deployment would take them from the lab's own LIS.
