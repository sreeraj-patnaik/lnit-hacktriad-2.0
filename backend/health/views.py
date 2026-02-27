from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render

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

    return render(
        request,
        "health/report_detail.html",
        {
            "report": report,
            "parameters": report.parameters.all(),
            "analysis": getattr(report, "analysis", None),
        },
    )
