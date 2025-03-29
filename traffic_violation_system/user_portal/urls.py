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
    path('notifications/', views.user_notifications, name='user_notifications'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('vehicles/register/', views.register_vehicle, name='register_vehicle'),
    path('vehicles/<int:vehicle_id>/', views.vehicle_detail, name='vehicle_detail'),
    path('admin/user-management/', views.user_management, name='user_management'),
    path('admin/regular-users/', views.regular_users_list, name='regular_users_list'),
    
    # Operator lookup URLs
    path('operator-lookup/', views.operator_lookup, name='operator_lookup'),
    path('operator-lookup/search/', views.operator_lookup_search, name='operator_lookup_search'),
    path('operator-lookup/history/', views.operator_lookup_history, name='operator_lookup_history'),
] 