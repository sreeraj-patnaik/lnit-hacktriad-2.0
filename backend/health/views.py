from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.text import slugify

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
        },
    )
