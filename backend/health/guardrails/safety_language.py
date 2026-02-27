import re


DIAGNOSIS_PATTERNS = [
    (re.compile(r"\byou have ([a-z\s-]+)\b", re.IGNORECASE), "This pattern may be associated with \\1"),
    (re.compile(r"\bthis confirms ([a-z\s-]+)\b", re.IGNORECASE), "This may suggest \\1"),
    (re.compile(r"\bdiagnosed with ([a-z\s-]+)\b", re.IGNORECASE), "shows findings related to \\1"),
]

ALARM_SOFTENERS = {
    "dangerous": "concerning",
    "severe": "significant",
    "critical": "important",
    "emergency": "prompt clinical review",
    "immediately": "soon",
}

PRESCRIPTION_PATTERNS = [
    re.compile(r"\b(start|take|use)\s+[a-z0-9\s-]+\s+mg\b", re.IGNORECASE),
    re.compile(r"\bprescribe\b", re.IGNORECASE),
]


def validate_language(text: str) -> tuple[str, dict]:
    value = (text or "").strip()
    if not value:
        return "", {"diagnosis_rewrites": 0, "alarm_softened": 0, "prescription_removed": 0}

    diagnosis_rewrites = 0
    for pattern, replacement in DIAGNOSIS_PATTERNS:
        value, count = pattern.subn(replacement, value)
        diagnosis_rewrites += count

    alarm_softened = 0
    for harsh, softer in ALARM_SOFTENERS.items():
        pattern = re.compile(rf"\b{re.escape(harsh)}\b", re.IGNORECASE)
        value, count = pattern.subn(softer, value)
        alarm_softened += count

    prescription_removed = 0
    for pattern in PRESCRIPTION_PATTERNS:
        value, count = pattern.subn("discuss treatment options with your clinician", value)
        prescription_removed += count

    if "educational support only" not in value.lower():
        value = value.rstrip() + " This is educational support only, not a diagnosis or prescription."

    return value, {
        "diagnosis_rewrites": diagnosis_rewrites,
        "alarm_softened": alarm_softened,
        "prescription_removed": prescription_removed,
    }
