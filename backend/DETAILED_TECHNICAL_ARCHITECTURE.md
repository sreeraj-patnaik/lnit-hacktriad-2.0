# Aarogya Health Command - Detailed Technical Architecture

## 0.0 Document Purpose
This document is the in-depth technical reference for the current implementation of Aarogya Health Command. It explains structure, architecture, stack, methods, guardrails, security, workflows, and operational behavior in implementation-level detail.

## 0.1 Scope
This document reflects the code currently present in:
- `backend/`
- `core` Django app
- `health` Django app
- static/templates frontend

## 0.2 System Mission
The system provides safe, context-aware interpretation of medical report data across time, with longitudinal trends, clinician-friendly summaries, and multilingual accessibility.

## 1.0 High-Level System Architecture

## 1.1 Runtime Topology
1. Browser UI (Django templates + CSS + JavaScript)
2. Django server (`manage.py runserver` in dev)
3. SQLite database (`backend/db.sqlite3`)
4. Optional external services:
- Groq API for text/vision LLM
- Google Translate endpoint for translation
- SMTP server for OTP email
- edge-tts runtime for audio generation

## 1.2 Application Modules
1. `core` app: authentication, profile, landing/dashboard views
2. `health` app: report upload, OCR parsing, AI analysis, trend rendering, translation, TTS, guardrails

## 2.0 Repository and Code Structure

## 2.1 Root-Level
1. `README.md` - project overview
2. `FEATURES.txt` - feature notes
3. `requirements.txt` - base dependency list
4. `backend/` - Django project root

## 2.2 Django Project Layer (`backend/backend/`)
1. `settings.py` - app config, installed apps, security middleware, API keys, email settings
2. `urls.py` - global URL routing (`core` + `health`)
3. `wsgi.py` / `asgi.py` - runtime entry points

## 2.3 Core Domain Layer (`backend/core/`)
1. `models.py` - `UserProfile`, `LLMContextSnapshot`
2. `forms.py` - signup, login, OTP form, profile form
3. `views.py` - signup/login/logout/dashboard/profile
4. `signals.py` - auto-create profile on user creation
5. `urls.py` - core routes
6. `tests.py` - core auth behavior tests

## 2.4 Health Domain Layer (`backend/health/`)
1. `models.py` - `MedicalReport`, `LabParameter`, `AnalysisResult`
2. `forms.py` - report upload validation
3. `views.py` - upload/detail/translate/tts endpoints
4. `services.py` - OCR, parser, AI generation, orchestration
5. `guardrails/` - input/output/language safety controls
6. `management/commands/` - connectivity checks (`check_groq`, `check_gemini`)
7. `tests.py` - health flow and safety tests

## 2.5 Frontend Layer
1. `templates/base.html` - global shell, nav, responsive menu
2. `templates/core/*.html` - landing, dashboard, auth, profile
3. `templates/health/*.html` - upload and report detail pages
4. `static/app.css` - enterprise design system

## 3.0 Technology Stack and Libraries

## 3.1 Core Backend Stack
1. Python 3.12 runtime (project venv)
2. Django 6.0.2
3. Django REST Framework 3.16.1 (installed; current UI is template-driven)
4. django-cors-headers 4.9.0

## 3.2 Integration Libraries
1. `requests` for HTTP calls
2. `edge-tts` for server-side TTS audio
3. `google-generativeai` + dependencies (Gemini utility/health checks)
4. Groq OpenAI-compatible API endpoints for text and vision inference

## 3.3 Data Layer
1. SQLite database in development
2. Django ORM model layer
3. JSON fields for metadata-rich outputs

## 3.4 Frontend Stack
1. Django template rendering
2. Vanilla JavaScript for charts + TTS controls + translation interactions
3. Custom CSS (token-based enterprise UI)

## 4.0 Configuration and Environment Variables

## 4.1 Core Environment Variables
1. `GROQ_API_KEY`
2. `GROQ_MODEL`
3. `GROQ_VISION_MODEL`
4. `GEMINI_API_KEY`

## 4.2 Email/OTP Environment Variables
1. `EMAIL_BACKEND`
2. `DEFAULT_FROM_EMAIL`
3. `SERVER_EMAIL`
4. `EMAIL_HOST`
5. `EMAIL_PORT`
6. `EMAIL_HOST_USER`
7. `EMAIL_HOST_PASSWORD`
8. `EMAIL_USE_TLS`
9. `EMAIL_USE_SSL`
10. `EMAIL_TIMEOUT`

## 4.3 Important Behavior
1. In `DEBUG=True`, default email backend is console backend unless overridden.
2. Email host password is normalized by removing spaces for Gmail app-password copy safety.

## 5.0 Data Model and Schema Design

## 5.1 `core.models.UserProfile`
Purpose: profile context used for personalized interpretation.
Key fields: age, gender, city, location_type, sleep/activity/diet, symptoms, medications, health_goal, language_preference, smoking/alcohol.

## 5.2 `health.models.MedicalReport`
Purpose: primary report container.
Key fields: `user`, `report_file`, `report_date`, `analysis_completed`, `ocr_text`, `doctor_suggestions`, `created_at`.

## 5.3 `health.models.LabParameter`
Purpose: normalized structured lab rows.
Key fields: `name`, `value`, `unit`, `ref_min`, `ref_max`, `risk_flag`.

## 5.4 `health.models.AnalysisResult`
Purpose: stores generated interpretation outputs.
Key fields: `mentor_summary`, `trend_analysis`, `doctor_summary`, `raw_response` (JSON), timestamps.

## 5.5 Relationships
1. `User` 1:N `MedicalReport`
2. `MedicalReport` 1:N `LabParameter`
3. `MedicalReport` 1:1 `AnalysisResult`
4. `User` 1:1 `UserProfile`

## 6.0 End-to-End Request Workflows

## 6.1 Signup Workflow
1. `SignupForm` validates user and profile fields.
2. User saved via Django auth model.
3. Profile auto-created by signal and populated by form save.
4. User is logged in and redirected to profile/dashboard flow.

## 6.2 Login + OTP Workflow
Location: `core/views.py`
1. Credential step validates username/password.
2. System generates 6-digit OTP.
3. OTP context saved in session with TTL and attempts.
4. OTP emailed via `_send_login_otp`.
5. User submits OTP step.
6. Code is compared using constant-time `secrets.compare_digest`.
7. On success, user session is authenticated.
8. Supports resend/reset.

OTP control constants:
1. `LOGIN_OTP_TTL_SECONDS = 300`
2. `LOGIN_OTP_MAX_ATTEMPTS = 5`

## 6.3 Report Upload Workflow
Location: `health/views.py` + `health/services.py`
1. Authenticated user submits upload form.
2. Form accepts either file or pasted text; rejects empty both.
3. `process_report(report_id)` orchestrates extraction and analysis.
4. Existing parameters are refreshed inside DB transaction.
5. Analysis result and guardrail metadata are persisted.

## 6.4 Report Processing Pipeline (`process_report`)
1. OCR stage: `run_ocr(report)`
2. Input guardrails: `run_input_guardrails(...)`
3. Parameter persistence and risk classification
4. Context assembly from profile + report history
5. AI generation (`generate_analysis` or fallback)
6. Output guardrails apply language/claim safety
7. If input quality low, degradation notice is prepended
8. Guardrail metadata appended to final raw response

## 6.5 Report Detail Workflow
Location: `health/views.py`
1. User-isolated report lookup (filter by request user)
2. Historical parameter series built from all user reports
3. Per-parameter trend metrics generated (delta/direction/point counts)
4. Top trend series passed to template
5. Frontend sparkline JS renders trend charts

## 6.6 Translation Workflow
Location: `translate_narrative_view`
1. Validates JSON payload and required fields.
2. Normalizes language codes.
3. Calls Google Translate endpoint via `requests.get`.
4. Returns translated text or controlled service-unavailable response.

## 6.7 TTS Workflow
Location: `tts_narrative_view`
1. Validates payload and max text length (<= 6000).
2. Resolves voice from `VOICE_MAP`.
3. Calls `edge_tts` async synthesis.
4. Returns `audio/mpeg` response.

## 7.0 OCR and Parsing Strategy

## 7.1 Input Modalities
1. Manual pasted text
2. Uploaded `.txt` files
3. Uploaded image files

## 7.2 Parser Logic
Location: `_parse_lines_to_parameters`
1. Primary strict regex parser for line structure with optional ranges.
2. Secondary permissive parser for noisy OCR outputs.
3. Numeric coercion via `_to_float`.

## 7.3 Vision OCR Logic
Location: `_ocr_image_with_groq`
1. Converts image to base64 data URL.
2. Sends image + extraction prompt to Groq vision model.
3. Tries model candidates in fallback order.
4. Parses JSON response or falls back to text parsing.

## 8.0 AI Generation and Narrative Assembly

## 8.1 LLM Prompt Strategy
Location: `generate_analysis`
1. Safety-first doctor-like tone instruction.
2. Constraints: no diagnosis, no prescriptions, data-grounded interpretations.
3. Required JSON schema enforced in prompt.
4. Includes profile context and historical report timeline.

## 8.2 Response Parsing and Shape Normalization
1. `_parse_json_response` handles JSON and fenced/partial objects.
2. `_ensure_analysis_shape` normalizes missing fields.
3. `_coerce_to_text` converts list/dict responses to readable text.

## 8.3 Deterministic Fallback Path
1. Triggered when key missing, API errors, parse errors.
2. Generates narrative, trends, and doctor summary from local structured data only.

## 9.0 Guardrails: Full Technical Breakdown

## 9.1 Input Guardrails (`input_guardrails.py`)
Checks:
1. `image_quality`
2. `data_completeness`
3. `ocr_confidence`

Thresholds:
1. `MIN_PARAMETERS = 3`
2. `MIN_IMAGE_BYTES = 20 * 1024`
3. `MIN_IMAGE_DIMENSION = 700`
4. OCR safe threshold: confidence >= 0.65

Output structure:
1. `safe`
2. `reason`
3. `confidence`
4. per-check details in `checks[]`

## 9.2 Output Guardrails (`output_guardrails.py`)
Mechanisms:
1. Language sanitization per narrative field
2. Numeric claim extraction and validation
3. Hallucination mismatch ratio scoring
4. Confidence label computation (`HIGH/MEDIUM/LOW`)

## 9.3 Safety Language Guardrails (`safety_language.py`)
1. Rewrites diagnosis-style statements
2. Softens alarmist words
3. Replaces prescription-style instructions
4. Appends mandatory educational disclaimer

## 9.4 Soft-Degraded Mode (Critical Update)
Location: `_apply_input_quality_notice` in `services.py`
1. Low-quality input no longer hard-blocks interpretation.
2. Output is returned with explicit confidence warning.
3. Metadata flag: `guardrail_meta.input_quality_degraded = true`.

## 10.0 Security Controls and Defensive Measures

## 10.1 Authentication and Access Control
1. Sensitive health routes protected with `@login_required`.
2. Report detail access is user-scoped and unauthorized access returns 404.

## 10.2 CSRF and HTTP Method Protection
1. CSRF middleware enabled.
2. Template forms use CSRF tokens.
3. JSON endpoints include CSRF header in frontend JS.
4. Translate/TTS use `@require_POST`.

## 10.3 Input Validation
1. Upload form enforces at least one input source.
2. Translation/TTS validate payload shape and required parameters.
3. TTS enforces text length limit.

## 10.4 Session-Based OTP Security
1. OTP stored server-side in session context.
2. Expiry enforced via timestamp.
3. Max-attempt lockout behavior.
4. Constant-time OTP comparison.

## 10.5 Transactional Data Integrity
1. Report processing runs in `transaction.atomic`.
2. Prevents partial writes during extraction/analysis.

## 10.6 Django Security Baseline
1. `SecurityMiddleware`
2. `CsrfViewMiddleware`
3. `XFrameOptionsMiddleware`
4. Password validators configured

## 10.7 CORS Policy
1. CORS restricted to local development origins.

## 11.0 Frontend Architecture and UI System

## 11.1 Template Composition
1. `base.html` defines global shell, nav, footer, and menu logic.
2. Core pages and health pages extend base.

## 11.2 Styling System
1. Tokenized colors, spacing, typography in `static/app.css`.
2. Responsive layouts using CSS grid and media queries.
3. Dedicated visual components: panels, KPI cards, trend cards, forms, tags.

## 11.3 Interactive Frontend Features
1. Trend sparkline rendering from embedded JSON payload.
2. Translation requests via async fetch.
3. TTS playback controls with server and browser fallback behavior.
4. Mobile nav toggle script.

## 12.0 Operational Commands and Tooling

## 12.1 Core Run Commands
1. `python manage.py migrate`
2. `python manage.py runserver`
3. `python manage.py check`

## 12.2 Integration Check Commands
1. `python manage.py check_groq`
2. `python manage.py check_gemini`

## 12.3 SMTP Validation Command
1. `python manage.py shell -c "from django.core.mail import send_mail; ..."`

## 13.0 Test Coverage and Validation Status

## 13.1 Health Tests (`health/tests.py`)
Covers:
1. User data isolation
2. Upload and analysis creation
3. Text-only mode
4. Image fallback mode
5. Trend section rendering
6. Translation endpoint behavior
7. TTS endpoint behavior
8. Guardrail degraded-mode behavior
9. Guardrail metadata confidence presence

## 13.2 Core Tests (`core/tests.py`)
Covers:
1. Signup profile creation
2. Dashboard access behavior expectations
3. Logout behavior

Note: dashboard behavior was changed to public landing for unauthenticated users. Existing tests expecting redirect may need update if strict pass is required.

## 14.0 Known Limitations and Tradeoffs
1. Development database is SQLite; production should use PostgreSQL.
2. OCR and narrative quality depend on input quality and LLM availability.
3. Translation uses a web endpoint; availability depends on external network/service state.
4. OTP email requires valid recipient email per user record.
5. In DEBUG mode, OTP may be surfaced via UI message for demo continuity.

## 15.0 Deployment and Production Hardening Checklist
1. Set `DEBUG=False`.
2. Configure strong `ALLOWED_HOSTS`.
3. Use production DB and backups.
4. Configure SMTP secrets in environment only.
5. Ensure HTTPS termination and secure cookies.
6. Rotate API/email credentials and app passwords.
7. Add logging/monitoring around integration calls.
8. Run test suite and fix any behavior-test mismatches.

## 16.0 Feature Inventory (Current)
1. User signup/login/logout/profile management
2. OTP-based login verification
3. Medical report upload with file or text input
4. OCR and text parsing into structured parameters
5. Risk classification per marker
6. Longitudinal trend series and sparkline rendering
7. AI comprehensive narrative + trend interpretation + doctor summary
8. Guardrail pipeline (input + output + language safety)
9. Soft-degraded interpretation for incomplete input
10. Translation endpoint
11. Multilingual TTS endpoint
12. Enterprise UI redesign across all major pages
13. Hackathon documentation and runbook support

## 17.0 Primary Files Index
1. `backend/backend/settings.py`
2. `backend/backend/urls.py`
3. `backend/core/views.py`
4. `backend/core/forms.py`
5. `backend/core/models.py`
6. `backend/core/signals.py`
7. `backend/health/services.py`
8. `backend/health/views.py`
9. `backend/health/forms.py`
10. `backend/health/models.py`
11. `backend/health/guardrails/input_guardrails.py`
12. `backend/health/guardrails/output_guardrails.py`
13. `backend/health/guardrails/safety_language.py`
14. `backend/templates/base.html`
15. `backend/templates/core/*.html`
16. `backend/templates/health/*.html`
17. `backend/static/app.css`
18. `backend/HACKATHON_IMPLEMENTATION_DOCUMENTATION.md`
19. `backend/MVP_RUNBOOK.md`

---
Document version: 1.0
Prepared for: Hackathon technical review and handoff
