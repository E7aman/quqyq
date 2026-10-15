from django.urls import re_path
from .consumers import CourtConsumer

websocket_urlpatterns = [re_path(r"^ws/court/(?P<code>[A-Z0-9]{4,8})/$", CourtConsumer.as_asgi())]
