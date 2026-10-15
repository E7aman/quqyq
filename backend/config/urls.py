from django.contrib import admin
from django.urls import path, re_path, include
from core import views as core_views
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Swagger / OpenAPI URLs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Подключение основных API вашего приложения
    path('api/', include('core.urls')),

    # Фронтенд (React SPA): всё, что не api/, admin/, static/, ws/, отдаёт index.html
    re_path(r"^(?!api/|admin/|static/|ws/).*$", core_views.spa),
]
