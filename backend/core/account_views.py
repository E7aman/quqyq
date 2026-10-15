"""API аккаунта: вход, чаты (с поиском), библиотека, настройки."""
import json
import re
from functools import wraps

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import accounts
from .models import Chat, LibraryItem, UserSettings
from .security import clean_text, client_ip, rate_limited
from .views import _body

from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['POST'])
def register_view(request):
    # твой код регистрации
    return Response({'status': 'ok'})

@api_view(['POST'])
def login_view(request):
    # твой код авторизации
    return Response({'status': 'ok'})

@api_view(['POST'])
def logout_view(request):
    # твой код выхода
    return Response({'status': 'ok'})

@api_view(['GET'])
def profile_view(request):
    # твой код профиля
    return Response({'status': 'ok'})

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SETTINGS_DEFAULT = {"lang": "ru", "voice_out": False, "theme": "auto"}
LIBRARY_KINDS = {"complaint", "source", "answer"}
MAX_LIBRARY = 200


def err(text, status=400):
    return JsonResponse({"error": text}, status=status)


def authed(fn):
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        user = accounts.auth_user(request)
        if not user:
            return err("Требуется вход", 401)
        request.account = user
        return fn(request, *args, **kwargs)
    return wrapper


def _settings(user):
    row = UserSettings.objects.filter(user=user).first()
    return {**SETTINGS_DEFAULT, **(row.data if row else {})}


def _user_json(user):
    return {"email": user.email, "name": user.first_name, "settings": _settings(user)}


# ---------- авторизация ----------

@csrf_exempt
@require_http_methods(["POST"])
def register(request):
    if rate_limited(f"auth:{client_ip(request)}", limit=10):
        return err("Слишком много попыток. Подождите минуту.", 429)
    d = _body(request)
    email = clean_text(d.get("email"), 254).lower()
    password = str(d.get("password") or "")
    if not EMAIL_RE.match(email):
        return err("Введите корректный email")
    if not 8 <= len(password) <= 128:
        return err("Пароль: от 8 до 128 символов")
    if User.objects.filter(username=email).exists():
        return err("Такой аккаунт уже есть", 409)
    try:
        user = User.objects.create_user(username=email, email=email, password=password, first_name=clean_text(d.get("name"), 40))
    except IntegrityError:
        return err("Такой аккаунт уже есть", 409)
    return JsonResponse({"token": accounts.issue_token(user), "user": _user_json(user)}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def login(request):
    if rate_limited(f"auth:{client_ip(request)}", limit=10):
        return err("Слишком много попыток. Подождите минуту.", 429)
    d = _body(request)
    user = authenticate(username=clean_text(d.get("email"), 254).lower(), password=str(d.get("password") or ""))
    if not user:
        return err("Неверный email или пароль", 401)  # одно и то же сообщение для обоих случаев
    return JsonResponse({"token": accounts.issue_token(user), "user": _user_json(user)})


@csrf_exempt
@require_http_methods(["POST"])
def logout(request):
    tok = accounts.auth_token(request)
    if tok:
        tok.delete()
    return JsonResponse({"ok": True})


@csrf_exempt
@require_http_methods(["GET", "DELETE"])
@authed
def me(request):
    if request.method == "DELETE":  # право на удаление данных: аккаунт и всё связанное
        request.account.delete()
        return JsonResponse({"ok": True})
    return JsonResponse(_user_json(request.account))


# ---------- настройки ----------

@csrf_exempt
@require_http_methods(["GET", "PUT"])
@authed
def settings_view(request):
    user = request.account
    if request.method == "PUT":
        d = _body(request)
        new = _settings(user)
        if "lang" in d:
            if d["lang"] not in ("ru", "kk"):
                return err("lang: ru или kk")
            new["lang"] = d["lang"]
        if "voice_out" in d:
            if not isinstance(d["voice_out"], bool):
                return err("voice_out: true или false")
            new["voice_out"] = d["voice_out"]
        if "theme" in d:
            if d["theme"] not in ("auto", "light", "dark"):
                return err("theme: auto, light или dark")
            new["theme"] = d["theme"]
        UserSettings.objects.update_or_create(user=user, defaults={"data": new})
    return JsonResponse(_settings(user))


# ---------- чаты ----------

def _chat_brief(c, msgs, snippet=None):
    last = msgs[-1].text if msgs else ""
    out = {"id": str(c.id), "title": c.title, "updated": c.updated.isoformat(), "preview": last[:90]}
    if snippet:
        out["snippet"] = snippet
    return out


def _snippet(text, q):
    i = text.casefold().find(q)
    if i < 0:
        return None
    a = max(0, i - 30)
    return ("…" if a else "") + text[a:i + len(q) + 50].strip() + "…"


@csrf_exempt
@require_http_methods(["GET", "POST", "DELETE"])
@authed
def chats(request):
    user = request.account
    if request.method == "POST":
        c = Chat.objects.create(user=user, title=clean_text(_body(request).get("title"), 120) or "Новый чат")
        return JsonResponse(_chat_brief(c, []), status=201)
    if request.method == "DELETE":
        n, _ = Chat.objects.filter(user=user).delete()
        return JsonResponse({"deleted": n})
    q = clean_text(request.GET.get("q", ""), 100).casefold()
    out = []
    # Поиск в Python: SQLite не умеет регистронезависимый поиск по кириллице
    for c in Chat.objects.filter(user=user).order_by("-updated").prefetch_related("msgs")[:accounts.MAX_CHATS]:
        msgs = list(c.msgs.all())
        snippet = None
        if q:
            if q in c.title.casefold():
                snippet = c.title
            else:
                snippet = next((s for m in msgs if (s := _snippet(m.text, q))), None)
            if not snippet:
                continue
        out.append(_chat_brief(c, msgs, snippet if q else None))
    return JsonResponse({"chats": out})


@csrf_exempt
@require_http_methods(["GET", "PATCH", "DELETE"])
@authed
def chat_detail(request, chat_id):
    c = accounts.get_owned_chat(request.account, chat_id)
    if not c:
        return err("Чат не найден", 404)
    if request.method == "DELETE":
        c.delete()
        return JsonResponse({"ok": True})
    if request.method == "PATCH":
        title = clean_text(_body(request).get("title"), 120)
        if not title:
            return err("Название не может быть пустым")
        c.title = title
        c.save(update_fields=["title", "updated"])
    return JsonResponse({"id": str(c.id), "title": c.title, "updated": c.updated.isoformat(),
                         "messages": [{"id": m.id, "role": m.role, "text": m.text, "data": m.data,
                                       "created": m.created.isoformat()} for m in c.msgs.all()]})


# ---------- библиотека ----------

def _lib_json(i):
    return {"id": i.id, "kind": i.kind, "title": i.title, "payload": i.payload, "created": i.created.isoformat()}


@csrf_exempt
@require_http_methods(["GET", "POST"])
@authed
def library(request):
    user = request.account
    if request.method == "POST":
        d = _body(request)
        payload = d.get("payload", {})
        if d.get("kind") not in LIBRARY_KINDS:
            return err("kind: complaint, source или answer")
        if not isinstance(payload, dict) or len(json.dumps(payload, ensure_ascii=False)) > 20000:
            return err("payload: объект до 20 КБ")
        title = clean_text(d.get("title"), 160)
        if not title:
            return err("Нужно название")
        if LibraryItem.objects.filter(user=user).count() >= MAX_LIBRARY:
            return err("Библиотека заполнена (200 записей)", 409)
        return JsonResponse(_lib_json(LibraryItem.objects.create(user=user, kind=d["kind"], title=title, payload=payload)), status=201)
    qs = LibraryItem.objects.filter(user=user)
    if request.GET.get("kind") in LIBRARY_KINDS:
        qs = qs.filter(kind=request.GET["kind"])
    return JsonResponse({"items": [_lib_json(i) for i in qs[:MAX_LIBRARY]]})


@csrf_exempt
@require_http_methods(["DELETE"])
@authed
def library_item(request, item_id):
    n, _ = LibraryItem.objects.filter(id=item_id, user=request.account).delete()
    return JsonResponse({"ok": True}) if n else err("Запись не найдена", 404)
