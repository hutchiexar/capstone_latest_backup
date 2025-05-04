from django.urls import path
from . import views
import educational_analytics  # Import the educational analytics module

urlpatterns = [
    path('search-users/', views.search_users, name='api_search_users'),
    path('check-repeat-violator/', views.check_repeat_violator, name='check_repeat_violator'),
    path('violations/<int:violation_id>/images/', views.get_violation_images, name='get_violation_images'),
    path('search_driver/<str:pd_number>/', views.search_driver_by_pd, name='search_driver_by_pd'),
    
    # Educational analytics endpoints
    path('educational-analytics/', educational_analytics.educational_analytics, name='educational_analytics'),
    path('educational-analytics/<str:time_range>/', educational_analytics.educational_analytics_by_range, name='educational_analytics_by_range'),
] 