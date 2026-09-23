# AI-CDSS: Demo Script & Verified Queries

Every query below was run against the live local stack (Qdrant with 11,000 MedQuAD points, MiniLM embeddings, cross-encoder reranker, Ollama `llama3.2` 3B) on 23 Sep 2026. The "Expect" notes describe what came back. Answers can vary slightly between runs, but confidence and sources are stable.

**Files in this folder**

| File | Use |
|---|---|
| `patient_report_maria_alvarez.pdf` | Synthetic discharge summary. Upload it to demo patient-grounded reasoning |
| `patient_report_maria_alvarez_scan.png` | The same report as a scanned image. Upload it to demo OCR (Tesseract) |
| `make_demo_report.py` | Regenerates the PDF |

> ⏱ Answers take **20–70 s**, because a 3B model runs locally on the laptop. Talk through the pipeline while it thinks (see the talking points at the end).

---

## 0. Before the call (2 min)

1. Open Docker Desktop and Ollama, then start the stack (`docs/DEMO_RUNBOOK.md`).
2. Warm up the model with one throwaway question, so the first live answer isn't slow.
3. Click **New** so the demo starts on the clean home screen.

---

## 1. Knowledge-base questions (general mode, no patient)

Type these, or click **Ask a Question** / **Treatment Plan** / **Red Flags** and pick the example.

| # | Query | Expect |
|---|---|---|
| G1 | **What causes glaucoma and how is it diagnosed?** | ⭐ Best opener. **High confidence**, 5 sources, clickable `[1]–[5]` citations (click one → jumps to the reference) |
| G2 | **How is Parkinson's disease treated?** | High confidence, 5 sources (levodopa, dopamine agonists, MAO-B inhibitors, deep brain stimulation) |
| G3 | What is the first-line treatment for type 2 diabetes? | High confidence, 5 sources |
| G4 | How is high blood pressure treated? | High confidence, 5 sources |
| G5 | What are the treatment options for chronic kidney disease? | High confidence, 5 sources |
| G6 | What are the symptoms of iron deficiency anemia? | High confidence, 3 sources, short "Tier 1" answer |
| G7 | What are the warning signs of a stroke? | High confidence, 3 sources, short answer |
| G8 | What are the warning signs of a heart attack that need emergency care? | High confidence, 3 sources |

**What to point out:** the "Response generated" steps, the confidence badge, the References list with relevance %, and that each source is a real retrieved MedQuAD (NIH) entry.
G6 and G7 show **adaptive response length**: simple questions get short answers, and management questions get the 4-section clinical format.

## 2. Conversation memory (query rewriting)

| # | Query | Expect |
|---|---|---|
| C1 | *(after G2)* **What are the side effects of those medications?** | High confidence, 3 sources. The backend rewrites "those medications" into *"levodopa, dopamine agonists, MAO-B inhibitors, COMT inhibitors…"* before searching |

Or click a **Suggested follow-up** chip under any answer.

---

## 3. Patient report (the main event)

**Upload:** `demo/patient_report_maria_alvarez.pdf` (the **Upload Report** button or the sidebar). It takes ~30 s.

**Expect in the Patient Overview tab:**
- **64 F**, 6 active problems: T2DM (poorly controlled), **CKD stage 4**, hypertension, iron-deficiency anemia, hyperlipidemia, osteoarthritis
- 6 medications with doses, including metformin, lisinopril, **ibuprofen**, and allergies (sulfa, penicillin)
- 13 labs, **11 flagged**: Troponin I 0.07 **Critical**; K 5.8, creatinine 2.1, BUN 42, glucose 248, HbA1c 9.2, LDL 142 **High**; Hb 9.4, ferritin 9, Na 133, eGFR 26 **Low**; WBC and platelets **Normal**

Then ask (or use the **Interpret Labs / Drug Interactions / Summarize Patient** chips):

| # | Query | Expect (verified) |
|---|---|---|
| P1 | **Which of this patient's lab values need urgent attention, and why?** | Leads with **Troponin I 0.07 (critical) → myocardial injury / rule out ACS** |
| P2 | **Is metformin safe to continue given this patient's kidney function?** | **Not safe**: stage 4 CKD, eGFR 26, creatinine 2.1 (lactic acidosis risk) |
| P3 | **Is ibuprofen safe for this patient's knee pain given her kidney function?** | **Not safe**: NSAIDs worsen kidney function at eGFR 26 |
| P4 | **Should lisinopril be continued with this patient's potassium level?** | **Should not be continued**: K 5.8 is high, and ACE inhibitors raise potassium |
| P5 | **What could be causing her anemia and how should it be managed?** | ⭐ **High confidence, 6 sources.** Iron deficiency (ferritin 9) + CKD (low erythropoietin), with cited kidney-disease/anemia entries. (The chip version "…this patient's anemia…" gave medium confidence, 5 sources, same reasoning) |
| P6 | Interpret this patient's abnormal labs and explain their clinical significance. | Correct values: troponin critical, K 5.8 high, eGFR 26 / creatinine 2.1 → severe kidney impairment |
| P7 | Summarize this patient: active problems, key findings, and what needs attention first. | Accurate one-paragraph summary: problems, troponin, potassium, eGFR |

**What to point out:**
- The patient's own data grounds the answers: exact values, flags and allergies.
- P2–P4 catch real prescribing hazards a clinician would want flagged.
- Several patient answers show **low confidence** with few or no sources. That's deliberate honesty: the knowledge base is consumer-level NIH Q&A, so there's little matching evidence for specialist prescribing questions. The answer says it relies on general clinical knowledge instead of inventing citations. (P5 shows the opposite case, where the knowledge base *does* cover it.)

## 4. OCR on a scanned document (optional)

Click **New**, then upload `demo/patient_report_maria_alvarez_scan.png`. Tesseract OCR reads the image, then the same structuring pipeline runs. Verified: it extracts the same 6 problems, 6 medications, 2 allergies and 13 labs with identical flags as the PDF. The only OCR artifact is "Troponin I" read as "Troponin |". Ask P1 again.

## 5. Case-style prompts (optional; work, but lower confidence)

| # | Query | Expect |
|---|---|---|
| D1 | A 60-year-old man presents with a resting tremor in his right hand, slowness of movement and a shuffling gait. What is the differential diagnosis? | Parkinson's disease first; essential tremor and X-linked dystonia-parkinsonism considered, with 4 sources. Low confidence (case wording is far from the Q&A wording) |
| D2 | A 45-year-old woman presents with fatigue, weight gain, cold intolerance, constipation and dry skin. What is the differential diagnosis? | Hypothyroidism, TSH/free T4 workup. **No sources**: the answer runs on general knowledge and makes no fake citations |
| D3 | Draft an assessment and plan for a 55-year-old man with newly diagnosed type 2 diabetes (HbA1c 8.1%) and high blood pressure. | Structured 4-section plan, 4 sources, low confidence |

---

## 6. Known limitations (good for a CI Foundations discussion)

- **Small model, narrow reasoning.** A broad prompt like *"Go through each of this patient's medications and say whether it is safe"* produced mistakes (it called ibuprofen "not a concern" and flagged amlodipine for kidney clearance). The same model answers the targeted questions P2–P4 correctly. Model size (3B params) limits multi-step reasoning. Swapping `OLLAMA_MODEL` to an 8B model, or `LLM_PROVIDER=openai`, needs no code change.
- **Prompt sensitivity.** *"Should lisinopril be continued **with** this patient's potassium level?"* → "should not be continued" (correct). *"…**given** this patient's potassium level?"* → "continue with caution" (weaker). Use the exact wordings in this sheet (the UI chips use them too).
- **Knowledge-base coverage.** MedQuAD is consumer health Q&A. It has no prescribing guidelines or drug-interaction tables, hence low confidence on those questions.
- **Confidence** = mean cross-encoder relevance of the evidence (≥0.8 high, ≥0.5 medium). It measures *evidence support*, not clinical correctness.
- **Lab flags** use hard-coded adult reference ranges. Tests without a range show "Not assessed".
- **LLM extraction is not perfectly deterministic.** During testing the model once added vital signs and a reference value as "labs"; rule-based post-processing now filters these out. That's a good example of pairing an LLM with deterministic guardrails.
- **Latency:** no streaming, so the reasoning steps in the UI are a visual indicator only.

## Talking points while an answer generates

1. **Query rewriting.** Follow-ups like "those medications" are resolved from the conversation, but only when needed.
2. **Query classification.** Four tiers (short fact → complex case) set answer length and how many sources are used.
3. **Retrieval.** MiniLM embedding → Qdrant HNSW cosine search (top 80 candidates) → similarity cutoff.
4. **Reranking.** A cross-encoder (`ms-marco-MiniLM-L-12-v2`) rescores query/passage pairs; results under 5% relevance are dropped.
5. **Grounded generation.** Numbered evidence + patient context → LLM, with rules: cite only given refs, quote patient values exactly, separate allergies from medications.
6. **Post-processing.** Invalid citations are removed, and follow-up questions are generated.
7. **Patient pipeline.** PDF (PyMuPDF) or image (Tesseract) → LLM extraction to JSON → rule-based abnormal-lab flagging → session memory.

> Decision support only: every output must be verified by a qualified clinician. All patient data here is synthetic.
