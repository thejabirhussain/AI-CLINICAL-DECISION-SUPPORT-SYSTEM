"""Numeric verification for extracted lab values.

Measured motivation (numeric-ocr/ in this repo): on degraded scans most misread lab values are decimal-point losses
(creatinine 2.1 -> 21), and most of those keep the same abnormal flag, so the reference-range check cannot see them.
At low resolution the decimal point disappears from the printed reference range too ("0.6-1.2" -> "06-12"), so a
check against the row's own range fails as well. These checks use knowledge from outside the OCR text, or a second
reading of it:

  source_row   the value the LLM extracted must match the first number on the source row (catches LLM rewriting
               and rows where the result cell was unreadable and only the reference range survived)
  precision    analytes conventionally reported with a decimal point must carry one
  magnitude    a value far above the reference window that a decimal shift would explain (narrow-range analytes only)

A failed check never changes the value or its clinical flag; it marks the lab for verification against the source.
"""

from __future__ import annotations

import difflib
import re
from typing import Any, Dict, List, Optional, Tuple

# Substring keys, as in ClinicalParser.reference_ranges. Analytes that labs print with at least one decimal place.
DECIMAL_ANALYTES = ("a1c", "hba1c", "glycated", "hemoglobin", "hematocrit", "wbc", "white blood", "potassium",
                    "creatinine", "troponin", "calcium", "magnesium", "albumin", "bilirubin", "inr", "tsh",
                    "lactate", "phosphorus")

NUMBER = re.compile(r"[-+]?\d+(?:[.,]\d+)?")
RANGE_AFTER = re.compile(r"^\s*(?:[-–=~]\s*|to\s+)\d")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def find_source_row(text: str, test_name: str) -> Tuple[Optional[str], str]:
    """Return (first numeric token after the label, line) for the best-matching row, as the study's row parser does:
    fuzzy label match on the first 1-4 tokens, preferring rows that carry two or more numbers (result + range)."""
    target = _norm(test_name)
    if not target:
        return None, ""
    best = None
    for line in text.splitlines():
        toks = line.replace("|", " ").split()
        for k in range(1, min(4, len(toks)) + 1):
            cand = _norm("".join(toks[:k]))
            if not cand:
                continue
            ratio = difflib.SequenceMatcher(None, target, cand).ratio()
            if ratio < 0.62:
                continue
            nums = [m.group() for t in toks[k:] for m in [NUMBER.match(t.lstrip("<>~*:"))] if m]
            if not nums:
                continue
            key = (len(nums) >= 2, ratio)
            if best is None or key > best[0]:
                best = (key, nums[0], line.strip())
    return (best[1], best[2]) if best else (None, "")


def _is_range_start(line: str, token: str) -> bool:
    idx = line.find(token)
    while idx != -1:
        if RANGE_AFTER.match(line[idx + len(token):]):
            return True
        idx = line.find(token, idx + 1)
    return False


def verify_lab(lab: Dict[str, Any], num_val: float, matched_key: Optional[str], ref: Optional[Dict[str, Any]],
               plausible_hi: Optional[float], raw_text: str) -> List[str]:
    reasons: List[str] = []
    token, line = find_source_row(raw_text, str(lab.get("test_name", "")))
    if line:
        lab["source_line"] = line[:160]
    if token is not None:
        src_val = float(token.replace(",", "."))
        if abs(src_val - num_val) > 1e-9:
            reasons.append(f"extracted {num_val:g} but the source row reads {token}")
        elif _is_range_start(line, token):
            reasons.append("the result cell looks unreadable; this number starts the reference range")
    shown = token if token is not None else str(lab.get("value", ""))
    if matched_key in DECIMAL_ANALYTES and "." not in shown and "," not in shown:
        reasons.append(f"{lab.get('test_name')} is reported with a decimal point; '{shown}' has none (possible lost decimal)")
    if ref and plausible_hi is not None and plausible_hi < 50 * ref["max"]:
        window_hi, window_lo = 4 * ref["max"], ref["min"] / 4
        if num_val > window_hi:
            for k in (1, 2, 3):
                if window_lo <= num_val / 10 ** k <= window_hi:
                    reasons.append(f"{num_val:g} is far above range; {num_val / 10 ** k:g} would fit (possible decimal shift)")
                    break
    return reasons
