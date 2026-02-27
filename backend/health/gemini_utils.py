import google.generativeai as genai


PREFERRED_MODELS = [
    "models/gemini-2.0-flash",
    "models/gemini-2.0-flash-lite",
    "models/gemini-1.5-flash",
    "models/gemini-1.5-pro",
]


def resolve_gemini_model_name() -> str:
    try:
        models = list(genai.list_models())
    except Exception:
        return "models/gemini-2.0-flash"

    eligible = []
    for model in models:
        methods = getattr(model, "supported_generation_methods", []) or []
        if "generateContent" in methods:
            eligible.append(getattr(model, "name", ""))

    for preferred in PREFERRED_MODELS:
        if preferred in eligible:
            return preferred

    if eligible:
        return eligible[0]

    return "models/gemini-2.0-flash"
