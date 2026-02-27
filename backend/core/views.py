import secrets
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Prefetch
from django.core.mail import send_mail
from django.shortcuts import redirect, render

from core.forms import LoginForm, LoginOTPForm, SignupForm, UserProfileForm
from core.models import UserProfile
from health.models import MedicalReport

LOGIN_OTP_SESSION_KEY = "login_otp_context"
LOGIN_OTP_TTL_SECONDS = 5 * 60
LOGIN_OTP_MAX_ATTEMPTS = 5


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

    otp_context = _get_login_otp_context(request)

    if request.method == "POST":
        step = (request.POST.get("step") or "credentials").strip().lower()

        if step == "credentials":
            form = LoginForm(request, data=request.POST or None)
            if form.is_valid():
                user = form.get_user()
                otp_code = _generate_otp_code()
                _store_login_otp_context(request, user.id, otp_code)
                sent, error = _send_login_otp(request, user, otp_code)
                if not sent:
                    _clear_login_otp_context(request)
                    form.add_error(None, error or "Unable to send OTP right now. Please try again.")
                    return render(
                        request,
                        "core/login.html",
                        {
                            "form": form,
                            "otp_form": LoginOTPForm(),
                            "otp_stage": False,
                        },
                    )
                otp_email = _mask_email(user.email)
                messages.success(request, f"OTP sent to {otp_email}.")
                return render(
                    request,
                    "core/login.html",
                    {
                        "form": LoginForm(request),
                        "otp_form": LoginOTPForm(),
                        "otp_stage": True,
                        "otp_email": otp_email,
                    },
                )
            return render(
                request,
                "core/login.html",
                {
                    "form": form,
                    "otp_form": LoginOTPForm(),
                    "otp_stage": False,
                },
            )

        if step == "otp":
            otp_context = _get_login_otp_context(request)
            if not otp_context:
                messages.error(request, "OTP expired. Please login again.")
                return render(
                    request,
                    "core/login.html",
                    {
                        "form": LoginForm(request),
                        "otp_form": LoginOTPForm(),
                        "otp_stage": False,
                    },
                )

            otp_form = LoginOTPForm(request.POST or None)
            if otp_form.is_valid():
                attempts = int(otp_context.get("attempts", 0))
                if attempts >= LOGIN_OTP_MAX_ATTEMPTS:
                    _clear_login_otp_context(request)
                    messages.error(request, "Too many invalid OTP attempts. Please login again.")
                    return render(
                        request,
                        "core/login.html",
                        {
                            "form": LoginForm(request),
                            "otp_form": LoginOTPForm(),
                            "otp_stage": False,
                        },
                    )

                entered = str(otp_form.cleaned_data["otp"]).strip()
                expected = str(otp_context.get("otp_code", ""))
                if secrets.compare_digest(entered, expected):
                    user = User.objects.filter(id=otp_context.get("user_id")).first()
                    _clear_login_otp_context(request)
                    if not user:
                        messages.error(request, "Session invalid. Please login again.")
                        return render(
                            request,
                            "core/login.html",
                            {
                                "form": LoginForm(request),
                                "otp_form": LoginOTPForm(),
                                "otp_stage": False,
                            },
                        )
                    login(request, user)
                    messages.success(request, "Login successful.")
                    return redirect("dashboard")

                attempts += 1
                remaining = LOGIN_OTP_MAX_ATTEMPTS - attempts
                if remaining <= 0:
                    _clear_login_otp_context(request)
                    messages.error(request, "Too many invalid OTP attempts. Please login again.")
                    return render(
                        request,
                        "core/login.html",
                        {
                            "form": LoginForm(request),
                            "otp_form": LoginOTPForm(),
                            "otp_stage": False,
                        },
                    )

                otp_context["attempts"] = attempts
                request.session[LOGIN_OTP_SESSION_KEY] = otp_context
                otp_form.add_error("otp", f"Invalid OTP. {remaining} attempt(s) left.")

            user = User.objects.filter(id=otp_context.get("user_id")).first()
            otp_email = _mask_email(user.email) if user else "your registered email"
            return render(
                request,
                "core/login.html",
                {
                    "form": LoginForm(request),
                    "otp_form": otp_form,
                    "otp_stage": True,
                    "otp_email": otp_email,
                },
            )

        if step == "resend":
            otp_context = _get_login_otp_context(request)
            if not otp_context:
                messages.error(request, "OTP session expired. Please login again.")
                return render(
                    request,
                    "core/login.html",
                    {
                        "form": LoginForm(request),
                        "otp_form": LoginOTPForm(),
                        "otp_stage": False,
                    },
                )
            user = User.objects.filter(id=otp_context.get("user_id")).first()
            if not user:
                _clear_login_otp_context(request)
                messages.error(request, "Session invalid. Please login again.")
                return render(
                    request,
                    "core/login.html",
                    {
                        "form": LoginForm(request),
                        "otp_form": LoginOTPForm(),
                        "otp_stage": False,
                    },
                )
            otp_code = _generate_otp_code()
            _store_login_otp_context(request, user.id, otp_code)
            sent, error = _send_login_otp(request, user, otp_code)
            if not sent:
                _clear_login_otp_context(request)
                messages.error(request, error or "Unable to resend OTP right now. Please login again.")
                return render(
                    request,
                    "core/login.html",
                    {
                        "form": LoginForm(request),
                        "otp_form": LoginOTPForm(),
                        "otp_stage": False,
                    },
                )
            otp_email = _mask_email(user.email)
            messages.success(request, f"New OTP sent to {otp_email}.")
            return render(
                request,
                "core/login.html",
                {
                    "form": LoginForm(request),
                    "otp_form": LoginOTPForm(),
                    "otp_stage": True,
                    "otp_email": otp_email,
                },
            )

        if step == "reset":
            _clear_login_otp_context(request)
            return redirect("login")

    if otp_context:
        user = User.objects.filter(id=otp_context.get("user_id")).first()
        otp_email = _mask_email(user.email) if user else "your registered email"
        return render(
            request,
            "core/login.html",
            {
                "form": LoginForm(request),
                "otp_form": LoginOTPForm(),
                "otp_stage": True,
                "otp_email": otp_email,
            },
        )

    return render(
        request,
        "core/login.html",
        {
            "form": LoginForm(request),
            "otp_form": LoginOTPForm(),
            "otp_stage": False,
        },
    )


def dashboard_view(request):
    if not request.user.is_authenticated:
        return render(request, "core/landing.html")

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


def _generate_otp_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def _store_login_otp_context(request, user_id: int, otp_code: str) -> None:
    request.session[LOGIN_OTP_SESSION_KEY] = {
        "user_id": user_id,
        "otp_code": otp_code,
        "attempts": 0,
        "expires_at": int(time.time()) + LOGIN_OTP_TTL_SECONDS,
    }


def _clear_login_otp_context(request) -> None:
    request.session.pop(LOGIN_OTP_SESSION_KEY, None)


def _get_login_otp_context(request) -> dict | None:
    context = request.session.get(LOGIN_OTP_SESSION_KEY)
    if not isinstance(context, dict):
        return None
    expires_at = int(context.get("expires_at", 0))
    if expires_at <= int(time.time()):
        _clear_login_otp_context(request)
        return None
    return context


def _mask_email(email: str) -> str:
    value = (email or "").strip()
    if "@" not in value:
        return "your registered email"
    name, domain = value.split("@", 1)
    if len(name) <= 2:
        masked_name = f"{name[:1]}*"
    else:
        masked_name = f"{name[:1]}{'*' * (len(name) - 2)}{name[-1:]}"
    return f"{masked_name}@{domain}"


def _send_login_otp(request, user: User, otp_code: str) -> tuple[bool, str]:
    recipient = (user.email or "").strip()
    if not recipient and "@" in (user.username or ""):
        recipient = user.username.strip()
    if not recipient:
        return (
            False,
            "No email is configured for this account. OTP login requires a registered email. "
            "Update your user email in admin/profile and retry.",
        )

    subject = "Your Aarogya Login OTP"
    message = (
        f"Hi {user.username},\n\n"
        f"Your OTP for login is: {otp_code}\n"
        "This code will expire in 5 minutes.\n\n"
        "If you did not request this login, please ignore this email."
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@aarogya.local")

    try:
        send_mail(subject, message, from_email, [recipient], fail_silently=False)
        if settings.DEBUG:
            messages.info(
                request,
                f"DEBUG OTP (for demo only): {otp_code}",
            )
        return True, ""
    except Exception as exc:
        if settings.DEBUG:
            messages.warning(
                request,
                "Email backend unavailable in DEBUG mode. "
                f"Reason: {exc}. OTP for demo login is: {otp_code}",
            )
            return True, ""
        return False, "Unable to send OTP email at the moment. Please try again."
