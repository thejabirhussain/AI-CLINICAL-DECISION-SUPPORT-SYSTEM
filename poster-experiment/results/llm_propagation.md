# Does a corrupted value change the recommendation?

Model: `llama3.2:latest`, temperature 0, seed 0. Knowledge base empty, so the laboratory values are the only thing that differs between runs. Synthetic patient. **Model output shown as a research artefact demonstrating error propagation — not clinical advice.**

## 300 dpi — all 13 values read correctly

Values wrong at this quality: **0 / 13**

<details><summary>Laboratory values given to the model</summary>

```
  Glucose (fasting): 248 mg/dL FLAG: High
  HbA1c: 9.2 % FLAG: High
  Hemoglobin: 9.4 g/dL FLAG: Low
  Ferritin: 9 ng/mL FLAG: Low
  WBC: 7.4 10^9/L
  Platelets: 262 10^9/L
  Sodium: 133 mEq/L FLAG: Low
  Potassium: 5.8 mEq/L FLAG: High
  BUN: 42 mg/dL FLAG: High
  Creatinine: 2.1 mg/dL FLAG: High
  eGFR: 26 mL/min/1.73m2 FLAG: Low
  Troponin I: 0.07 ng/mL FLAG: Critical
  LDL cholesterol: 142 mg/dL FLAG: High
```
</details>

**Generated recommendation:**

> I've reviewed the patient's current medications against the laboratory results. Based on the provided information, I recommend the following adjustments:
> 
> 1. **Metformin 1000 mg PO twice daily**: The patient's eGFR is 26 mL/min/1.73m2, which is low. Metformin is primarily excreted by the kidneys, and dose adjustment is recommended in patients with reduced kidney function. I recommend reducing the dose to 500 mg PO twice daily.
> 2. **Lisinopril 20 mg PO daily**: The patient's potassium level is 5.8 mEq/L, which is high. Lisinopril is an ACE inhibitor that can increase potassium levels. I recommend holding lisinopril until the potassium level returns to normal.
> 3. **Amlodipine 10 mg PO daily**: The patient's potassium level is 5.8 mEq/L, which is high. Amlodipine can also increase potassium levels. I recommend holding amlodipine until the potassium level returns to normal.
> 4. **Atorvastatin 40 mg PO daily**: The patient's LDL cholesterol is 142 mg/dL, which is high. Atorvastatin is a statin that can increase the risk of muscle damage. I recommend monitoring the patient's muscle function and considering alternative statins if necessary.
> 
> I do not recommend adjusting or stopping the other medications based on the provided laboratory results.

---

## 150 dpi — 2 of 13 values wrong

Values wrong at this quality: **2 / 13**

<details><summary>Laboratory values given to the model</summary>

```
  Glucose (fasting): 248 mg/dL FLAG: High
  HbA1c: 9.2 % FLAG: High
  Hemoglobin: 9.4 g/dL FLAG: Low
  Ferritin: 9 ng/mL FLAG: Low
  WBC: 74 10^9/L FLAG: High
  Platelets: 262 10^9/L
  Sodium: 133 mEq/L FLAG: Low
  Potassium: 5.8 mEq/L FLAG: High
  BUN: 42 mg/dL FLAG: High
  Creatinine: 21 mg/dL FLAG: High
  eGFR: 26 mL/min/1.73m2 FLAG: Low
  Troponin I: 0.07 ng/mL FLAG: Critical
  LDL cholesterol: 142 mg/dL FLAG: High
```
</details>

**Generated recommendation:**

> I've reviewed the patient's current medications against the laboratory results. Based on the provided information, I recommend the following adjustments:
> 
> 1. **Metformin 1000 mg PO twice daily**: The patient's eGFR is 26 mL/min/1.73m2, which is low. Metformin is primarily excreted by the kidneys, and its dose should be adjusted in patients with impaired renal function. I recommend reducing the dose to 500 mg PO twice daily to minimize the risk of lactic acidosis.
> 2. **Lisinopril 20 mg PO daily**: The patient's potassium level is 5.8 mEq/L, which is high. Lisinopril is an ACE inhibitor that can increase potassium levels. I recommend holding lisinopril until the potassium level returns to normal.
> 3. **Amlodipine 10 mg PO daily**: The patient's potassium level is also high. Amlodipine can also increase potassium levels. I recommend holding amlodipine until the potassium level returns to normal.
> 4. **Atorvastatin 40 mg PO daily**: The patient's LDL cholesterol is 142 mg/dL, which is high. Atorvastatin is a statin that can increase the risk of muscle damage. I recommend monitoring the patient's muscle enzymes and considering alternative statins if necessary.
> 
> I do not recommend adjusting or stopping the other medications based on the provided laboratory results.

---

## 100 dpi — 4 of 13 values wrong

Values wrong at this quality: **4 / 13**

<details><summary>Laboratory values given to the model</summary>

```
  Glucose (fasting): 248 mg/dL FLAG: High
  HbA1c: NOT READ
  Hemoglobin: 94 g/dL FLAG: High
  Ferritin: 9 ng/mL FLAG: Low
  WBC: 74 10^9/L FLAG: High
  Platelets: 262 10^9/L
  Sodium: 133 mEq/L FLAG: Low
  Potassium: 58 mEq/L FLAG: High
  BUN: 42 mg/dL FLAG: High
  Creatinine: 24 mg/dL FLAG: High
  eGFR: 26 mL/min/1.73m2 FLAG: Low
  Troponin I: 0.07 ng/mL FLAG: Critical
  LDL cholesterol: 142 mg/dL FLAG: High
```
</details>

**Generated recommendation:**

> I've reviewed the patient's current medications against the laboratory results. Based on the provided information, I recommend the following adjustments:
> 
> 1. **Metformin 1000 mg PO twice daily**: The patient's eGFR is 26 mL/min/1.73m2, which is low. Metformin is contraindicated in patients with severe kidney disease. **STOP METFORMIN IMMEDIATELY**.
> 2. **Lisinopril 20 mg PO daily**: The patient's eGFR is 26 mL/min/1.73m2, which is low. Lisinopril is a potassium-sparing diuretic, and the patient's potassium level is 58 mEq/L, which is high. **DOSE-ADJUST LISINOPRIL TO MINIMIZE POTASSIUM RISKS**.
> 3. **Amlodipine 10 mg PO daily**: The patient's eGFR is 26 mL/min/1.73m2, which is low. Amlodipine is also a potassium-sparing diuretic, and the patient's potassium level is 58 mEq/L, which is high. **DOSE-ADJUST AMLODIPINE TO MINIMIZE POTASSIUM RISKS**.
> 4. **Atorvastatin 40 mg PO daily**: The patient's LDL cholesterol is 142 mg/dL, which is high. However, there is no direct contraindication or interaction with the patient's kidney function or potassium levels. **NO ADJUSTMENT NEEDED**.
> 5. **Ibuprofen 400 mg PO three times daily PRN**: The patient's WBC count is 74 10^9/L, which is high. Ibuprofen can exacerbate thrombocytopenia. **STOP IBUPROFEN UNTIL WBC COUNT NORMALIZES**.
> 6. **Ferrous sulfate 325 mg PO daily**: The patient's ferritin level is 9 ng/mL, which is low

---
