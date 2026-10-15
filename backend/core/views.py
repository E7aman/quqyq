import json
from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
import io

from . import accounts, doc_generator, llm, rag, rooms, services
from .security import clean_text, client_ip, rate_limited

MAX_IMAGE = 6 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
AUDIO_TYPES = {"audio/webm", "audio/ogg", "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp4", "audio/aac", "audio/m4a"}
MAX_AUDIO = 5 * 1024 * 1024


def _body(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


def _limited(request, bucket="api"):
    if rate_limited(f"{bucket}:{client_ip(request)}"):
        return JsonResponse({"error": "Слишком много запросов. Подождите минуту."}, status=429)
    return None


def spa(request):
    index = settings.FRONTEND_DIST / "index.html"
    if index.exists():
        return HttpResponse(index.read_text(encoding="utf-8"))
    return HttpResponse("Фронтенд не собран: cd frontend && npm install && npm run build", status=503)


@require_GET
def health(request):
    return JsonResponse({"ok": True, "gemini": llm.available(), "chunks": len(__import__("core.rag", fromlist=["x"]).get_index().chunks)})


@csrf_exempt
@require_POST
def chat(request):
    """Вопрос боту. Если пользователь вошёл (Bearer-токен), диалог сохраняется: chat_id нет или "new" — новый чат."""
    if (r := _limited(request)):
        return r
    data = _body(request)
    user = accounts.auth_user(request)
    chat_obj = None
    if user and data.get("chat_id") not in (None, "", "new"):
        chat_obj = accounts.get_owned_chat(user, data["chat_id"])
        if chat_obj is None:
            return JsonResponse({"error": "Чат не найден"}, status=404)
    message = clean_text(data.get("message", ""))
    if chat_obj is not None:  # вошедший пользователь: контекст берём из сохранённого чата, а не от клиента
        history = [m.text for m in chat_obj.msgs.filter(role="user").order_by("-created", "-id")[:services.MAX_HISTORY]][::-1]
    else:  # анонимный режим: фронтенд присылает последние реплики пользователя
        raw = data.get("history")
        history = raw[-services.MAX_HISTORY:] if isinstance(raw, list) else []
    result = services.answer_chat(message, data.get("lang", "ru"), history)
    if user and message:
        result["chat_id"] = accounts.save_exchange(user, chat_obj, message, result)
    return JsonResponse(result)


@csrf_exempt
@require_POST
def create_room(request):
    if (r := _limited(request, "room")):
        return r
    data = _body(request)
    return JsonResponse({"code": rooms.create_room(data.get("lang", "ru"))})


@csrf_exempt
@require_POST
def complaint_draft(request):
    if (r := _limited(request)):
        return r
    d = _body(request)
    return JsonResponse(services.draft_complaint(d.get("situation", ""), d.get("lang", "ru"),
                                                 clean_text(d.get("applicant"), 120), clean_text(d.get("recipient"), 200)))


@csrf_exempt
@require_POST
def complaint_docx(request):
    if (r := _limited(request)):
        return r
    d = _body(request)
    payload = {
        "title": clean_text(d.get("title"), 80), "recipient": clean_text(d.get("recipient"), 200),
        "applicant": clean_text(d.get("applicant"), 120),
        "paragraphs": [clean_text(p, 1500) for p in (d.get("paragraphs") or [])[:10]],
        "demands": [clean_text(p, 400) for p in (d.get("demands") or [])[:8]],
        "sources": [clean_text(f"{s.get('title', '')}, {s.get('article', '')}", 250) for s in (d.get("sources") or [])[:6] if isinstance(s, dict)],
    }
    blob = doc_generator.build_docx(payload, d.get("lang", "ru"))
    return FileResponse(io.BytesIO(blob), as_attachment=True, filename="zhaloba.docx",
                        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


def _real_file_type(content_type, data):
    """Проверка «магических байтов»: JPEG, PNG, WEBP, PDF."""
    head = data[:12]
    if content_type == "image/jpeg":
        return head.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    if content_type == "application/pdf":
        return head.startswith(b"%PDF")
    return False


@csrf_exempt
@require_POST
def analyze(request):
    if (r := _limited(request, "img")):
        return r
    f = request.FILES.get("image")
    if not f or f.content_type not in IMAGE_TYPES or f.size > MAX_IMAGE:
        return JsonResponse({"error": "Нужен JPG, PNG, WEBP или PDF до 6 МБ."}, status=400)
    data = f.read()
    if not _real_file_type(f.content_type, data):  # тип от браузера можно подделать: сверяем начало файла
        return JsonResponse({"error": "Файл не похож на заявленный формат."}, status=400)
    try:
        return JsonResponse(services.analyze_image(data, f.content_type, request.POST.get("lang", "ru")))
    except llm.LLMError as exc:
        return JsonResponse({"error": f"ИИ сейчас недоступен: {exc}"}, status=503)


# ---------- подсказки, статус комнаты, расшифровка голоса ----------

SUGGEST = {
    "ru": ["Имею ли я право на бесплатное образование?", "Могут ли меня задержать без решения суда?",
           "Меня уволили без объяснения причин. Что делать?", "Как защитить свои права в суде?",
           "Куда можно обратиться с жалобой на действия чиновника?", "Что значит презумпция невиновности?",
           "Можно ли лишить меня жилья без решения суда?", "Какие права гарантирует Конституция на охрану здоровья?",
           "Мне угрожают в интернете. Что делать?", "Что значит принцип «Закон и Порядок» в преамбуле Конституции?"],
    "kk": ["Тегін білім алуға құқығым бар ма?", "Мені сот шешімінсіз ұстауға бола ма?",
           "Мені себебін түсіндірмей жұмыстан шығарды. Не істеймін?", "Құқықтарымды сотта қалай қорғауға болады?",
           "Шенеунік әрекетіне шағымды қайда жазуға болады?", "Кінәсіздік презумпциясы дегеніміз не?",
           "Мені сот шешімінсіз тұрғын үйден айыруға бола ма?", "Конституция денсаулық сақтау құқығын қалай кепілдендіреді?",
           "Интернетте маған қауіп төндіріп жатыр. Не істеймін?", "Конституция кіріспесіндегі «Заң және Тәртіп» қағидаты нені білдіреді?"],
}


@require_GET
def suggestions(request):
    """Всплывающие подсказки. Без q — стартовые вопросы; с q — подходящие вопросы и прямой переход на статью."""
    lang = "kk" if request.GET.get("lang") == "kk" else "ru"
    q = clean_text(request.GET.get("q", ""), 100).casefold()
    items = []
    if q:
        art = rag.by_article(q, k=1)
        if art:
            n = art[0]["article"].replace("ст. ", "")
            items.append({"text": f"Статья {n}" if lang == "ru" else f"{n}-бап", "kind": "article"})
        words = q.split()
        for text in SUGGEST[lang]:
            if all(w in text.casefold() for w in words):
                items.append({"text": text, "kind": "question"})
    else:
        items = [{"text": t, "kind": "question"} for t in SUGGEST[lang][:6]]
    return JsonResponse({"suggestions": items[:6]})


@require_GET
def room_status(request, code):
    """Проверка кода комнаты до входа (экран «войти по QR»)."""
    if (r := _limited(request, "room")):
        return r
    room = rooms.get_room(code.upper())
    if not room:
        return JsonResponse({"exists": False})
    return JsonResponse({"exists": True, "lang": room["lang"], "phase": room["phase"], "players": len(room["players"]),
                         "full": len(room["players"]) >= rooms.MAX_PLAYERS, "started": room["phase"] != "lobby"})


@csrf_exempt
@require_POST
def transcribe(request):
    """Голос в текст через Gemini (запасной вариант для браузеров без Web Speech API и для казахского)."""
    if (r := _limited(request, "stt")):
        return r
    f = request.FILES.get("audio")
    mime = (f.content_type or "").split(";")[0] if f else ""
    if not f or mime not in AUDIO_TYPES or f.size > MAX_AUDIO:
        return JsonResponse({"error": "Нужна аудиозапись (webm, ogg, wav, mp3, m4a) до 5 МБ."}, status=400)
    try:
        lang = "казахском" if request.POST.get("lang") == "kk" else "русском"
        d = llm.generate_json(f"Расшифруй речь на {lang} языке дословно. Верни ТОЛЬКО JSON: {{\"text\": \"...\"}}.",
                              "Расшифруй запись.", image=f.read(), mime=mime, temperature=0.0)
        return JsonResponse({"text": clean_text(d.get("text", ""), 2000)})
    except llm.LLMError as exc:
        return JsonResponse({"error": f"Расшифровка недоступна: {exc}"}, status=503)
