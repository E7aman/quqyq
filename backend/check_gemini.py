import os, sys
sys.path.insert(0, ".")
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
import django; django.setup()
from django.conf import settings
from core import llm
print("ключ задан:", bool(settings.GEMINI_API_KEY), "| модель:", settings.GEMINI_MODEL)
try:
    print("ответ:", llm.generate_json('Верни только JSON {"ok": true}', "ping"))
except Exception as e:
    print("ОШИБКА:", e)
