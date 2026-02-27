import base64
import json
import mimetypes
import os
import re

import requests
from django.conf import settings
from django.db import transaction

from core.models import UserProfile
from .models import AnalysisResult, LabParameter, MedicalReport


def process_report(report_id: int) -> AnalysisResult:
    report = MedicalReport.objects.select_related("user").get(id=report_id)
    extracted_data = run_ocr(report)

    with transaction.atomic():
        report.parameters.all().delete()
        for item in extracted_data:
            LabParameter.objects.create(
                report=report,
                name=item["name"],
                value=item["value"],
                unit=item.get("unit", ""),
                ref_min=item.get("ref_min"),
                ref_max=item.get("ref_max"),
                risk_flag=classify(item["value"], item.get("ref_min"), item.get("ref_max")),
            )

        context = prepare_llm_context(report)
        result = generate_analysis(context)
        analysis, _ = AnalysisResult.objects.update_or_create(
            report=report,
            defaults={
                "user": report.user,
                "mentor_summary": result.get("mentor_summary", ""),
                "trend_analysis": result.get("trend_analysis", ""),
                "doctor_summary": result.get("doctor_summary", ""),
                "raw_response": result,
            },
        )

        report.analysis_completed = True
        report.save(update_fields=["analysis_completed"])

    return analysis


def prepare_llm_context(report: MedicalReport) -> dict:
    user = report.user
    profile = UserProfile.objects.get(user=user)
    reports = (
        MedicalReport.objects.filter(user=user)
        .order_by("report_date", "created_at")
        .prefetch_related("parameters")
    )

    reports_data = []
    for report_item in reports:
        params = [
            {
                "name": p.name,
                "value": p.value,
                "unit": p.unit,
                "ref_min": p.ref_min,
                "ref_max": p.ref_max,
                "risk_flag": p.risk_flag,
            }
            for p in report_item.parameters.all()
        ]
        reports_data.append(
            {
                "report_id": report_item.id,
                "date": str(report_item.report_date),
                "parameter_count": len(params),
                "parameters": params,
            }
        )

    return {
        "current_report_id": report.id,
        "user_context": {
            "age": profile.age,
            "gender": profile.gender,
            "city": profile.city,
            "location_type": profile.location_type,
            "occupation": profile.occupation,
            "past_medical_conditions": profile.past_medical_conditions,
            "current_symptoms": profile.current_symptoms,
            "medications": profile.medications,
            "health_goal": profile.health_goal,
            "language_preference": profile.language_preference,
            "smoking_status": profile.smoking_status,
            "alcohol_consumption": profile.alcohol_consumption,
            "lifestyle": {
                "sleep_hours": profile.sleep_hours,
                "activity_level": profile.activity_level,
                "diet_type": profile.diet_type,
            },
        },
        "reports": reports_data,
    }


def generate_analysis(context: dict) -> dict:
    api_key = getattr(settings, "GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return fallback_analysis(context)

    model = getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant")
    prompt = f"""
You are a safety-first health trajectory interpreter.

Rules:
- Explain only from the provided data.
- No diagnosis and no medication advice.
- Use calm, actionable, non-alarming language.
- Mention trends, borderline concerns, and changes over time.
- Produce practical lifestyle guidance only.

Return ONLY valid JSON with this schema:
{{
  "mentor_summary": "plain-language explanation",
  "trend_analysis": "what is increasing/decreasing/stable",
  "doctor_summary": "concise handoff summary for doctor consultation"
}}

DATA:
{json.dumps(context, indent=2)}
"""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": "You are a medical education assistant."},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=40,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = _parse_json_response(content)
        if parsed is None:
            return fallback_analysis(context)
        return _ensure_analysis_shape(parsed, context)
    except Exception:
        return fallback_analysis(context)


def _parse_json_response(content: str) -> dict | None:
    value = (content or "").strip()
    if not value:
        return None

    if value.startswith("```"):
        value = value.strip("`")
        if value.startswith("json"):
            value = value[4:].strip()

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        start = value.find("{")
        end = value.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(value[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def fallback_analysis(context: dict) -> dict:
    reports = context.get("reports", [])
    latest_report = reports[-1] if reports else {"parameters": []}
    latest_params = latest_report.get("parameters", [])
    high = [p["name"] for p in latest_report.get("parameters", []) if p.get("risk_flag") == "high"]
    low = [p["name"] for p in latest_report.get("parameters", []) if p.get("risk_flag") == "low"]
    normal_count = len([p for p in latest_report.get("parameters", []) if p.get("risk_flag") == "normal"])

    trend_hint = _build_trend_hint(context)
    if not latest_params:
        mentor_summary = (
            "No lab parameters could be extracted from the latest upload. "
            "Please upload a clearer photo or paste report text in structured lines."
        )
    else:
        mentor_summary = (
            f"Your latest report has {normal_count} parameters in the normal range. "
            f"High markers: {', '.join(high) if high else 'none'}. "
            f"Low markers: {', '.join(low) if low else 'none'}. "
            "This is an educational summary and should be validated with your doctor."
        )

    return {
        "mentor_summary": mentor_summary,
        "trend_analysis": (
            f"{trend_hint} "
            "For richer narrative insight, set GROQ_API_KEY."
        ),
        "doctor_summary": (
            "Patient has longitudinal report history with profile context. "
            "Please review flagged high/low parameters against symptoms and history."
        ),
    }


def run_ocr(report: MedicalReport) -> list[dict]:
    # MVP parser:
    # 1) Use pasted/report text if provided
    # 2) Parse uploaded .txt file if available
    manual_text = (report.ocr_text or "").strip()
    if manual_text:
        parsed = _parse_lines_to_parameters(manual_text)
        if parsed:
            return parsed
        report.ocr_text = (
            "Provided text could not be parsed. "
            "Use one line per parameter like: Hemoglobin 11.2 g/dL 12-16"
        )
        report.save(update_fields=["ocr_text"])
        return []

    if report.report_file and report.report_file.name.lower().endswith(".txt"):
        try:
            with open(report.report_file.path, "r", encoding="utf-8", errors="ignore") as file_obj:
                file_text = file_obj.read()
            if not report.ocr_text:
                report.ocr_text = file_text[:10000]
                report.save(update_fields=["ocr_text"])
            parsed = _parse_lines_to_parameters(file_text)
            if parsed:
                return parsed
        except OSError:
            pass

    if report.report_file and _is_image_file(report.report_file.path):
        parsed, debug_message = _ocr_image_with_groq(report.report_file.path)
        if parsed:
            if not report.ocr_text:
                report.ocr_text = "\n".join(
                    [f"{p['name']} {p['value']} {p.get('unit', '')}".strip() for p in parsed]
                )
                report.save(update_fields=["ocr_text"])
            return parsed
        report.ocr_text = debug_message[:10000]
        report.save(update_fields=["ocr_text"])
        return []

    report.ocr_text = "No parseable text found from upload. Try a clearer image or paste report text."
    report.save(update_fields=["ocr_text"])
    return []


def _parse_lines_to_parameters(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        cleaned = " ".join(line.strip().split())
        if not cleaned:
            continue

        match = re.search(
            r"^(?P<name>[A-Za-z0-9\-\(\)\/\s]+?)\s+(?P<value>[-+]?\d*\.?\d+)\s*(?P<unit>[A-Za-z%\/0-9\^\.]*)\s*(?P<ref>[-+]?\d*\.?\d+\s*[-to]+\s*[-+]?\d*\.?\d+)?$",
            cleaned,
            re.IGNORECASE,
        )
        if not match:
            continue

        value = _to_float(match.group("value"))
        if value is None:
            continue
        ref_min = ref_max = None
        ref = match.group("ref") or ""
        ref_nums = re.findall(r"[-+]?\d*\.?\d+", ref)
        if len(ref_nums) >= 2:
            ref_min = _to_float(ref_nums[0])
            ref_max = _to_float(ref_nums[1])
        parsed_row = {
            "name": match.group("name").strip(),
            "value": value,
            "unit": (match.group("unit") or "").strip(),
            "ref_min": ref_min,
            "ref_max": ref_max,
        }
        rows.append(parsed_row)

    if rows:
        return rows

    # Secondary permissive parser for OCR text with loose formatting.
    for line in text.splitlines():
        cleaned = " ".join(line.strip().split())
        if not cleaned:
            continue
        nums = re.findall(r"[-+]?\d*\.?\d+", cleaned)
        if not nums:
            continue
        value = _to_float(nums[0])
        if value is None:
            continue
        ref_min = _to_float(nums[1]) if len(nums) > 2 else None
        ref_max = _to_float(nums[2]) if len(nums) > 2 else None
        name = cleaned.split(nums[0])[0].strip(" :-")
        if not name:
            continue
        rows.append(
            {
                "name": name,
                "value": value,
                "unit": "",
                "ref_min": ref_min,
                "ref_max": ref_max,
            }
        )
    return rows


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _is_image_file(path: str) -> bool:
    mime_type, _ = mimetypes.guess_type(path)
    return bool(mime_type and mime_type.startswith("image/"))


def _ocr_image_with_groq(file_path: str) -> tuple[list[dict], str]:
    api_key = getattr(settings, "GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return [], "OCR failed: GROQ_API_KEY not set."

    try:
        data_url = _file_to_data_url(file_path)
    except OSError:
        return [], "OCR failed: uploaded file could not be read."

    configured = getattr(settings, "GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")
    model_candidates = [m.strip() for m in configured.split(",") if m.strip()]
    model_candidates.extend(["llama-3.2-11b-vision-preview", "meta-llama/llama-4-scout-17b-16e-instruct"])
    tried = []

    prompt = (
        "Extract lab parameters from this medical report image and return strict JSON only.\n"
        'Format: {"parameters":[{"name":"Hemoglobin","value":11.2,"unit":"g/dL","ref_min":12,"ref_max":16}]}\n'
        "Rules: include only rows with numeric values, use null for missing ref_min/ref_max."
    )

    for model in dict.fromkeys(model_candidates):
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "temperature": 0,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": data_url}},
                            ],
                        }
                    ],
                },
                timeout=50,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            payload = _parse_json_response(content)
            if not payload:
                rows = _parse_lines_to_parameters(content)
                if rows:
                    return rows, f"OCR succeeded with {model} using text parse."
                tried.append(f"{model}: response not parseable")
                continue
            if isinstance(payload, dict):
                payload = payload.get("parameters", [])
            rows = _normalize_parameters(payload if isinstance(payload, list) else [])
            if rows:
                return rows, f"OCR succeeded with {model}."
            tried.append(f"{model}: no numeric parameters")
        except Exception as exc:
            tried.append(f"{model}: {exc}")

    return [], "OCR failed after trying models. " + " | ".join(tried[:4])


def _file_to_data_url(file_path: str) -> str:
    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "image/jpeg"
    with open(file_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def _normalize_parameters(items: list[dict]) -> list[dict]:
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        value = _to_float(item.get("value"))
        if not name or value is None:
            continue
        rows.append(
            {
                "name": name,
                "value": value,
                "unit": str(item.get("unit", "")).strip(),
                "ref_min": _to_float(item.get("ref_min")),
                "ref_max": _to_float(item.get("ref_max")),
            }
        )
    return rows


def _build_trend_hint(context: dict) -> str:
    reports = context.get("reports", [])
    if len(reports) < 2:
        return "Only one report is available, so trend direction is limited."

    previous = reports[-2].get("parameters", [])
    current = reports[-1].get("parameters", [])
    prev_map = {p.get("name"): p for p in previous}
    deltas = []
    for param in current:
        name = param.get("name")
        if name in prev_map:
            prev_value = _to_float(prev_map[name].get("value"))
            cur_value = _to_float(param.get("value"))
            if prev_value is None or cur_value is None:
                continue
            delta = cur_value - prev_value
            if delta > 0:
                deltas.append(f"{name} increased by {delta:.2f}")
            elif delta < 0:
                deltas.append(f"{name} decreased by {abs(delta):.2f}")
            else:
                deltas.append(f"{name} stayed stable")
    if not deltas:
        return "Not enough comparable parameters for trend analysis."
    return "Trend snapshot: " + "; ".join(deltas[:5]) + "."


def _ensure_analysis_shape(parsed: dict, context: dict) -> dict:
    fallback = fallback_analysis(context)
    return {
        "mentor_summary": parsed.get("mentor_summary") or fallback["mentor_summary"],
        "trend_analysis": parsed.get("trend_analysis") or fallback["trend_analysis"],
        "doctor_summary": parsed.get("doctor_summary") or fallback["doctor_summary"],
    }


def classify(value: float, ref_min: float | None, ref_max: float | None) -> str:
    if ref_min is None or ref_max is None:
        return "unknown"
    if value < ref_min:
        return "low"
    if value > ref_max:
        return "high"
    return "normal"
