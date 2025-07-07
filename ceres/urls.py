"""
CERES Simplified URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.customers.urls')),
    path('api/', include('apps.risk.urls')),
    path('api/', include('apps.sanctions.urls')),
    path('api/', include('apps.cases.urls')),
    path('api/', include('apps.documents.urls')),
    path('api/', include('apps.compliance.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Add debug toolbar URLs
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns

# Customize admin site
admin.site.site_header = 'CERES - Sistema Simplificado'
admin.site.site_title = 'CERES Admin'
admin.site.index_title = 'Painel de Administração'

