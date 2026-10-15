"""Вход по токену (Authorization: Bearer ...) и сохранение чатов. Анонимный режим остаётся рабочим."""
import hashlib
import secrets
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import AuthToken, Chat, Message

TOKEN_TTL = timedelta(days=30)
MAX_CHATS = 200


def _hash(key):
    return hashlib.sha256(key.encode()).hexdigest()


def issue_token(user):
    key = secrets.token_urlsafe(32)
    AuthToken.objects.create(user=user, key_hash=_hash(key))
    return key


def auth_token(request):
    """Возвращает AuthToken или None. К базе не обращается, если заголовка нет."""
    header = request.META.get("HTTP_AUTHORIZATION", "")
    if not header.startswith("Bearer "):
        return None
    tok = AuthToken.objects.select_related("user").filter(key_hash=_hash(header[7:].strip())).first()
    if tok and timezone.now() - tok.created > TOKEN_TTL:
        tok.delete()
        return None
    return tok


def auth_user(request):
    tok = auth_token(request)
    return tok.user if tok else None


def get_owned_chat(user, chat_id):
    try:
        return Chat.objects.filter(id=chat_id, user=user).first()
    except (ValidationError, ValueError):
        return None


def bot_text(result):
    parts = [p.get("bubble", "") for p in result.get("panels", [])] + [result.get("details", "")]
    return " ".join(x for x in parts if x).strip()


def save_exchange(user, chat, message, result):
    if chat is None:
        chat = Chat.objects.create(user=user, title=" ".join(message.split())[:48] or "Чат")
        extra = Chat.objects.filter(user=user).order_by("-updated")[MAX_CHATS:]
        Chat.objects.filter(id__in=[c.id for c in extra]).delete()
    Message.objects.create(chat=chat, role="user", text=message)
    Message.objects.create(chat=chat, role="bot", text=bot_text(result), data=result)
    chat.save(update_fields=["updated"])
    return str(chat.id)
