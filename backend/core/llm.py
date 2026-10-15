"""Обёртка над Gemini. Ключ берётся только из окружения (.env)."""
import json
import logging
import re
from django.conf import settings

log = logging.getLogger(__name__)


class LLMError(Exception):
    pass


def available():
    return bool(settings.GEMINI_API_KEY)


_client = None


def _get_client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _parse_json(text):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


def generate_json(system, user, image=None, mime="image/jpeg", temperature=0.3):
    """Возвращает dict. image — bytes (для анализа фото документа)."""
    if not available():
        raise LLMError("GEMINI_API_KEY не задан")
    from google.genai import types

    contents = [user]
    if image:
        contents = [types.Part.from_bytes(data=image, mime_type=mime), user]
    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        temperature=temperature,
        max_output_tokens=2048,
    )
    last = None
    for model in dict.fromkeys([settings.GEMINI_MODEL, settings.GEMINI_FALLBACK_MODEL]):
        try:
            resp = _get_client().models.generate_content(model=model, contents=contents, config=config)
            return _parse_json(resp.text)
        except Exception as exc:  # сеть, лимиты, неверная модель, битый JSON
            log.warning("Gemini %s failed: %s", model, exc)
            last = exc
    raise LLMError(str(last))
