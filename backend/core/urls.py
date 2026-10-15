from django.urls import path
from . import account_views as a, views

urlpatterns = [
    path("health/", views.health),
    # чат, документы, голос
    path("chat/", views.chat),
    path("suggestions/", views.suggestions),
    path("complaint/draft/", views.complaint_draft),
    path("complaint/docx/", views.complaint_docx),
    path("analyze/", views.analyze),
    path("transcribe/", views.transcribe),
    # суд
    path("rooms/", views.create_room),
    path("rooms/<str:code>/", views.room_status),
    # аккаунт
    path("auth/register/", a.register),
    path("auth/login/", a.login),
    path("auth/logout/", a.logout),
    path("auth/me/", a.me),
    path("settings/", a.settings_view),
    path("chats/", a.chats),
    path("chats/<uuid:chat_id>/", a.chat_detail),
    path("library/", a.library),
    path("library/<int:item_id>/", a.library_item),
    
]
