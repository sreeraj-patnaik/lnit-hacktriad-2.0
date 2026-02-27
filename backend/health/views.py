import json

import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import MedicalReportUploadForm
from .models import MedicalReport
from .services import process_report


@login_required
def upload_report_view(request):
    form = MedicalReportUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        report = form.save(commit=False)
        report.user = request.user
        report.save()
        process_report(report.id)
        messages.success(request, "Report uploaded and analyzed.")
        return redirect("report-detail", report_id=report.id)
    return render(request, "health/upload_report.html", {"form": form})


@login_required
def report_detail_view(request, report_id: int):
    report = MedicalReport.objects.filter(user=request.user).prefetch_related("parameters").select_related("analysis").filter(id=report_id).first()
    if not report:
        raise Http404("Report not found.")

    timeline_reports = (
        MedicalReport.objects.filter(user=request.user)
        .prefetch_related("parameters")
        .order_by("report_date", "created_at")
    )
    series_map = {}
    for report_item in timeline_reports:
        date_label = str(report_item.report_date)
        for param in report_item.parameters.all():
            item = series_map.setdefault(
                param.name,
                {
                    "name": param.name,
                    "slug": slugify(param.name),
                    "unit": param.unit or "",
                    "points": [],
                },
            )
            item["points"].append(
                {
                    "date": date_label,
                    "value": float(param.value),
                    "risk": param.risk_flag,
                }
            )

    current_params = list(report.parameters.all())
    current_param_names = [p.name for p in current_params]
    trend_series = []
    for name in current_param_names:
        if name not in series_map:
            continue
        series = series_map[name]
        points = series.get("points", [])
        if not points:
            continue
        latest_value = points[-1]["value"]
        previous_value = points[-2]["value"] if len(points) > 1 else None
        delta = latest_value - previous_value if previous_value is not None else None
        if delta is None:
            direction = "neutral"
        elif delta > 0:
            direction = "up"
        elif delta < 0:
            direction = "down"
        else:
            direction = "flat"

        series["first_date"] = points[0]["date"]
        series["last_date"] = points[-1]["date"]
        series["latest_value"] = round(latest_value, 2)
        series["delta"] = round(delta, 2) if delta is not None else None
        series["direction"] = direction
        series["latest_risk"] = points[-1].get("risk", "unknown")
        series["point_count"] = len(points)
        trend_series.append(series)

    trend_series.sort(key=lambda x: (x["latest_risk"] != "high", x["latest_risk"] != "low", x["name"]))

    return render(
        request,
        "health/report_detail.html",
        {
            "report": report,
            "parameters": report.parameters.all(),
            "analysis": getattr(report, "analysis", None),
            "trend_series": trend_series[:10],
            "full_narrative": (
                getattr(report, "analysis", None).raw_response.get("comprehensive_narrative", "")
                if getattr(report, "analysis", None)
                else ""
            )
            or (getattr(report, "analysis", None).mentor_summary if getattr(report, "analysis", None) else ""),
            "tts_default_lang": (
                getattr(getattr(request.user, "userprofile", None), "language_preference", "") or "en-IN"
            ),
        },
    )


@login_required
@require_POST
@csrf_exempt
def translate_narrative_view(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    text = str(payload.get("text") or "").strip()
    target_lang = str(payload.get("target_lang") or "").strip()
    if not text:
        return JsonResponse({"error": "Text is required."}, status=400)
    if not target_lang:
        return JsonResponse({"error": "target_lang is required."}, status=400)

    normalized_target = _normalize_translate_lang(target_lang)
    normalized_source = _normalize_translate_lang(str(payload.get("source_lang") or "en"))

    if normalized_target == normalized_source:
        return JsonResponse({"translated_text": text, "target_lang": target_lang})

    try:
        response = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": normalized_source,
                "tl": normalized_target,
                "dt": "t",
                "q": text,
            },
            timeout=12,
        )
        response.raise_for_status()
        data = response.json()
        translated = "".join(chunk[0] for chunk in data[0] if chunk and chunk[0])
        if not translated.strip():
            raise ValueError("Empty translation response")
        return JsonResponse({"translated_text": translated, "target_lang": target_lang})
    except Exception:
        return JsonResponse(
            {
                "error": "Translation service is unavailable right now.",
                "translated_text": text,
                "target_lang": target_lang,
            },
            status=503,
        )


def _normalize_translate_lang(lang_code: str) -> str:
    value = (lang_code or "en").strip().lower()
    if not value:
        return "en"
    return value.split("-")[0]
