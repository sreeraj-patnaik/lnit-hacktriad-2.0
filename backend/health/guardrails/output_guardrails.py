import re
from typing import Any

from .safety_language import validate_language


TEXT_FIELDS = (
    "comprehensive_narrative",
    "mentor_summary",
    "trend_analysis",
    "doctor_summary",
)


def run_output_guardrails(
    ai_output: dict[str, Any],
    parameters: list[dict[str, Any]],
    input_confidence: float = 1.0,
) -> dict[str, Any]:
    output = dict(ai_output or {})
    language_meta = {}

    for field in TEXT_FIELDS:
        safe_text, meta = validate_language(str(output.get(field, "") or ""))
        output[field] = safe_text
        language_meta[field] = meta

    claims = validate_claims(" ".join(str(output.get(field, "") or "") for field in TEXT_FIELDS), parameters)
    confidence_label = calculate_confidence(input_confidence=input_confidence, claim_result=claims)

    output["guardrail_meta"] = {
        "language_validation": language_meta,
        "claim_validation": claims,
        "confidence": confidence_label,
        "input_confidence": round(float(input_confidence), 2),
    }

    if claims["hallucination_detected"]:
        caution = (
            " Some generated claims could not be verified against extracted lab values, "
            "so this summary should be reviewed carefully with a clinician."
        )
        output["mentor_summary"] = (output.get("mentor_summary") or "").strip() + caution
        output["trend_analysis"] = (output.get("trend_analysis") or "").strip() + caution

    return output


def validate_claims(text: str, parameters: list[dict[str, Any]]) -> dict[str, Any]:
    content = str(text or "")
    found = _extract_numbers(content)
    allowed = _allowed_values(parameters)
    if not found:
        return {
            "hallucination_detected": False,
            "number_count": 0,
            "unmatched_count": 0,
            "mismatch_ratio": 0.0,
        }

    unmatched = 0
    for value in found:
        if not _matches_allowed(value, allowed):
            unmatched += 1

    ratio = round(unmatched / len(found), 2)
    return {
        "hallucination_detected": ratio > 0.45 and len(found) >= 4,
        "number_count": len(found),
        "unmatched_count": unmatched,
        "mismatch_ratio": ratio,
    }


def calculate_confidence(input_confidence: float, claim_result: dict[str, Any]) -> str:
    base = max(0.0, min(1.0, float(input_confidence)))
    mismatch_penalty = float(claim_result.get("mismatch_ratio", 0.0))
    score = base * (1.0 - min(0.75, mismatch_penalty))
    if score >= 0.75:
        return "HIGH"
    if score >= 0.45:
        return "MEDIUM"
    return "LOW"


def _extract_numbers(text: str) -> list[float]:
    values = []
    for token in re.findall(r"[-+]?\d*\.?\d+", text or ""):
        try:
            number = float(token)
        except ValueError:
            continue
        # Ignore likely year stamps and list numbering noise.
        if 1900 <= number <= 2200:
            continue
        values.append(number)
    return values


def _allowed_values(parameters: list[dict[str, Any]]) -> list[float]:
    allowed = []
    for item in parameters or []:
        for key in ("value", "ref_min", "ref_max"):
            value = item.get(key)
            if value is None:
                continue
            try:
                allowed.append(float(value))
            except (TypeError, ValueError):
                continue
    return allowed


def _matches_allowed(value: float, allowed: list[float]) -> bool:
    for candidate in allowed:
        tolerance = max(0.2, abs(candidate) * 0.06)
        if abs(value - candidate) <= tolerance:
            return True
    return False
