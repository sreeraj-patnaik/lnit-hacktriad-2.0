from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import redirect, render

from core.forms import LoginForm, SignupForm, UserProfileForm
from core.models import UserProfile
from health.models import MedicalReport


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Account created successfully.")
        return redirect("profile")
    return render(request, "core/signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("dashboard")
    return render(request, "core/login.html", {"form": form})


@login_required
def dashboard_view(request):
    reports = (
        MedicalReport.objects.filter(user=request.user)
        .select_related("analysis")
        .prefetch_related(Prefetch("parameters"))
    )
    report_rows = []
    total_high = 0
    total_low = 0
    for report in reports:
        parameters = list(report.parameters.all())
        high_count = len([p for p in parameters if p.risk_flag == "high"])
        low_count = len([p for p in parameters if p.risk_flag == "low"])
        normal_count = len([p for p in parameters if p.risk_flag == "normal"])
        total_high += high_count
        total_low += low_count
        report_rows.append(
            {
                "report": report,
                "high_count": high_count,
                "low_count": low_count,
                "normal_count": normal_count,
                "parameter_count": len(parameters),
            }
        )

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(
        request,
        "core/dashboard.html",
        {
            "reports": reports,
            "report_rows": report_rows,
            "profile": profile,
            "stats": {
                "total_reports": len(report_rows),
                "completed_reports": len([row for row in report_rows if row["report"].analysis_completed]),
                "flagged_high": total_high,
                "flagged_low": total_low,
            },
        },
    )


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    form = UserProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("dashboard")
    return render(request, "core/profile.html", {"form": form})


@login_required
def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("login")
    return redirect("dashboard")
