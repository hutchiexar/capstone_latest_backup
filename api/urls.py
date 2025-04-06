from django.urls import path
from . import views

urlpatterns = [
    path('search-users/', views.search_users, name='api_search_users'),
    path('check-repeat-violator/', views.check_repeat_violator, name='check_repeat_violator'),
    path('violations/<int:violation_id>/images/', views.get_violation_images, name='get_violation_images'),
] 