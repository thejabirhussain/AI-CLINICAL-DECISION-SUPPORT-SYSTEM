"""Clinical Document Parsing and Structured Extraction."""

import json
import logging
import re
import unicodedata
from typing import Any, Dict, List

from app.generation.llm import get_llm_provider

logger = logging.getLogger(__name__)

VITALS_RE = re.compile(
    r"^\s*(bp|blood pressure|hr|heart rate|pulse|spo2|o2 sat|oxygen saturation|temp|temperature|rr|respiratory rate|"
    r"weight|height|bmi)\b",
    re.IGNORECASE,
)


class ClinicalParser:
    """Parses raw clinical text into structured patient data."""

    def __init__(self):
        self.llm_provider = get_llm_provider()

        # Hardcoded adult reference ranges for MVP abnormal detection.
        # Matched by substring in dict order, so more specific names come first ("a1c" before "hemoglobin").
        a1c = {"min": 4.0, "max": 5.6, "unit": "%"}
        bun = {"min": 7, "max": 20, "unit": "mg/dL"}
        wbc = {"min": 4.5, "max": 11.0, "unit": "10^9/L"}
        self.reference_ranges = {
            "a1c": a1c,
            "hba1c": a1c,
            "glycated": a1c,
            "glucose": {"min": 70, "max": 99, "unit": "mg/dL"},
            "hemoglobin": {"min": 12.0, "max": 17.5, "unit": "g/dL"},
            "wbc": wbc,
            "white blood": wbc,
            "platelet": {"min": 150, "max": 450, "unit": "10^9/L"},
            "sodium": {"min": 135, "max": 145, "unit": "mEq/L"},
            "potassium": {"min": 3.5, "max": 5.0, "unit": "mEq/L"},
            "creatinine": {"min": 0.6, "max": 1.2, "unit": "mg/dL"},
            "bun": bun,
            "urea nitrogen": bun,
            "egfr": {"min": 60, "max": 200, "unit": "mL/min/1.73m2"},
            "ferritin": {"min": 15, "max": 200, "unit": "ng/mL"},
            "ldl": {"min": 0, "max": 99, "unit": "mg/dL"},
            "troponin": {"min": 0.0, "max": 0.04, "unit": "ng/mL"},
        }

    def parse_document(self, text: str) -> Dict[str, Any]:
        """
        Extract structured demographics, diagnoses, meds, labs, and history
        using an LLM to parse the raw OCR/PDF text.
        """
        text = unicodedata.normalize("NFKC", text)  # PDF ligatures ("ﬁ") -> plain letters
        prompt = f"""
You are an expert Clinical Data Extractor. Extract the following information from the provided raw clinical document text.
Return ONLY a valid JSON object with the exact schema below. If a field is missing, use null or an empty array [].

SCHEMA:
{{
    "demographics": {{
        "age": (integer or null),
        "gender": (string or null)
    }},
    "active_problems": [(array of strings: DIAGNOSES / conditions from the problem list or past medical history, not symptoms)],
    "medications": [(array of strings: drug name WITH dose, route and frequency exactly as written, e.g. "Metformin 1000 mg PO twice daily")],
    "allergies": [(array of strings: allergen with reaction if given)],
    "labs": [
        {{
            "test_name": (string, e.g., "Glucose", "Hemoglobin"),
            "value": (float or string),
            "unit": (string or null)
        }}
    ],
    "unstructured_narrative": (string, a brief 2-3 sentence summary of the history and physical context found in the doc)
}}

RULES:
- Include EVERY laboratory result row in the document in "labs" (for example HbA1c, glucose, hemoglobin, ferritin, electrolytes, kidney function, troponin, lipids). Do not skip any.
- Each lab test appears ONCE, with its measured result. The reference range column is NOT a result.
- Vital signs (blood pressure, heart rate, SpO2, temperature, respiratory rate, weight, BMI) are NOT labs; do not put them in "labs".
- Copy values exactly; do not invent data that is not in the text.

RAW CLINICAL TEXT TO PARSE:
{text[:4000]}
"""

        try:
            # We use a lower temperature for extraction to keep JSON tight
            response = self.llm_provider.generate(
                prompt=prompt,
                system_prompt="You are a precise data extraction system. You only return valid JSON.",
                temperature=0.0,
                max_tokens=2500,
            )
            
            # Keep only the JSON object (local models often wrap it in prose or ``` fences)
            cleaned_response = response.strip()
            start, end = cleaned_response.find("{"), cleaned_response.rfind("}")
            if start != -1 and end > start:
                cleaned_response = cleaned_response[start : end + 1]

            data = json.loads(cleaned_response)
            for key in ("active_problems", "medications", "allergies", "labs"):
                if not isinstance(data.get(key), list):
                    data[key] = []
            
            # Post-process: Flag abnormal labs
            data["labs"] = self._detect_abnormal_labs(data.get("labs", []))
            return data

        except Exception as e:
            logger.error(f"Failed to parse clinical document: {e}")
            # Fallback to stuffing everything in narrative
            return {
                "demographics": {"age": None, "gender": None},
                "active_problems": [],
                "medications": [],
                "allergies": [],
                "labs": [],
                "unstructured_narrative": "Failed to parse document structurally. Raw content:\n" + text[:2000]
            }

    def _detect_abnormal_labs(self, labs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add flag to labs that fall outside generic reference ranges."""
        processed_labs = []
        seen = set()
        for lab in labs:
            if not isinstance(lab, dict) or not lab.get("test_name"):
                continue
            name_key = re.sub(r"[^a-z0-9]", "", str(lab["test_name"]).lower())
            # Drop vitals the model mislabels as labs, and repeated tests (e.g. a reference range read as a 2nd result)
            if VITALS_RE.search(str(lab["test_name"])) or name_key in seen:
                continue
            seen.add(name_key)
            test_name = lab.get("test_name", "").lower()
            val = lab.get("value")
            
            # Only tests we have a reference range for can be judged; others are reported as not assessed
            lab["flag"] = "Not assessed"
            
            if val is not None:
                # Use the first number in the value ("26 mL/min/1.73m2" -> 26, "<0.01" -> 0.01)
                match = re.search(r"\d+(?:\.\d+)?", str(val))
                if not match:
                    processed_labs.append(lab)
                    continue
                num_val = float(match.group())
                # Models often put the unit into the value ("248 mg/dL"); keep value numeric when a unit is given
                if isinstance(val, str) and lab.get("unit") and str(val).strip() != match.group():
                    lab["value"] = match.group()

                # Check against standard ranges if we know the test
                matched_key = None
                for key in self.reference_ranges:
                    if key in test_name:
                        matched_key = key
                        break
                        
                if matched_key:
                    ref = self.reference_ranges[matched_key]
                    lab["flag"] = "Normal"
                    if num_val < ref["min"]:
                        lab["flag"] = "Low"
                        lab["reference_range"] = f"{ref['min']}-{ref['max']} {ref['unit']}"
                    elif num_val > ref["max"]:
                        # Troponin gets a Critical flag, others get High
                        lab["flag"] = "Critical" if matched_key == "troponin" else "High"
                        lab["reference_range"] = f"{ref['min']}-{ref['max']} {ref['unit']}"
            
            processed_labs.append(lab)
        return processed_labs


def get_clinical_parser() -> ClinicalParser:
    return ClinicalParser()
