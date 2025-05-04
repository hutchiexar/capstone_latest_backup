from django.urls import path
from . import educational_analytics

# These URLs would be included in your main urls.py file
# Example: path('api/', include('your_app.urls_educational')),

urlpatterns = [
    # Educational analytics API endpoints
    path('educational-analytics/', educational_analytics.educational_analytics, name='educational_analytics'),
    path('educational-analytics/<str:time_range>/', educational_analytics.educational_analytics_by_range, name='educational_analytics_by_range'),
] 