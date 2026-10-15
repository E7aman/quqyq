# Контракт API (бэкенд ↔ фронтенд)

Все ответы JSON. Ошибка всегда `{"error": "текст"}` + HTTP-статус (400 неверные данные, 401 нужен вход, 404 не найдено,
409 конфликт, 429 слишком много запросов, 503 ИИ недоступен). Адрес в разработке: `/api/...` (Vite проксирует на :8000).
**Правило для двоих:** новые поля добавлять можно, существующие не удалять и не переименовывать без предупреждения.

Вход: заголовок `Authorization: Bearer <token>`. Токен выдают `register`/`login`, живёт 30 дней. Фронтенд хранит его
в `localStorage`. Без токена чат и суд работают как раньше (анонимно, без сохранения).

## Карта схемы экрана → запросы

| Блок на схеме | Что вызывает |
|---|---|
| главная, текстовый ввод | `POST /api/chat/` |
| всплывающие подсказки | `GET /api/suggestions/` |
| голосовой ввод | Web Speech API в браузере; запасной вариант `POST /api/transcribe/` |
| кнопка «прикрепить» | `POST /api/analyze/` (фото или PDF) |
| переключатель языков | параметр `lang` ("ru" \| "kk") в запросах + `PUT /api/settings/` для вошедших |
| вкладка / новый чат | `POST /api/chat/` с `chat_id: "new"` (или `POST /api/chats/`) |
| поиск по чатам | `GET /api/chats/?q=...` |
| список чатов, открыть, переименовать, удалить | `GET /api/chats/`, `GET/PATCH/DELETE /api/chats/<id>/` |
| библиотека | `GET/POST /api/library/`, `DELETE /api/library/<id>/` |
| настройки | `GET/PUT /api/settings/`, `DELETE /api/auth/me/` (удалить аккаунт) |
| авторизация | `POST /api/auth/register/`, `login/`, `logout/`, `GET /api/auth/me/` |
| войти в комнату по QR | сканер в браузере → код из ссылки `?code=XXXXX` → `GET /api/rooms/<код>/` → WebSocket |

## Авторизация
- `POST /api/auth/register/` `{email, password (8–128), name?}` → 201 `{token, user}`. Занятый email: 409.
- `POST /api/auth/login/` `{email, password}` → `{token, user}`. Неверные данные: 401 (текст одинаковый для обоих случаев). Лимит: 10 попыток в минуту с IP.
- `POST /api/auth/logout/` → `{ok: true}`.
- `GET /api/auth/me/` → `{email, name, settings}`. `DELETE /api/auth/me/` удаляет аккаунт и все его чаты и библиотеку.
- `user` = `{email, name, settings: {lang, voice_out, theme}}`.

## Чат
`POST /api/chat/` `{message, lang, chat_id?, history?}` (`history` — до 3 последних реплик пользователя строками, для продолжений вроде «а если я его…»; у вошедших с `chat_id` контекст берётся из сохранённого чата) →
```json
{"refused": false, "panels": [{"pose": "pointing", "bubble": "..."}], "details": "...",
 "sources": [{"id","title","article","source","url","constitution","verified","section","quote","confidence"}],
 "disclaimer": "...", "mode": "gemini|offline|guard", "safety": "(только при угрозах/насилии)", "chat_id": "(только если вошёл)"}
```
- **Новые поля (только добавлены, старые не менялись):**
  - `sources[].kind`: `"norm"` (закон/Конституция), `"guide"` (практическая памятка, не закон: пометка «Совет») или `"concept"` (принцип/программный документ, не норма права: пометка «Принцип»).
  - `constitution_refs`: `["преамбула", "ст. 33"]` — если концепция закреплена в Конституции (требование п. 4.1). Показать заметной плашкой «Закреплено в Конституции 2026: …»; сами статьи лежат в `sources` с `constitution: true`.
  - `follow_up`: `["Сколько вам лет?", ...]` до 2 уточняющих вопросов (может отсутствовать). Показать кнопками-подсказками под ответом.
  - `urgency`: `"normal"` | `"high"`. При `high` показать ответ заметно (красная полоса, барс `stern`).
  - `help_lines`: `[{"number": "112", "label": "..."}]` только при угрозах/насилии/травле. Рендерить кнопками `tel:112`.
- `pose` ∈ idle, thinking, pointing, surprised, stern, happy. При отказе `refused: true`, `sources: []`, при инъекции ещё `reason: "injection"`.
- Вошедший пользователь: без `chat_id` или `"new"` создаётся новый чат, `chat_id` из ответа передавать дальше. Чужой/неверный id: 404.

## Чаты (нужен вход)
- `GET /api/chats/?q=` → `{chats: [{id, title, updated, preview, snippet?}]}`, новые сверху. `q` ищет по заголовкам и всем сообщениям, регистр не важен; `snippet` показывает совпавший фрагмент.
- `POST /api/chats/` `{title?}` → 201 `{id, title, updated, preview}`.
- `GET /api/chats/<id>/` → `{id, title, updated, messages: [{id, role: "user"|"bot", text, data, created}]}`; у `bot` в `data` лежит полный ответ чата (панели, источники).
- `PATCH /api/chats/<id>/` `{title}`, `DELETE /api/chats/<id>/`, `DELETE /api/chats/` (удалить все → `{deleted: N}`). Максимум 200 чатов, старые удаляются сами.

## Библиотека (нужен вход)
- `GET /api/library/?kind=complaint|source|answer` → `{items: [{id, kind, title, payload, created}]}`.
- `POST /api/library/` `{kind, title, payload: {...до 20 КБ}}` → 201. Примеры: жалоба (`payload` = ответ `/api/complaint/draft/`), статья (`payload` = объект из `sources`), ответ бота. Максимум 200 записей.
- `DELETE /api/library/<id>/`.

## Настройки (нужен вход)
`GET /api/settings/` → `{lang: "ru"|"kk", voice_out: bool, theme: "auto"|"light"|"dark"}`; `PUT` принимает любое подмножество этих полей.

## Подсказки
`GET /api/suggestions/?q=&lang=` → `{suggestions: [{text, kind: "question"|"article"}]}` до 6 штук. Без `q` стартовые вопросы; с `q`: подходящие вопросы и, если введён номер («статья 33»), элемент `kind: "article"`. Вызывать с задержкой ~250 мс при вводе.

## Документы и вложения
- `POST /api/complaint/draft/` `{situation, lang, applicant?, recipient?}` → `{title, recipient, applicant, paragraphs[], demands[], sources[], mode}`.
- `POST /api/complaint/docx/` тем же объектом (можно отредактированным) + `lang` → файл `.docx`.
- `POST /api/analyze/` multipart: `image` (jpg, png, webp или **pdf**, до 6 МБ), `lang` → `{doc_type, found[], missing[], advice, disclaimer}`.
- `POST /api/transcribe/` multipart: `audio` (webm, ogg, wav, mp3, m4a, до 5 МБ), `lang` → `{text}`. Нужен ключ Gemini.

## Суд
- `POST /api/rooms/` `{lang}` → `{code}`. `GET /api/rooms/<код>/` → `{exists, lang?, phase?, players?, full?, started?}`; показывать «комната не найдена / уже началась / заполнена» до входа.
- WebSocket `/ws/court/<код>/`. Клиент → сервер: `join {name, role, token?}`, `set_case {text}`, `start`, `statement {text}`, `answer {qid, text}`, `force_next`.
  Сервер → клиент: `joined {you}`, `state {room}`, `error {text}`. Фазы: lobby → statements → questions → verdict. Закрытие с кодом 4404: комнаты нет.
- Ссылка на комнату (в QR): `<адрес сайта>/?code=XXXXX`.

## Что пока не готово / на заметку
- Новые эндпоинты аккаунта, чатов, библиотеки, настроек, подсказок покрыты автотестами. Расшифровка голоса и PDF проверены только с подставной моделью, без настоящего Gemini.
- Фронтенд пока работает на локальной истории (`localStorage`). Вход, серверные чаты и библиотеку нужно подключить на фронте.
- Токен в `localStorage` приемлем для проекта, но уязвим при XSS: не вставляйте пользовательский HTML через `dangerouslySetInnerHTML`.
