"""Clinical Document Parsing and Structured Extraction."""

import json
import logging
import re
from typing import Any, Dict, List

from app.generation.llm import get_llm_provider

logger = logging.getLogger(__name__)


class ClinicalParser:
    """Parses raw clinical text into structured patient data."""

    def __init__(self):
        self.llm_provider = get_llm_provider()

        # Hardcoded reference ranges for MVP abnormal detection
        self.reference_ranges = {
            "glucose": {"min": 70, "max": 99, "unit": "mg/dL"},
            "hba1c": {"min": 4.0, "max": 5.6, "unit": "%"},
            "hemoglobin": {"min": 12.0, "max": 17.5, "unit": "g/dL"},
            "wbc": {"min": 4.5, "max": 11.0, "unit": "10^9/L"},
            "platelets": {"min": 150, "max": 450, "unit": "10^9/L"},
            "sodium": {"min": 135, "max": 145, "unit": "mEq/L"},
            "potassium": {"min": 3.5, "max": 5.0, "unit": "mEq/L"},
            "creatinine": {"min": 0.6, "max": 1.2, "unit": "mg/dL"},
            "bun": {"min": 7, "max": 20, "unit": "mg/dL"},
            "troponin": {"min": 0.0, "max": 0.04, "unit": "ng/mL"}
        }

    def parse_document(self, text: str) -> Dict[str, Any]:
        """
        Extract structured demographics, diagnoses, meds, labs, and history
        using an LLM to parse the raw OCR/PDF text.
        """
        prompt = f"""
You are an expert Clinical Data Extractor. Extract the following information from the provided raw clinical document text.
Return ONLY a valid JSON object with the exact schema below. If a field is missing, use null or an empty array [].

SCHEMA:
{{
    "demographics": {{
        "age": (integer or null),
        "gender": (string or null)
    }},
    "active_problems": [(array of strings)],
    "medications": [(array of strings)],
    "allergies": [(array of strings)],
    "labs": [
        {{
            "test_name": (string, e.g., "Glucose", "Hemoglobin"),
            "value": (float or string),
            "unit": (string or null)
        }}
    ],
    "unstructured_narrative": (string, a brief 2-3 sentence summary of the history and physical context found in the doc)
}}

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
            
            # Clean possible markdown formatting
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
                
            data = json.loads(cleaned_response)
            
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
        for lab in labs:
            test_name = lab.get("test_name", "").lower()
            val = lab.get("value")
            
            lab["flag"] = "Normal" # Default
            
            if val is not None:
                # Try to cast value to float
                try:
                    num_val = float(re.sub(r'[^\d.]', '', str(val)))
                except ValueError:
                    processed_labs.append(lab)
                    continue

                # Check against standard ranges if we know the test
                matched_key = None
                for key in self.reference_ranges:
                    if key in test_name:
                        matched_key = key
                        break
                        
                if matched_key:
                    ref = self.reference_ranges[matched_key]
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
