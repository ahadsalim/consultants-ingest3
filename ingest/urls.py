"""ingest URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .admin import admin_site

urlpatterns = [
    path('admin/', admin_site.urls),
    path('api/', include('ingest.api.urls')),
]

# Serve static files in development/production
if settings.DEBUG or True:  # Always serve static files
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
