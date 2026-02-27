# MVP Runbook (Groq Mode)

## 1) Set API key
```powershell
$env:GROQ_API_KEY="your_groq_api_key"
$env:GROQ_MODEL="llama-3.1-8b-instant"
```

## 2) Verify API
```powershell
.\venv\Scripts\python.exe manage.py check_groq
```

## 3) Prepare DB and run
```powershell
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver
```

## 4) Demo flow
1. Sign up and fill profile.
2. Open `Upload Report`.
3. Upload a report photo/file OR paste report text.
4. Use report detail page to review extracted parameters + LLM output.
5. Add another report and re-run to see trend-aware output.

## Accepted text format (for paste mode)
Use one line per parameter:
```text
Hemoglobin 11.2 g/dL 12-16
WBC 7000 cells/uL 4000-11000
Platelets 220000 /uL 150000-450000
```

## Notes
- User data is isolated: users can access only their own reports.
- If Groq key is missing/invalid, app falls back to deterministic educational summary.
- Photo OCR (jpg/png/webp) is enabled through Groq vision model.
- If vision OCR fails for any reason, paste mode remains the reliable backup path.


