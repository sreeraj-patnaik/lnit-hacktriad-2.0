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
    extracted_data, doctor_suggestions = run_ocr(report)

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
        report.doctor_suggestions = doctor_suggestions
        report.save(update_fields=["doctor_suggestions"])

        context = prepare_llm_context(report)
        result = generate_analysis(context)
        analysis, _ = AnalysisResult.objects.update_or_create(
            report=report,
            defaults={
                "user": report.user,
                "mentor_summary": result.get("comprehensive_narrative")
                or result.get("mentor_summary", ""),
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
    profile, _ = UserProfile.objects.get_or_create(user=user)
    reports = (
        MedicalReport.objects.filter(user=user)
        .order_by("report_date", "created_at")
        .prefetch_related("parameters")
    )

    reports_data = []
    for report_item in reports:
        raw_text = (report_item.ocr_text or "").strip()
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
                "report_text_excerpt": raw_text[:3000],
                "doctor_notes_or_comments": report_item.doctor_suggestions
                or _extract_report_notes(raw_text),
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
        "current_report_doctor_suggestions": report.doctor_suggestions
        or _extract_report_notes((report.ocr_text or "").strip()),
    }


def generate_analysis(context: dict) -> dict:
    api_key = getattr(settings, "GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return fallback_analysis(context)

    model = getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant")
    prompt = f"""
You are a safety-first family-doctor style health report explainer.

Audience and tone:
- Speak directly to the person in plain language, with empathy and clarity.
- Sound like a thoughtful family doctor, not a technical bot.
- Be detailed and context-aware using personal profile, symptoms, lifestyle, medications, and report history.

Data interpretation rules:
- Use only provided data.
- No diagnosis and no medication prescriptions.
- Include all relevant details from report text, including doctor notes/comments/suggestions if present.
- Explain what each key marker means in everyday language, why it may matter, and whether it changed over time.
- Call out stable, improving, worsening, and borderline trends.
- Mention where uncertainty exists (missing refs, unclear OCR, sparse history).
- Provide practical next-step guidance and questions to discuss with a clinician.

Return ONLY valid JSON with this schema:
{{
  "comprehensive_narrative": "single long, coherent, person-to-person interpretation that integrates current status, trends, lifestyle context, symptoms, doctor notes, and practical next steps in one flow",
  "mentor_summary": "short optional summary line",
  "trend_analysis": "detailed trend and timeline interpretation across reports",
  "doctor_summary": "structured and concise clinical handoff including key values, trends, symptoms, and note text highlights",
  "doctor_suggestions_considered": ["list of doctor notes/comments/suggestions considered while writing this output"]
}}

Important style constraints:
- Write one continuous narrative, not fragmented sections.
- Do not restate a full dump of all parameter values; the table already shows them.
- Focus on interpretation: what it means for this person, what patterns matter, what to monitor next.
- Use warm clinical language, like a trusted family doctor speaking directly to the patient.

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
    user_context = context.get("user_context", {}) or {}
    doctor_notes = latest_report.get("doctor_notes_or_comments", []) or []
    notes_line = (
        " I also noticed report comments/notes: "
        + "; ".join(doctor_notes[:3])
        + "."
        if doctor_notes
        else ""
    )
    if not latest_params:
        mentor_summary = (
            "No lab parameters could be extracted from the latest upload. "
            "Please upload a clearer photo or paste report text in structured lines."
            f"{notes_line}"
        )
    else:
        symptoms = user_context.get("current_symptoms") or "not provided"
        conditions = user_context.get("past_medical_conditions") or "not provided"
        medications = user_context.get("medications") or "not provided"
        lifestyle = user_context.get("lifestyle") or {}
        lifestyle_line = (
            f"Sleep: {lifestyle.get('sleep_hours') or 'NA'}h, "
            f"Activity: {lifestyle.get('activity_level') or 'NA'}, "
            f"Diet: {lifestyle.get('diet_type') or 'NA'}."
        )
        mentor_summary = (
            "I reviewed your latest report together with your profile and previous records. "
            f"In this report, {normal_count} markers are in the normal range. "
            f"Markers running higher than range: {', '.join(high) if high else 'none identified'}. "
            f"Markers below range: {', '.join(low) if low else 'none identified'}. "
            f"Your shared symptoms: {symptoms}. Past conditions: {conditions}. Current medicines: {medications}. "
            f"Lifestyle context: {lifestyle_line}{notes_line} "
            "Please treat this as educational guidance and confirm with your clinician."
        )

    return {
        "comprehensive_narrative": _build_comprehensive_fallback_narrative(context),
        "mentor_summary": mentor_summary,
        "trend_analysis": (
            f"{trend_hint} "
            "This trend view is generated from available records and may be limited by OCR quality or missing ranges. "
            "For richer narrative insight, set GROQ_API_KEY."
        ),
        "doctor_summary": (
            "Longitudinal review prepared with profile context. "
            f"Current high markers: {', '.join(high) if high else 'none'}. "
            f"Current low markers: {', '.join(low) if low else 'none'}. "
            f"Reported symptoms: {user_context.get('current_symptoms') or 'not provided'}. "
            f"Past conditions: {user_context.get('past_medical_conditions') or 'not provided'}. "
            + (
                f"Report note highlights: {'; '.join(doctor_notes[:3])}. "
                if doctor_notes
                else ""
            )
            + "Please correlate with clinical history and examination."
        ),
        "doctor_suggestions_considered": doctor_notes[:6],
    }


def run_ocr(report: MedicalReport) -> tuple[list[dict], list[str]]:
    # MVP parser:
    # 1) Use pasted/report text if provided
    # 2) Parse uploaded .txt file if available
    manual_text = (report.ocr_text or "").strip()
    if manual_text:
        parsed = _parse_lines_to_parameters(manual_text)
        suggestions = _extract_report_notes(manual_text)
        if parsed:
            return parsed, suggestions
        report.ocr_text = (
            "Provided text could not be parsed. "
            "Use one line per parameter like: Hemoglobin 11.2 g/dL 12-16"
        )
        report.save(update_fields=["ocr_text"])
        return [], suggestions

    if report.report_file and report.report_file.name.lower().endswith(".txt"):
        try:
            with open(report.report_file.path, "r", encoding="utf-8", errors="ignore") as file_obj:
                file_text = file_obj.read()
            if not report.ocr_text:
                report.ocr_text = file_text[:10000]
                report.save(update_fields=["ocr_text"])
            parsed = _parse_lines_to_parameters(file_text)
            suggestions = _extract_report_notes(file_text)
            if parsed:
                return parsed, suggestions
        except OSError:
            pass

    if report.report_file and _is_image_file(report.report_file.path):
        parsed, suggestions, debug_message = _ocr_image_with_groq(report.report_file.path)
        if parsed:
            if not report.ocr_text:
                report.ocr_text = "\n".join(
                    [f"{p['name']} {p['value']} {p.get('unit', '')}".strip() for p in parsed]
                )
                report.save(update_fields=["ocr_text"])
            return parsed, suggestions
        report.ocr_text = debug_message[:10000]
        report.save(update_fields=["ocr_text"])
        return [], suggestions

    report.ocr_text = "No parseable text found from upload. Try a clearer image or paste report text."
    report.save(update_fields=["ocr_text"])
    return [], []


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


def _ocr_image_with_groq(file_path: str) -> tuple[list[dict], list[str], str]:
    api_key = getattr(settings, "GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return [], [], "OCR failed: GROQ_API_KEY not set."

    try:
        data_url = _file_to_data_url(file_path)
    except OSError:
        return [], [], "OCR failed: uploaded file could not be read."

    configured = getattr(settings, "GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")
    model_candidates = [m.strip() for m in configured.split(",") if m.strip()]
    model_candidates.extend(["llama-3.2-11b-vision-preview", "meta-llama/llama-4-scout-17b-16e-instruct"])
    tried = []

    prompt = (
        "Extract lab parameters from this medical report image and return strict JSON only.\n"
        'Format: {"parameters":[{"name":"Hemoglobin","value":11.2,"unit":"g/dL","ref_min":12,"ref_max":16}],"doctor_suggestions":["free-text doctor comments/suggestions/notes"]}\n'
        "Rules: include only rows with numeric values in parameters, use null for missing ref_min/ref_max, and collect non-tabular doctor notes in doctor_suggestions."
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
                suggestions = _extract_report_notes(content)
                if rows:
                    return rows, suggestions, f"OCR succeeded with {model} using text parse."
                tried.append(f"{model}: response not parseable")
                continue
            suggestions = []
            if isinstance(payload, dict):
                suggestions = _normalize_suggestions(payload.get("doctor_suggestions", []))
                payload = payload.get("parameters", [])
            rows = _normalize_parameters(payload if isinstance(payload, list) else [])
            if rows:
                return rows, suggestions, f"OCR succeeded with {model}."
            tried.append(f"{model}: no numeric parameters")
        except Exception as exc:
            tried.append(f"{model}: {exc}")

    return [], [], "OCR failed after trying models. " + " | ".join(tried[:4])


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


def _normalize_suggestions(items) -> list[str]:
    if not isinstance(items, list):
        return []
    cleaned = []
    for item in items:
        text = str(item or "").strip()
        if text:
            cleaned.append(text)
    return cleaned[:6]


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


def _extract_report_notes(text: str) -> list[str]:
    if not text:
        return []

    note_keywords = (
        "advice",
        "suggestion",
        "recommend",
        "recommendation",
        "doctor",
        "consult",
        "follow up",
        "follow-up",
        "impression",
        "comment",
        "note",
        "remark",
    )
    notes = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            continue
        has_number = bool(re.search(r"\d", line))
        looks_parameter = has_number and bool(
            re.search(
                r"[-+]?\d*\.?\d+\s*([A-Za-z%\/0-9\^\.]+)?\s*([-to]+\s*[-+]?\d*\.?\d+)?$",
                line,
                re.IGNORECASE,
            )
        )
        if looks_parameter:
            continue
        low = line.lower()
        if any(keyword in low for keyword in note_keywords) or len(line.split()) >= 6:
            notes.append(line)
        if len(notes) >= 6:
            break
    return notes


def _ensure_analysis_shape(parsed: dict, context: dict) -> dict:
    fallback = fallback_analysis(context)
    comprehensive = _coerce_to_text(parsed.get("comprehensive_narrative"))
    mentor = _coerce_to_text(parsed.get("mentor_summary"))
    return {
        "comprehensive_narrative": comprehensive or fallback["comprehensive_narrative"],
        "mentor_summary": mentor or comprehensive or fallback["mentor_summary"],
        "trend_analysis": _coerce_to_text(parsed.get("trend_analysis")) or fallback["trend_analysis"],
        "doctor_summary": _coerce_to_text(parsed.get("doctor_summary")) or fallback["doctor_summary"],
        "doctor_suggestions_considered": (
            _normalize_suggestions(parsed.get("doctor_suggestions_considered", []))
            or fallback.get("doctor_suggestions_considered", [])
        ),
    }


def _coerce_to_text(value) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        lines = [str(item).strip() for item in value if str(item).strip()]
        return "\n".join(lines)
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            text = str(item).strip()
            if text:
                lines.append(f"{str(key).replace('_', ' ').title()}: {text}")
        return "\n".join(lines)
    if value is None:
        return ""
    return str(value).strip()


def _build_comprehensive_fallback_narrative(context: dict) -> str:
    reports = context.get("reports", []) or []
    latest_report = reports[-1] if reports else {"parameters": []}
    latest_params = latest_report.get("parameters", []) or []
    user_context = context.get("user_context", {}) or {}

    high = [p.get("name") for p in latest_params if p.get("risk_flag") == "high"]
    low = [p.get("name") for p in latest_params if p.get("risk_flag") == "low"]
    normal_count = len([p for p in latest_params if p.get("risk_flag") == "normal"])
    trend_hint = _build_trend_hint(context)
    doctor_notes = latest_report.get("doctor_notes_or_comments", []) or []

    symptoms = user_context.get("current_symptoms") or "no symptoms shared currently"
    conditions = user_context.get("past_medical_conditions") or "no major past conditions shared"
    medications = user_context.get("medications") or "no current medicines listed"
    lifestyle = user_context.get("lifestyle") or {}
    sleep = lifestyle.get("sleep_hours") or "NA"
    activity = lifestyle.get("activity_level") or "NA"
    diet = lifestyle.get("diet_type") or "NA"

    if not latest_params:
        return (
            "I could not reliably read lab values from this upload, so I cannot give a trustworthy interpretation yet. "
            "Please upload a clearer scan or paste the report text line by line, and I will re-build your trend story. "
            f"From your profile, I still consider your context important: symptoms are {symptoms}, past history is {conditions}, "
            f"and medications are {medications}. Lifestyle currently reflects sleep around {sleep} hours, activity level {activity}, and diet type {diet}. "
            "Once the values are readable, I will connect these factors with your marker patterns and give you a complete interpretation."
        )

    stability_note = (
        "Most markers appear stable or within expected range in this cycle."
        if not high and not low
        else (
            f"The main points needing attention are higher markers: {', '.join(high) if high else 'none'}, "
            f"and lower markers: {', '.join(low) if low else 'none'}."
        )
    )
    doctor_note_line = (
        f" I also factored in your report notes: {'; '.join(doctor_notes[:3])}."
        if doctor_notes
        else ""
    )

    return (
        "I reviewed this report in the context of your previous records and your personal health background, so this is not just a one-time reading. "
        f"You currently have {normal_count} markers in normal range, and {stability_note} "
        f"When I map this to your day-to-day context, your current symptoms are {symptoms}, your background history is {conditions}, "
        f"and your medicine list shows {medications}. Your routine currently reflects sleep around {sleep} hours, activity level {activity}, and a {diet} diet, "
        "which can meaningfully influence energy, recovery, and longer-term marker movement over time. "
        f"Across timeline comparison, {trend_hint} "
        "The practical takeaway is to continue monitoring consistency rather than reacting to one isolated number: keep sleep and activity regular, repeat follow-up testing on schedule, "
        "and watch for any new symptoms that match trend shifts rather than isolated fluctuations."
        f"{doctor_note_line} "
        "Use this as a structured discussion aid with your clinician so decisions are based on your full history, not a single report snapshot."
    )


def classify(value: float, ref_min: float | None, ref_max: float | None) -> str:
    if ref_min is None or ref_max is None:
        return "unknown"
    if value < ref_min:
        return "low"
    if value > ref_max:
        return "high"
    return "normal"
