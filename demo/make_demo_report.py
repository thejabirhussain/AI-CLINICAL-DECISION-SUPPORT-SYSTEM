"""Render the synthetic demo patient report (demo/patient_report_maria_alvarez.pdf).

Needs PyMuPDF, which the API container has:
    docker cp demo/make_demo_report.py ai-cdss-api:/tmp/ && \
    docker exec ai-cdss-api python /tmp/make_demo_report.py /app/data/report.pdf && \
    cp ai/data/report.pdf demo/patient_report_maria_alvarez.pdf
"""
import sys

import fitz  # PyMuPDF

OUT = sys.argv[1] if len(sys.argv) > 1 else "/app/data/demo_patient_report.pdf"

LABS = [
    # test, result, units, reference, flag
    ("Glucose (fasting)", "248", "mg/dL", "70 - 99", "H"),
    ("HbA1c", "9.2", "%", "4.0 - 5.6", "H"),
    ("Hemoglobin", "9.4", "g/dL", "12.0 - 15.5", "L"),
    ("Ferritin", "9", "ng/mL", "15 - 200", "L"),
    ("WBC", "7.4", "10^9/L", "4.5 - 11.0", ""),
    ("Platelets", "262", "10^9/L", "150 - 450", ""),
    ("Sodium", "133", "mEq/L", "135 - 145", "L"),
    ("Potassium", "5.8", "mEq/L", "3.5 - 5.0", "H"),
    ("BUN", "42", "mg/dL", "7 - 20", "H"),
    ("Creatinine", "2.1", "mg/dL", "0.6 - 1.2", "H"),
    ("eGFR", "26", "mL/min/1.73m2", "> 60", "L"),
    ("Troponin I", "0.07", "ng/mL", "0.00 - 0.04", "H"),
    ("LDL cholesterol", "142", "mg/dL", "< 100", "H"),
]

rows = "".join(
    f"<tr><td>{t}</td><td class='num{' ab' if f else ''}'>{r}</td><td>{u}</td><td>{ref}</td>"
    f"<td class='flag'>{f}</td></tr>"
    for t, r, u, ref, f in LABS
)

HTML = f"""
<div class="banner">SYNTHETIC PATIENT RECORD &#8212; FOR DEMONSTRATION ONLY. NOT A REAL PERSON.</div>
<h1>Riverside General Hospital &#8212; Discharge Summary</h1>
<table class="demo">
<tr><td><b>Patient:</b> Maria Alvarez (synthetic)</td><td><b>MRN:</b> DEMO-240917</td></tr>
<tr><td><b>Age / Sex:</b> 64-year-old Female</td><td><b>Attending:</b> Internal Medicine</td></tr>
<tr><td><b>Admitted:</b> 09/14/2026</td><td><b>Discharged:</b> 09/18/2026</td></tr>
</table>

<h2>Chief Complaint</h2>
<p>Progressive fatigue, shortness of breath on exertion and intermittent chest tightness for 3 weeks.</p>

<h2>History of Present Illness</h2>
<p>64-year-old woman with long-standing type 2 diabetes, hypertension and chronic kidney disease who presented with
3 weeks of worsening fatigue, exertional dyspnea and two episodes of chest tightness at rest lasting under 10 minutes.
She reports ankle swelling and taking ibuprofen several times daily for knee osteoarthritis. ECG showed sinus rhythm
without acute ST changes. Troponin I was mildly elevated and stable on repeat. Hemoglobin and ferritin were low.
Potassium was elevated on admission and treated.</p>

<h2>Active Problems / Past Medical History</h2>
<ul>
<li>Type 2 diabetes mellitus (12 years), poorly controlled</li>
<li>Chronic kidney disease, stage 4 (baseline creatinine 1.8)</li>
<li>Essential hypertension</li>
<li>Iron deficiency anemia</li>
<li>Hyperlipidemia</li>
<li>Osteoarthritis of both knees</li>
</ul>

<h2>Allergies</h2>
<p>Sulfa drugs (rash); Penicillin (hives)</p>

<h2>Current Medications</h2>
<ul>
<li>Metformin 1000 mg PO twice daily</li>
<li>Lisinopril 20 mg PO daily</li>
<li>Amlodipine 10 mg PO daily</li>
<li>Atorvastatin 40 mg PO daily</li>
<li>Ibuprofen 400 mg PO three times daily as needed for knee pain</li>
<li>Ferrous sulfate 325 mg PO daily</li>
</ul>

<h2>Laboratory Results (09/17/2026)</h2>
<table class="labs">
<tr><th>Test</th><th>Result</th><th>Units</th><th>Reference</th><th>Flag</th></tr>
{rows}
</table>

<h2>Vitals at Discharge</h2>
<p>BP 158/92 mmHg, HR 88, SpO2 96% on room air, weight 82 kg, BMI 31.</p>

<h2>Discharge Plan</h2>
<p>Follow up with primary care and nephrology in 1 week. Repeat BMP in 3 days. Cardiology referral for outpatient
stress testing. Medication review requested.</p>
"""

CSS = """
* { font-family: sans-serif; }
body { font-size: 9.5pt; color: #1f1f1f; }
.banner { background-color: #fde8e8; color: #9b1c1c; font-size: 8pt; font-weight: bold; padding: 4px; text-align: center; }
h1 { font-size: 14pt; color: #000db5; margin: 8px 0 4px 0; }
h2 { font-size: 10.5pt; color: #000db5; margin: 10px 0 3px 0; border-bottom: 1px solid #d0d4e8; }
p { margin: 2px 0; line-height: 1.35; }
ul { margin: 2px 0 2px 14px; }
li { margin: 0; }
table.demo td { padding: 2px 16px 2px 0; }
table.labs { border-collapse: collapse; width: 100%; }
table.labs th { background-color: #eef0ff; text-align: left; padding: 3px 6px; font-size: 9pt; }
table.labs td { border-bottom: 1px solid #e5e5e5; padding: 2px 6px; font-size: 9pt; }
td.ab { font-weight: bold; }
td.flag { color: #b91c1c; font-weight: bold; }
"""

story = fitz.Story(html=HTML, user_css=CSS)
writer = fitz.DocumentWriter(OUT)
mediabox = fitz.paper_rect("letter")
where = mediabox + (48, 42, -48, -42)
more = True
while more:
    dev = writer.begin_page(mediabox)
    more, _ = story.place(where)
    story.draw(dev)
    writer.end_page()
writer.close()

doc = fitz.open(OUT)
text = "".join(p.get_text() for p in doc)
print(f"pages={doc.page_count} chars={len(text)}")
