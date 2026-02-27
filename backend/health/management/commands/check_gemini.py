import os

import google.generativeai as genai
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from health.gemini_utils import resolve_gemini_model_name


class Command(BaseCommand):
    help = "Checks if GEMINI_API_KEY is configured and Gemini API is reachable."

    def handle(self, *args, **options):
        api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise CommandError("GEMINI_API_KEY not set.")

        try:
            genai.configure(api_key=api_key)
            model_name = resolve_gemini_model_name()
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Reply with exactly: OK")
            text = (getattr(response, "text", "") or "").strip()
        except Exception as exc:
            raise CommandError(f"Gemini API check failed: {exc}") from exc

        if "OK" not in text.upper():
            self.stdout.write(self.style.WARNING(f"Unexpected response: {text}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Gemini API is working with {model_name}."))
