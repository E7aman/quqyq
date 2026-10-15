"""Защита входа: очистка текста, антиинъекции, лимиты запросов."""
import re
import time
from django.conf import settings
from django.core.cache import cache

MAX_TEXT = 2000

DISCLAIMER = {
    "ru": "Справочная информация, не юридическое заключение. Проверьте нормы по официальным источникам.",
    "kk": "Бұл анықтамалық ақпарат, заңды қорытынды емес. Нормаларды ресми дереккөздерден тексеріңіз.",
}

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_INJECTION = re.compile(
    r"(ignore (all |any )?(previous|prior|above) (instructions|rules)|"
    r"disregard (the )?(system|previous)|reveal (your )?(system )?prompt|"
    r"system prompt|developer mode|jailbreak|you are now|act as (?!a (student|plaintiff))|"
    r"игнорируй (все |любые )?(предыдущие |прежние )?(инструкции|правила)|"
    r"забудь (все |свои )?(инструкции|правила)|покажи (свой )?(системный )?промпт|"
    r"системн\w+ промпт|ты теперь|веди себя как|"
    r"алдыңғы нұсқаулықтарды ұмыт|нұсқаулықтарды елеме)",
    re.IGNORECASE,
)


def clean_text(text, limit=MAX_TEXT):
    text = _CTRL.sub("", str(text or "")).strip()
    return text[:limit]


def looks_like_injection(text):
    return bool(_INJECTION.search(text or ""))


def client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    return (fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR", "?"))


def rate_limited(key, limit=None, window=60):
    """Простой счётчик в кэше. True — лимит превышен."""
    limit = limit or settings.RATE_LIMIT_PER_MIN
    bucket = f"rl:{key}:{int(time.time() // window)}"
    count = cache.get(bucket, 0) + 1
    cache.set(bucket, count, window + 5)
    return count > limit
