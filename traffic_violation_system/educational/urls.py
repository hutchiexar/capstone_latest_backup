from django.urls import path
from . import views

app_name = 'educational'

urlpatterns = [
    # User portal views
    path('', views.landing_page, name='landing_page'),
    path('topics/', views.topic_list, name='topic_list'),
    path('topics/<int:topic_id>/', views.topic_detail, name='topic_detail'),
    path('toggle-bookmark/<int:topic_id>/', views.toggle_bookmark, name='toggle_bookmark'),
    path('mark-completed/<int:topic_id>/', views.mark_as_completed, name='mark_as_completed'),
    path('track-progress/<int:topic_id>/', views.track_progress, name='track_progress'),
    path('get-topic/<int:topic_id>/', views.get_topic, name='get_topic'),
    path('get-category-topics/', views.get_category_topics, name='get_category_topics'),
    path('bookmarks/', views.user_bookmarks, name='user_bookmarks'),
    path('progress/', views.user_progress, name='user_progress'),
    
    # Admin views
    path('admin/', views.admin_index, name='admin_index'),
    path('admin/dashboard/', views.admin_index, name='admin_dashboard'),
    path('admin/data/', views.admin_educational_data, name='admin_educational_data'),
    path('admin/categories/', views.admin_category_list, name='admin_category_list'),
    path('admin/categories/create/', views.admin_category_create, name='admin_category_create'),
    path('admin/categories/edit/<int:category_id>/', views.admin_category_edit, name='admin_category_edit'),
    path('admin/categories/delete/<int:category_id>/', views.admin_category_delete, name='admin_category_delete'),
    path('admin/topics/', views.admin_topic_list, name='admin_topic_list'),
    path('admin/topics/create/', views.admin_topic_create, name='admin_topic_create'),
    path('admin/topics/edit/<int:topic_id>/', views.admin_topic_edit, name='admin_topic_edit'),
    path('admin/topics/delete/<int:topic_id>/', views.admin_topic_delete, name='admin_topic_delete'),
    path('admin/topics/publish/<int:topic_id>/', views.admin_topic_publish, name='admin_topic_publish'),
    path('admin/topics/preview/<int:topic_id>/', views.admin_topic_preview, name='admin_topic_preview'),
] 