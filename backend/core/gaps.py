"""Журнал пробелов: какие вопросы остались без ответа в базе. Помогает понять, какие документы добавить.

Включается переменной LOG_GAPS=1 (по умолчанию выключено: тексты вопросов могут содержать личные данные, п. 13.1 положения).
Пишутся только вопросы, на которые бот ответил отказом, без номеров, e-mail и телефонов, не длиннее 200 символов, без привязки к человеку.
"""
import json
import logging
import re
import time
from pathlib import Path

from django.conf import settings

log = logging.getLogger(__name__)
_PII = re.compile(r"([\w.+-]+@[\w-]+\.[\w.]+|\+?\d[\d\s()\-]{6,}\d|\b\d{5,}\b)")


def anonymize(text):
    return _PII.sub("[…]", " ".join(str(text).split()))[:200]


def log_gap(question, lang, reason="no_sources"):
    if not getattr(settings, "LOG_GAPS", False):
        return
    try:
        path = Path(settings.GAPS_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"t": int(time.time()), "q": anonymize(question), "lang": lang, "reason": reason}, ensure_ascii=False) + "\n")
    except OSError:
        log.warning("gaps: не удалось записать журнал")


def top_gaps(limit=30):
    path = Path(settings.GAPS_FILE)
    if not path.exists():
        return []
    counts = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            q = json.loads(line)["q"].strip().lower()
        except (ValueError, KeyError):
            continue
        counts[q] = counts.get(q, 0) + 1
    return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
