# Aarogya Health Command - Implementation Documentation

## 1. Project Status Summary
This project is a context-aware medical report interpreter with:
- Multi-report upload and parsing
- Longitudinal trend analysis
- AI narrative generation with safety guardrails
- Doctor summary + extracted report notes
- Translation + multilingual text-to-speech (TTS)
- Enterprise-style frontend UI/UX redesign

All core integrations and workflows are preserved while frontend was fully revamped.

## 2. Updated Guardrails (What, Where, How)

### 2.1 Input Guardrails
**File:** `health/guardrails/input_guardrails.py`

Implemented checks:
- `image_quality`
  - Validates image readability by file size and optional image dimension checks.
  - Thresholds:
    - `MIN_IMAGE_BYTES = 20 KB`
    - `MIN_IMAGE_DIMENSION = 700`
- `data_completeness`
  - Requires minimum parameter rows and adequate presence of units + reference ranges.
  - Thresholds:
    - `MIN_PARAMETERS = 3`
    - `unit_ratio >= 0.3`
    - `reference_ratio >= 0.3`
- `ocr_confidence`
  - Estimates extraction confidence from numeric/name coverage.
  - Safe if confidence >= `0.65`.

Returned metadata includes:
- `safe`
- `reason`
- `confidence`
- per-check `meta`

### 2.2 Important Update: Soft Degrade Instead of Hard Block
**File:** `health/services.py`

Previous behavior blocked full interpretation when input was low quality.

Updated behavior:
- Analysis still runs even when input guardrails are not safe.
- `_apply_input_quality_notice(...)` prepends a limited-confidence warning.
- `guardrail_meta.input_quality_degraded = true` is added.

Result: usable output under incomplete input, but clearly marked as lower confidence.

### 2.3 Output Guardrails
**File:** `health/guardrails/output_guardrails.py`

Implemented checks:
- Language safety validation on:
  - `comprehensive_narrative`
  - `mentor_summary`
  - `trend_analysis`
  - `doctor_summary`
- Claim validation:
  - Extracts numeric claims from generated text.
  - Matches against allowed report numbers (`value`, `ref_min`, `ref_max`) with tolerance.
  - Flags hallucination when mismatch ratio is high.
- Confidence labeling:
  - Uses input confidence + claim mismatch penalty.
  - Final label: `HIGH`, `MEDIUM`, or `LOW`.

### 2.4 Safety Language Enforcement
**File:** `health/guardrails/safety_language.py`

Implemented rewrites:
- Diagnosis-like claims softened/reframed
- Alarmist words softened
- Prescription-like instructions replaced with clinician-discussion guidance
- Mandatory disclaimer appended:
  - "educational support only, not a diagnosis or prescription"

## 3. Security Features Implemented

### 3.1 Authentication + Session Controls
**Files:**
- `core/views.py`
- `health/views.py`
- `backend/settings.py`

Controls:
- `login_required` on sensitive routes (`upload`, `detail`, `translate`, `tts`, profile actions)
- Redirect flows:
  - `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`

### 3.2 Object-Level Access Protection
**File:** `health/views.py`

Protection:
- Report access is always filtered by current user.
- Unauthorized report IDs return `404` (`Http404`).

### 3.3 CSRF + Safe POST Patterns
**Files:**
- `templates/*.html`
- `health/views.py`
- `backend/settings.py`

Controls:
- Django `CsrfViewMiddleware` enabled.
- Form POSTs include `{% csrf_token %}`.
- JS `fetch` calls include `X-CSRFToken` header for translate/TTS.
- `@require_POST` enforced for translation and TTS endpoints.

### 3.4 Input Validation on API/Form Boundaries
**Files:**
- `health/forms.py`
- `health/views.py`

Validation:
- Upload requires at least one of: file or pasted text.
- Translate endpoint validates JSON payload and required fields.
- TTS endpoint validates JSON, non-empty text, and length cap (`<= 6000`).

### 3.5 Password and Core Django Security Middleware
**File:** `backend/settings.py`

Enabled:
- Password validators (similarity, min length, common password, numeric)
- Security middleware
- CSRF middleware
- Clickjacking protection (`XFrameOptionsMiddleware`)

### 3.6 Transaction Safety for Processing
**File:** `health/services.py`

Protection:
- `transaction.atomic()` wraps report parameter refresh + analysis save to prevent partial writes.

### 3.7 Controlled External Integrations + Fail-Safe Fallbacks
**Files:**
- `health/services.py`
- `health/views.py`

Controls:
- External calls have explicit timeouts.
- Exceptions handled to avoid crashes.
- If LLM unavailable, fallback narrative still generated.
- If OCR vision model fails, model fallback chain is attempted.

### 3.8 CORS Scope (Dev)
**File:** `backend/settings.py`

- CORS restricted to localhost dev origins (`5173`), not fully open.

## 4. Functional Features Implemented (Current)

### 4.1 User and Profile Context
**Files:**
- `core/forms.py`
- `core/models.py`
- `core/views.py`

- Signup captures rich health profile context.
- Profile update flow supports ongoing personalization.

### 4.2 Report Upload Modes
**Files:**
- `health/forms.py`
- `health/views.py`
- `health/services.py`

Supports:
- File upload (`image` / `.txt`)
- Text-only manual report entry

### 4.3 OCR + Structured Parsing
**File:** `health/services.py`

Pipeline:
- Manual text parser (strict + permissive modes)
- `.txt` file parser
- Image OCR via GROQ vision models with fallback model attempts

### 4.4 Risk Classification + Persistence
**Files:**
- `health/services.py`
- `health/models.py`

- Classifies each marker as `high`, `low`, `normal`, or `unknown` using reference ranges.
- Stores structured parameters per report.

### 4.5 Longitudinal Trend Analysis
**File:** `health/views.py`

- Builds marker-wise timeline series from historical reports.
- Computes delta, direction, latest risk, and top trend cards.

### 4.6 AI Interpretation + Doctor Summary
**File:** `health/services.py`

Outputs include:
- comprehensive narrative
- mentor summary
- trend analysis text
- doctor summary
- doctor suggestions considered

### 4.7 Translation + TTS
**File:** `health/views.py`

- Translate endpoint (Google Translate API)
- TTS endpoint (edge-tts voice mapping across languages)
- Robust fallback and error responses

### 4.8 Frontend Revamp (Enterprise UI)
**Files:**
- `templates/base.html`
- `templates/core/*.html`
- `templates/health/*.html`
- `static/app.css`

Delivered:
- New design system (typography, spacing, color tokens, responsive grids)
- New landing/dashboard/auth/profile/upload/detail page structure
- Mobile nav behavior
- Preserved all functional IDs/hooks for trend + TTS + translate

### 4.9 CSS Cache-Busting Fix
**File:** `templates/base.html`

- `app.css` served with version query string to prevent stale browser cache from showing old styles.

## 5. Test Coverage (Implemented)
**File:** `health/tests.py`

Validated cases include:
- Cross-user report access denial
- Upload -> analysis creation flow
- Text-only upload support
- Image upload fallback flow
- Trend section rendering
- Translation endpoint behavior
- TTS endpoint behavior + empty-text rejection
- Guardrail degraded-mode behavior for low completeness input
- Guardrail meta and confidence presence on safe input

## 6. Route Map (Current)

### Core Routes
**File:** `core/urls.py`
- `/` -> dashboard (or public landing for unauthenticated users)
- `/signup/`
- `/login/`
- `/logout/`
- `/profile/`

### Health Routes
**File:** `health/urls.py`
- `/health/upload/`
- `/health/translate/`
- `/health/tts/`
- `/health/<report_id>/`

## 7. Out-of-Scope / Safety Boundaries
System does **not** provide:
- final diagnosis
- medication prescriptions
- emergency decision support

It provides educational interpretation with explicit guardrails and clinician-review direction.

## 8. Quick Demo Script (Hackathon)
1. Signup and save profile context.
2. Upload text-only report, show extracted parameters and risk tags.
3. Upload second report to show trend cards.
4. Open report detail, show narrative + doctor summary.
5. Switch language and play TTS.
6. Show `guardrail_meta` in stored raw response for safety transparency.
7. Mention degraded-confidence behavior on incomplete input.

---
Last updated: 2026-02-28

## 9. OTP Email Setup (Demo + Real SMTP)

OTP login is implemented in:
- `core/views.py` (`login_view`, `_send_login_otp`, OTP session helpers)
- `core/forms.py` (`LoginOTPForm`)
- `templates/core/login.html` (2-step login UI)

Email config is now environment-driven in:
- `backend/settings.py`

### Recommended env vars
- `EMAIL_BACKEND`
- `DEFAULT_FROM_EMAIL`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS`
- `EMAIL_USE_SSL`
- `EMAIL_TIMEOUT`

### Behavior
- In `DEBUG=True`, default backend is console backend (safe demo fallback).
- In non-debug environments, use SMTP backend via env vars.

### Gmail demo setup example
- `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
- `EMAIL_HOST=smtp.gmail.com`
- `EMAIL_PORT=587`
- `EMAIL_USE_TLS=true`
- `EMAIL_HOST_USER=yourdemoid@gmail.com`
- `EMAIL_HOST_PASSWORD=<gmail_app_password>`
- `DEFAULT_FROM_EMAIL=Aarogya Demo <yourdemoid@gmail.com>`
