import os
from typing import Any


MIN_PARAMETERS = 3
MIN_IMAGE_BYTES = 20 * 1024
MIN_IMAGE_DIMENSION = 700


def run_input_guardrails(report, extracted_data: list[dict]) -> dict[str, Any]:
    image_result = _check_image_quality(report)
    completeness_result = _check_data_completeness(extracted_data)
    ocr_result = _check_ocr_confidence(extracted_data)

    checks = [image_result, completeness_result, ocr_result]
    safe = all(item["safe"] for item in checks)
    reasons = [item["reason"] for item in checks if item["reason"]]

    confidence = round(sum(item["confidence"] for item in checks) / len(checks), 2)
    return {
        "safe": safe,
        "reason": " | ".join(reasons) if reasons else "",
        "confidence": confidence,
        "checks": checks,
    }


def _check_image_quality(report) -> dict[str, Any]:
    if not getattr(report, "report_file", None):
        return {
            "name": "image_quality",
            "safe": True,
            "reason": "",
            "confidence": 1.0,
            "meta": {"mode": "text"},
        }

    file_name = (report.report_file.name or "").lower()
    if not _looks_like_image(file_name):
        return {
            "name": "image_quality",
            "safe": True,
            "reason": "",
            "confidence": 1.0,
            "meta": {"mode": "non-image-upload"},
        }

    try:
        file_size = os.path.getsize(report.report_file.path)
    except OSError:
        return {
            "name": "image_quality",
            "safe": False,
            "reason": "Image file could not be read.",
            "confidence": 0.0,
            "meta": {"mode": "image"},
        }

    min_dimension_ok = True
    width = None
    height = None
    try:
        from PIL import Image

        with Image.open(report.report_file.path) as image:
            width, height = image.size
        min_dimension_ok = bool(width and height and min(width, height) >= MIN_IMAGE_DIMENSION)
    except Exception:
        # PIL can be unavailable in lean environments; keep this check optional.
        min_dimension_ok = True

    safe = file_size >= MIN_IMAGE_BYTES and min_dimension_ok
    reason = ""
    if not safe:
        reason = "Please upload a clearer report image with better resolution."
    confidence = 1.0 if safe else 0.2
    return {
        "name": "image_quality",
        "safe": safe,
        "reason": reason,
        "confidence": confidence,
        "meta": {"mode": "image", "file_size": file_size, "width": width, "height": height},
    }


def _check_data_completeness(extracted_data: list[dict]) -> dict[str, Any]:
    count = len(extracted_data or [])
    unit_present = len([row for row in extracted_data or [] if str(row.get("unit") or "").strip()])
    refs_present = len(
        [
            row
            for row in extracted_data or []
            if row.get("ref_min") is not None and row.get("ref_max") is not None
        ]
    )

    count_ok = count >= MIN_PARAMETERS
    unit_ratio = (unit_present / count) if count else 0.0
    ref_ratio = (refs_present / count) if count else 0.0
    safe = bool(count_ok and unit_ratio >= 0.3 and ref_ratio >= 0.3)
    reason = ""
    if not safe:
        reason = "Report data is incomplete. Add clearer values, units, and reference ranges."
    confidence = round(min(1.0, ((unit_ratio + ref_ratio) / 2.0)), 2) if count else 0.0
    return {
        "name": "data_completeness",
        "safe": safe,
        "reason": reason,
        "confidence": confidence,
        "meta": {
            "parameter_count": count,
            "unit_ratio": round(unit_ratio, 2),
            "reference_ratio": round(ref_ratio, 2),
        },
    }


def _check_ocr_confidence(extracted_data: list[dict]) -> dict[str, Any]:
    count = len(extracted_data or [])
    if count == 0:
        return {
            "name": "ocr_confidence",
            "safe": False,
            "reason": "OCR confidence is too low to proceed.",
            "confidence": 0.0,
            "meta": {"estimated_ocr_confidence": 0.0},
        }

    numeric_ok = len([row for row in extracted_data if row.get("value") is not None]) / count
    named_ok = len([row for row in extracted_data if str(row.get("name") or "").strip()]) / count
    confidence = round(((numeric_ok * 0.7) + (named_ok * 0.3)), 2)
    safe = confidence >= 0.65
    reason = "" if safe else "OCR confidence is below threshold. Please upload a clearer image."
    return {
        "name": "ocr_confidence",
        "safe": safe,
        "reason": reason,
        "confidence": confidence,
        "meta": {"estimated_ocr_confidence": confidence},
    }


def _looks_like_image(file_name: str) -> bool:
    return file_name.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp"))
