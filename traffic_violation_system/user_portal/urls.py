from django.urls import path
from django.views.generic.base import RedirectView
from . import views

app_name = 'user_portal'

urlpatterns = [
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('violations/', views.user_violations, name='user_violations'),
    # Redirect NCAP violations route to the main violations view
    path('ncap-violations/', RedirectView.as_view(pattern_name='user_portal:user_violations'), name='user_ncap_violations'),
    path('ncap-violations/<int:violation_id>/print/', views.print_ncap_violation_form, name='print_ncap_violation_form'),
    path('notifications/', views.user_notifications, name='user_notifications'),
    path('violations/<int:violation_id>/', views.violation_detail, name='violation_detail'),
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('settings/', views.user_settings, name='user_settings'),
    path('settings/change-password/', views.change_password, name='change_password'),
    path('settings/delete-account/', views.delete_account, name='delete_account'),
    path('file-report/', views.file_report, name='file_report'),
    path('notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/<int:notification_id>/detail/', views.notification_detail, name='notification_detail'),
    path('notifications/load-more/', views.load_more_notifications, name='load_more_notifications'),
    # Debug endpoints
    path('notifications/create-test/', views.create_test_notification, name='create_test_notification'),
    path('notifications/debug/', views.debug_notifications, name='debug_notifications'),
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('vehicles/register/', views.register_vehicle, name='register_vehicle'),
    path('vehicles/<int:vehicle_id>/', views.vehicle_detail, name='vehicle_detail'),
    path('admin/user-management/', views.user_management, name='user_management'),
    path('admin/regular-users/', views.regular_users_list, name='regular_users_list'),
    
    # Educational materials routes
    path('education/', views.education_topics, name='education_topics'),
    path('education/topic/<int:topic_id>/', views.education_topic_detail, name='education_topic_detail'),
    path('education/bookmarks/', views.education_bookmarks, name='education_bookmarks'),
    path('education/progress/', views.education_progress, name='education_progress'),
    
    # Driver Application Routes
    path('driver/apply/', views.driver_apply, name='driver_apply'),
    path('driver/application/status/', views.driver_application_status, name='driver_application_status'),
    path('driver/id-card/', views.driver_id_card, name='driver_id_card'),
    path('driver/<str:driver_id>/verify/', views.driver_id_verify, name='driver_id_verify'),
    
    # Admin Driver Application Management
    path('admin/driver-applications/', views.driver_applications_manage, name='driver_applications_manage'),
    path('admin/driver-application/<int:application_id>/review/', views.driver_application_review, name='driver_application_review'),
] 