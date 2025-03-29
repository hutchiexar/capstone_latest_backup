from django.urls import path, include
from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as auth_views
from . import views
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Landing Pages
    path('', views.landing_home, name='landing_home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('contact/', views.contact, name='contact'),
    path('track/', views.track_violation, name='track_violation'),

    path('accounts/login/', views.login_view, name='login'),
    path('accounts/register/', views.register, name='register'),
    path('accounts/profile/', views.profile, name='profile'),
    path('accounts/profile/edit/', views.edit_profile, name='edit_profile'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('upload-violation/', views.upload_violation, name='upload_violation'),
    path('issue-ticket/', views.issue_ticket, name='issue_ticket'),
    path('violation/<int:violation_id>/', views.violation_detail, name='violation_detail'),
    path('violation/<int:violation_id>/modal/', views.violation_detail_modal, name='violation_detail_modal'),
    path('violation/<int:violation_id>/process-payment/', views.process_payment, name='process_payment'),
    path('violation/<int:violation_id>/record-payment/', views.record_payment, name='record_payment'),
    
    # User management URLs
    path('users/', views.users_list, name='users_list'),
    path('users/create/', views.create_user, name='create_user'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('activity-history/', views.activity_history, name='activity_history'),
    path('api/statistics/<str:time_range>/', views.get_statistics, name='get_statistics'),
    path('webhook/payment/', views.payment_webhook, name='payment_webhook'),
    path('violations/', views.violations_list, name='violations_list'),
    path('violations/<int:violation_id>/update-status/', views.update_violation_status, name='update_violation_status'),
    path('users/<int:user_id>/modal/', views.user_detail_modal, name='user_detail_modal'),
    path('ncap-violations/', views.ncap_violations_list, name='ncap_violations_list'),
    
    # NCAP Violation creation URLs
    path('ncap-violations/create/', views.create_ncap_violation, name='create_ncap_violation'),
    path('ncap-violations/save/', views.save_ncap_violation, name='save_ncap_violation'),
    
    path('adjudication/', views.adjudication_list, name='adjudication_list'),
    path('violation/<int:violation_id>/adjudicate/', views.adjudication_form, name='adjudication_form'),
    path('violation/<int:violation_id>/submit-adjudication/', views.submit_adjudication, name='submit_adjudication'),

    # Announcement URLs
    path('announcements/', views.announcements_list, name='announcements_list'),
    path('announcements/create/', views.create_announcement, name='create_announcement'),
    path('announcements/edit/<int:announcement_id>/', views.edit_announcement, name='edit_announcement'),
    path('announcements/delete/<int:announcement_id>/', views.delete_announcement, name='delete_announcement'),
    path('announcements/<int:announcement_id>/resend-notification/', views.resend_announcement_notification, name='resend_announcement_notification'),
    path('api/announcements/popup/', views.get_popup_announcement, name='get_popup_announcement'),
    path('api/announcements/<int:announcement_id>/acknowledge/', views.acknowledge_announcement, name='api_acknowledge_announcement'),
    path('announcements/<int:announcement_id>/reset-popup/', views.reset_popup_announcement, name='reset_popup_announcement'),
    path('user/notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('announcements/api/<int:announcement_id>/', views.get_announcement_details, name='get_announcement_details'),

    # Enforcer Tracking URLs
    path('enforcer-map/', views.enforcer_map, name='enforcer_map'),
    path('api/update-location/', views.update_location, name='update_location'),
    path('api/get-enforcer-locations/', views.get_enforcer_locations, name='get_enforcer_locations'),
    path('api/get-enforcer-path/', views.get_enforcer_path, name='get_enforcer_path'),

    # Add these URL patterns in the urlpatterns list
    path('payments/', views.payment_records, name='payment_records'),
    path('violation/<int:violation_id>/print-receipt/', views.print_receipt, name='print_receipt'),

    # Adjudication approval URLs
    path('pending-approvals/', views.pending_approvals, name='pending_approvals'),
    path('violation/<int:violation_id>/approve-adjudication/', views.approve_adjudication, name='approve_adjudication'),
    path('violation/<int:violation_id>/reject-adjudication/', views.reject_adjudication, name='reject_adjudication'),

    # Payment processing URLs
    path('payment-processing/', views.payment_processing, name='payment_processing'),
    path('violation/<int:violation_id>/record-payment/', views.record_payment, name='record_payment'),

    # Authentication URLs
    path('accounts/password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt'
    ), name='password_reset'),
    
    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),

    # Dashboard URL
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('reports/dashboard/', views.admin_reports_dashboard, name='admin_reports_dashboard'),

    # Add this line in the urlpatterns list
    path('user/', include('traffic_violation_system.user_portal.urls', namespace='user_portal')),

    path('scan-document/', views.scan_document, name='scan_document'),
    
    # Signature handling URLs
    path('save-signature/', views.save_signature, name='save_signature'),
    path('get-signature/<str:filename>/', views.get_signature, name='get_signature'),

    # Operator Management
    path('operators/', views.operator_list, name='operator_list'),
    path('operators/<int:pk>/', views.operator_detail, name='operator_detail'),
    path('operators/create/', views.operator_create, name='operator_create'),
    path('operators/<int:pk>/update/', views.operator_update, name='operator_update'),
    path('operators/<int:pk>/delete/', views.operator_delete, name='operator_delete'),
    path('operators/<int:operator_id>/vehicles/', views.operator_vehicles, name='operator_vehicles'),
    path('operators/import/', views.operator_import, name='operator_import'),
    path('operators/import/confirm/', views.operator_import_confirm, name='operator_import_confirm'),
    path('operators/export/excel/', views.operator_export_excel, name='operator_export_excel'),
    
    # Driver Management
    path('drivers/', views.driver_list, name='driver_list'),
    path('drivers/create/', views.driver_create, name='driver_create'),
    path('drivers/<int:pk>/update/', views.driver_update, name='driver_update'),
    path('drivers/<int:pk>/delete/', views.driver_delete, name='driver_delete'),
    path('drivers/import/', views.driver_import, name='driver_import'),
    path('drivers/import/confirm/', views.driver_import_confirm, name='driver_import_confirm'),
    path('drivers/export/excel/', views.driver_export_excel, name='driver_export_excel'),
    
    # Operator Application System
    path('operator/apply/', views.operator_apply, name='operator_apply'),
    path('operator/application/status/', views.operator_application_status, name='operator_application_status'),
    path('operator/dashboard/', views.operator_dashboard, name='operator_dashboard'),
    path('operator/applications/manage/', views.operator_applications_manage, name='operator_applications_manage'),
    path('operator/application/<int:application_id>/review/', views.operator_application_review, name='operator_application_review'),

    # API Endpoints
    path('api/', include('api.urls')),

    # Reports management
    path('admin/reports/update/<int:report_id>/', views.update_report, name='update_report'),
    path('admin/reports/detail/<int:report_id>/', views.get_report_details, name='get_report_details'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)