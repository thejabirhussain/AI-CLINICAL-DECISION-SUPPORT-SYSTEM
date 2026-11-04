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

## Queries (ask after uploading `maria_scan_72dpi.png`; each tested on the live app, ~30 s)

1. **What are the most urgent issues for this patient and what should be done first?**  ← the headline query
   Got: "Troponin = 0.07 ng/mL (CRITICAL) and the high creatinine level (21 mg/dl, UNVERIFIED READING, possibly 2.1
   due to lost decimal point)... possible acute coronary syndrome and severe kidney dysfunction."
2. **Is her kidney function good enough to continue metformin?**
   Got: kidney function severely impaired, eGFR 26, so not good enough to continue metformin.
3. **Summarise her anemia work-up from the labs.**
   Got: Hb 9.4 g/dL low (anemia), structured as interpretation, risk flags, evidence, next steps.

Avoid open-ended questions about which values to re-check or which drugs raise potassium: the local 3B model
(llama3.2) answers those poorly. The Verify badge in the lab table already shows the re-check story visually.

## If something goes wrong

* An upload spins for more than 2 minutes: Ollama is busy; run
  `curl -s localhost:11434/api/generate -d '{"model":"llama3.2","prompt":"hi","stream":false,"keep_alive":"4h"}'`
  and retry.
* "Patient session not found": the API restarted; upload the file again.
