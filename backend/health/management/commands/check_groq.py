import os

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Checks if GROQ_API_KEY is configured and Groq API is reachable."

    def handle(self, *args, **options):
        api_key = getattr(settings, "GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise CommandError("GROQ_API_KEY not set.")

        model = getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant")
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "temperature": 0,
                    "messages": [
                        {"role": "user", "content": "Reply with exactly OK"},
                    ],
                },
                timeout=30,
            )
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            raise CommandError(f"Groq API check failed: {exc}") from exc

        if "OK" not in text.upper():
            self.stdout.write(self.style.WARNING(f"Unexpected response: {text}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Groq API is working with {model}."))
