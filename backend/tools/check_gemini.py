"""Проверка связи с Gemini: python tools/check_gemini.py  (запускать из папки backend)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.conf import settings
from core import llm

print("ключ задан:", bool(settings.GEMINI_API_KEY), "| модель:", settings.GEMINI_MODEL, "| запасная:", settings.GEMINI_FALLBACK_MODEL)
try:
    print("ответ модели:", llm.generate_json('Верни только JSON {"ok": true}', "ping"))
    print("ВСЁ В ПОРЯДКЕ: Gemini отвечает")
except Exception as exc:
    print("ОШИБКА:", exc)
    print("Подсказки: 429/quota — исчерпан лимит, подождите или смените ключ; 404/not found — неверный код модели в .env;"
          " 403/API key — ключ неверный или не включён.")
