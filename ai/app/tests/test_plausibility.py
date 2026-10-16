"""Tests for the physiological plausibility check in the clinical parser.

A value outside the plausibility envelope must be reported as a suspect
READING, not as an extreme clinical finding. Flagging an impossible value
"High" hides the error behind a correct-looking alarm.
"""

from unittest.mock import patch

import pytest

from app.ingestion.clinical_parser import ClinicalParser


@pytest.fixture
def parser():
    with patch("app.ingestion.clinical_parser.get_llm_provider", return_value=None):
        yield ClinicalParser()


def _flag(parser, name, value, unit=""):
    out = parser._detect_abnormal_labs(
        [{"test_name": name, "value": value, "unit": unit}])
    assert len(out) == 1
    return out[0]


def test_true_values_keep_their_clinical_flags(parser):
    """The undegraded demo report must flag exactly as before."""
    assert _flag(parser, "Potassium", "5.8")["flag"] == "High"
    assert _flag(parser, "Sodium", "133")["flag"] == "Low"
    assert _flag(parser, "Troponin I", "0.07")["flag"] == "Critical"
    assert _flag(parser, "WBC", "7.4")["flag"] == "Normal"
    assert _flag(parser, "Creatinine", "2.1")["flag"] == "High"


@pytest.mark.parametrize(
    "name,value",
    [
        ("Potassium", "58"),      # 5.8 with the decimal point lost
        ("Hemoglobin", "94"),     # 9.4 with the decimal point lost
        ("HbA1c", "92"),          # 9.2 with the decimal point lost
        ("Sodium", "1330"),       # 133 with a digit duplicated
    ],
)
def test_impossible_values_are_flagged_implausible_not_high(parser, name, value):
    lab = _flag(parser, name, value)
    assert lab["flag"] == "Implausible", (
        f"{name} {value} was flagged {lab['flag']!r}; an impossible value must "
        "not be reported as an ordinary clinical abnormality")
    assert lab["needs_verification"] is True
    assert "plausible_range" in lab


def test_plausible_but_abnormal_values_are_not_suppressed(parser):
    """The check must not swallow genuine extremes that are survivable.

    These are the documented blind spots. Measured on the fault-injection
    corpus, the plausibility bound converts 9 of 28 silent corruptions into
    visible ones; the other 19 look like this.
    """
    # 2.1 read as 21 is a tenfold error, but 21 mg/dL is reachable in severe
    # renal failure, so no plausibility bound can catch it.
    assert _flag(parser, "Creatinine", "21")["flag"] == "High"
    # 0.07 read as 7.0 is a hundredfold error, but troponin I really does reach
    # 7 ng/mL in a large myocardial infarction. Uncatchable.
    assert _flag(parser, "Troponin I", "7.0")["flag"] == "Critical"
    # 26 read as 2 is a tenfold error; an eGFR of 2 is survivable on dialysis.
    assert _flag(parser, "eGFR", "2")["flag"] == "Low"
    # 9 read as 15 lands inside the reference range; also uncatchable.
    assert _flag(parser, "Ferritin", "15")["flag"] == "Normal"


def test_unknown_tests_are_reported_as_not_assessed(parser):
    assert _flag(parser, "Serum copper", "1.2")["flag"] == "Not assessed"
