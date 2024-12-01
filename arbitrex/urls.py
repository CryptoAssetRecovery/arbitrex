# arbitrex/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
import os

def debug_static(request):
    static_root = settings.STATIC_ROOT
    static_dirs = settings.STATICFILES_DIRS
    
    content = f"""
    STATIC_ROOT: {static_root}
    Files in STATIC_ROOT: {os.listdir(static_root) if os.path.exists(static_root) else 'Directory does not exist'}
    
    STATICFILES_DIRS: {static_dirs}
    Files in first STATICFILES_DIR: {os.listdir(static_dirs[0]) if static_dirs and os.path.exists(static_dirs[0]) else 'Directory does not exist'}
    """
    
    return HttpResponse(content, content_type='text/plain')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('strategies/', include('strategies.urls')),
    path('backtesting/', include('backtesting.urls')),
    path('data/', include('data.urls')),
    path("", include("dashboard.urls")),
    path('debug-static/', debug_static),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)