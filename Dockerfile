# ---- 1) сборка фронтенда ----
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- 2) бэкенд + готовая сборка фронта (один процесс: сайт + API + WebSocket) ----
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
# settings.py ждёт сборку по пути ../frontend/dist
COPY --from=frontend /app/frontend/dist /app/frontend/dist
RUN python manage.py collectstatic --noinput

EXPOSE 10000
# Render передаёт порт в $PORT. Миграции при каждом старте безопасны (повторно ничего не делают).
CMD ["sh", "-c", "python manage.py migrate --noinput && daphne -b 0.0.0.0 -p ${PORT:-10000} config.asgi:application"]
