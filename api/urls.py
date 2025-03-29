from django.urls import path
from . import views

urlpatterns = [
    path('search-users/', views.search_users, name='api_search_users'),
    path('check-repeat-violator/', views.check_repeat_violator, name='check_repeat_violator'),
] 