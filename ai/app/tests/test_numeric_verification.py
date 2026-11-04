"""Tests for numeric verification of extracted lab values.

Each failing case is a real OCR or VLM output from numeric-ocr/results (study document or held-out reports).
A verification mark must never change the value or its clinical flag.
"""

from unittest.mock import patch

import pytest

from app.ingestion.clinical_parser import ClinicalParser

CLEAN_REPORT = """Laboratory Results (09/17/2026)
Test                Result   Units          Reference      Flag
Glucose (fasting)   248      mg/dL          70 - 99        H
HbA1c               9.2      %              4.0 - 5.6      H
Hemoglobin          9.4      g/dL           12.0 - 15.5    L
Ferritin            9        ng/mL          15 - 200       L
WBC                 7.4      10^9/L         4.5 - 11.0
Platelets           262      10^9/L         150 - 450
Sodium              133      mEq/L          135 - 145      L
Potassium           5.8      mEq/L          3.5 - 5.0      H
BUN                 42       mg/dL          7 - 20         H
Creatinine          2.1      mg/dL          0.6 - 1.2      H
eGFR                26       mL/min/1.73m2  > 60           L
Troponin I          0.07     ng/mL          0.00 - 0.04    H
LDL cholesterol     142      mg/dL          < 100          H
"""


@pytest.fixture
def parser():
    with patch("app.ingestion.clinical_parser.get_llm_provider", return_value=None):
        yield ClinicalParser()


def _lab(parser, name, value, raw_text):
    out = parser._detect_abnormal_labs([{"test_name": name, "value": value}], raw_text=raw_text)
    assert len(out) == 1
    return out[0]


def test_clean_report_raises_no_verification(parser):
    """No false alarms on correctly read values, including the abnormal ones."""
    values = {"Glucose (fasting)": 248, "HbA1c": 9.2, "Hemoglobin": 9.4, "Ferritin": 9, "WBC": 7.4,
              "Platelets": 262, "Sodium": 133, "Potassium": 5.8, "BUN": 42, "Creatinine": 2.1, "eGFR": 26,
              "Troponin I": 0.07, "LDL cholesterol": 142}
    for name, v in values.items():
        lab = _lab(parser, name, v, CLEAN_REPORT)
        assert not lab.get("needs_verification"), (name, lab.get("verification_reasons"))


def test_lost_decimal_point_keeps_flag_but_needs_verification(parser):
    """Creatinine 2.1 read as 21 at 150 dpi: still 'High', so the range check alone is silent."""
    row = "Creatinine            21         mg/dL              06-12       H"
    lab = _lab(parser, "Creatinine", "21", row)
    assert lab["flag"] == "High"
    assert lab["value"] == "21"
    assert lab["needs_verification"]
    assert any("decimal" in r for r in lab["verification_reasons"])


def test_wbc_decimal_shift_caught_by_precision_and_magnitude(parser):
    row = "WBC                 74        10°9/L.              4.5-11.0"
    reasons = _lab(parser, "WBC", "74", row)["verification_reasons"]
    assert any("decimal point" in r for r in reasons)
    assert any("7.4 would fit" in r for r in reasons)


def test_llm_rewrite_against_source_row(parser):
    """The extractor (LLM or VLM) reports a value the source row does not contain."""
    lab = _lab(parser, "Potassium", 3.6, "Potassium           5.8      mEq/L          3.5 - 5.0      H")
    assert lab["needs_verification"]
    assert any("source row reads 5.8" in r for r in lab["verification_reasons"])


def test_unreadable_result_falls_through_to_reference_range(parser):
    """'INR aril 0.8 - 1.2': the only number left on the row is the range's lower bound."""
    lab = _lab(parser, "INR", 0.8, "INR                                     aril              0.8 - 1.2")
    assert lab["needs_verification"]
    assert any("reference range" in r for r in lab["verification_reasons"])


def test_true_extreme_troponin_is_not_called_a_decimal_shift(parser):
    """Troponin has a wide true dynamic range; a real infarct value must not be second-guessed."""
    lab = _lab(parser, "Troponin I", 5.0, "Troponin I     5.00    ng/mL    0.00 - 0.04    H")
    assert lab["flag"] == "Critical"
    assert not lab.get("needs_verification")


def test_true_extreme_low_is_not_flagged(parser):
    lab = _lab(parser, "eGFR", 3, "eGFR      3      mL/min/1.73m2      > 60      L")
    assert lab["flag"] == "Low"
    assert not lab.get("needs_verification")


def test_without_raw_text_behaviour_is_unchanged(parser):
    lab = parser._detect_abnormal_labs([{"test_name": "Creatinine", "value": "21"}])[0]
    assert lab["flag"] == "High"
    assert "needs_verification" not in lab


def test_ocr_misread_analyte_name_still_gets_its_range(parser):
    """'HbA1c' read as 'HbAic' at 100 dpi must still be judged against the HbA1c range."""
    assert _lab(parser, "HbAic", "9.2", "HbAic   9.2   %   4.0 - 5.6   H")["flag"] == "High"
    assert _lab(parser, "Ferntin", "9", "Ferntin   9   ng/mL   15 - 200   L")["flag"] == "Low"
    assert _lab(parser, "Troponin |", "0.07", "Troponin |   0.07   ng/mL   0.00 - 0.04   H")["flag"] == "Critical"
