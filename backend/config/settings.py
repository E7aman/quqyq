import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEBUG = os.environ.get("DEBUG", "1") == "1"
# В режиме разработки (DEBUG=1) допустимы запасные значения, чтобы всё запускалось с первого раза.
# В боевом режиме (DEBUG=0) секретный ключ обязателен, а хосты ограничены списком из ALLOWED_HOSTS.
SECRET_KEY = os.environ.get("SECRET_KEY") or ("dev-insecure-key-change-me" if DEBUG else "")
if not SECRET_KEY:
    raise RuntimeError("Задайте SECRET_KEY в .env (при DEBUG=0 он обязателен)")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "*" if DEBUG else "localhost,127.0.0.1").split(",") if h.strip()]

# Render сам задаёт эти переменные для веб-сервиса
RENDER_HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
if RENDER_HOST and RENDER_HOST not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_HOST)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]
if RENDER_HOST:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_HOST}")

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",        # <--- Добавь эту строку
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",     # <--- Добавь эту строку
    "django.contrib.messages",     # <--- Добавь эту строку
    "django.contrib.staticfiles",
    "channels",
    'corsheaders',
    'drf_spectacular',
    "core",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # раздаёт /static/ (сборку фронта) в проде
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # <--- Сюда
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
# SQLite: аккаунты, чаты, библиотека. Комнаты суда по-прежнему живут в памяти, база знаний — файлы.
# На Render задаётся DATABASE_URL (Postgres). Без неё — локальный SQLite, как раньше.
if os.environ.get("DATABASE_URL"):
    DATABASES = {"default": dj_database_url.config(conn_max_age=600)}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

# Для демо хватает in-memory слоя (один процесс). Для продакшена — channels_redis.
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

STATIC_URL = "/static/"
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"
STATICFILES_DIRS = [FRONTEND_DIST] if FRONTEND_DIST.exists() else []
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_ROOT.mkdir(exist_ok=True)  # иначе WhiteNoise ругается, пока не запускали collectstatic
# Без манифеста: Vite уже кладёт хэши в имена файлов
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# За прокси Render: понимать, что снаружи https
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash")
RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "20"))
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
DATA_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024


# Журнал вопросов без ответа (python manage.py show_gaps). Выключен по умолчанию: см. core/gaps.py
LOG_GAPS = os.environ.get("LOG_GAPS", "0") == "1"
GAPS_FILE = BASE_DIR / "data" / "gaps.jsonl"

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Quqyq AI Backend API',
    'DESCRIPTION': 'API сервиса Quqyq AI — интеллектуального навигатора по Конституции 2026 и внутренней политике РК',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Фронт и API на одном домене, CORS в проде не нужен. Открываем только в разработке
# (или явным списком через CORS_ALLOWED_ORIGINS, если фронт когда-нибудь вынесут отдельно).
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
