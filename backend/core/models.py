import uuid
from django.contrib.auth.models import User
from django.db import models


class AuthToken(models.Model):
    """Токен входа. В базе хранится только SHA-256 от токена, сам токен знает лишь клиент."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tokens")
    key_hash = models.CharField(max_length=64, unique=True)
    created = models.DateTimeField(auto_now_add=True)


class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="app_settings")
    data = models.JSONField(default=dict)


class Chat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chats")
    title = models.CharField(max_length=120, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="msgs")
    role = models.CharField(max_length=8)  # user | bot
    text = models.TextField(blank=True)    # для поиска по чатам
    data = models.JSONField(null=True, blank=True)  # полный ответ бота (панели, источники)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created", "id"]


class LibraryItem(models.Model):
    """Библиотека: сохранённые жалобы, статьи, ответы."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="library")
    kind = models.CharField(max_length=16)  # complaint | source | answer
    title = models.CharField(max_length=160)
    payload = models.JSONField(default=dict)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created", "-id"]
