from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.decorators.cache import never_cache
import os

urlpatterns = [
    path('admin/', admin.site.urls, name='admin'),
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(
        next_page='login',
        extra_context={'no_cache': True}
    ), name='logout'),
    path('reports/', include('reports.urls')),
    path('', include('traffic_violation_system.adjudication_history_urls')),
    path('', include('traffic_violation_system.reports.urls')),
    path('', include('traffic_violation_system.urls')),
]

# Always serve static files in any environment
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# For development environment, serve media files directly
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# For production environment like Render, use our custom media server
elif os.environ.get('RENDER', 'False') == 'True':
    from traffic_violation_system.serve_media import MediaFileServer
    
    # Add a path to serve media files
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', MediaFileServer.serve_media_file, name='serve_media'),
    ]
else:
    # Fallback for other production environments
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)