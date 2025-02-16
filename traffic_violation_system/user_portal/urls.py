from django.urls import path
from . import views

app_name = 'user_portal'

urlpatterns = [
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('violations/', views.user_violations, name='user_violations'),
    path('violations/<int:violation_id>/', views.violation_detail, name='violation_detail'),
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('settings/', views.user_settings, name='user_settings'),
    path('settings/change-password/', views.change_password, name='change_password'),
    path('settings/delete-account/', views.delete_account, name='delete_account'),
    path('file-report/', views.file_report, name='file_report'),
    path('notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
] 