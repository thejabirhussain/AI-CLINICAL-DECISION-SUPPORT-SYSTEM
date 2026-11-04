# AI-CDSS demo: OCR pipeline and numeric verification

App: http://localhost:5173 (start everything with `~/Projects/start-demo.sh`). Each upload takes ~50 s because the
local LLM extracts the labs; talk over it.

## Files (this folder)

| File | What it is | What you should see |
|---|---|---|
| `patient_report_maria_alvarez.pdf` | Clean digital report (synthetic patient) | 13 labs, flags, **no** Verify marks |
| `maria_scan_100dpi.png` | Same report as a 100 dpi scan | 13 of 13 values correct (old pipeline: 61.5% at this quality) |
| `maria_scan_72dpi.png` | Same report as a 72 dpi phone photo | 12 of 13 correct (old pipeline: 3 of 13); **Creatinine "21"** carries an amber **Verify** chip; summary shows "To verify: 1" |
| `maria_scanned_150dpi.pdf` | Scanned PDF, no text layer | 13 of 13 correct (old pipeline rejected it: "Could not extract any text") |

True values for reference: Glucose 248 · HbA1c 9.2 · Hemoglobin 9.4 · Ferritin 9 · WBC 7.4 · Platelets 262 ·
Sodium 133 · Potassium 5.8 · BUN 42 · **Creatinine 2.1** · eGFR 26 · Troponin I 0.07 · LDL 142.

## Order

1. Upload `patient_report_maria_alvarez.pdf`. Point at the flags: Troponin Critical, K 5.8 High, Hb 9.4 Low.
2. Upload `maria_scan_72dpi.png`. Point at "To verify: 1" and the Verify chip on Creatinine. Hover it: the reason
   ("Creatinine is reported with a decimal point; '21' has none (possible lost decimal)") and the source row.
   Say: the flag is still "High", so without this check the error would be invisible. That is the silent corruption.
3. Ask the queries below on the 72 dpi upload.

## Queries (ask after uploading `maria_scan_72dpi.png`)

1. **What are the most urgent issues for this patient and what should be done first?**
   Expect: troponin critical; creatinine named as an UNVERIFIED reading, possibly 2.1, to confirm against the source.
2. **Is her kidney function good enough to continue metformin?**
   Expect: eGFR 26 drives the answer (below 30: stop metformin), with a guideline citation; creatinine treated as unverified.
3. **Which of her lab values should be re-checked against the original document, and why?**
   Expect: creatinine 21, lost decimal point; the rest consistent.
4. **Her potassium is 5.8. Which of her current medications could be contributing?**
   Expect: lisinopril (ACE inhibitor), and NSAID (ibuprofen) with CKD.
5. **Summarise her anemia work-up from the labs.**
   Expect: Hb 9.4 low, ferritin 9 low: iron deficiency; she is on ferrous sulfate.

Backup question if time allows, on the clean PDF: **"Draft a differential for her chest tightness."**

## If something goes wrong

* An upload spins for more than 2 minutes: Ollama is busy; run
  `curl -s localhost:11434/api/generate -d '{"model":"llama3.2","prompt":"hi","stream":false,"keep_alive":"4h"}'`
  and retry.
* "Patient session not found": the API restarted; upload the file again.
