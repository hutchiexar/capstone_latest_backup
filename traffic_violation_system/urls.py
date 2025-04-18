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
    path('violation/<int:violation_id>/payment-info/', views.violation_payment_info, name='violation_payment_info'),
    path('violation/<int:violation_id>/process-payment/', views.process_payment, name='process_payment'),
    path('violation/<int:violation_id>/record-payment/', views.record_payment, name='record_payment'),
    path('violation/<int:violation_id>/print/', views.print_violation_form, name='print_violation_form'),
    
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
    path('violations/search-violators/', views.search_violators, name='search_violators'),
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
    path('api/announcements/<int:announcement_id>/mark-seen/', views.mark_announcement_seen, name='mark_announcement_seen'),
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
    path('payments/export-excel/', views.export_payment_records_excel, name='export_payment_records_excel'),
    path('payments/export-pdf/', views.export_payment_records_pdf, name='export_payment_records_pdf'),
    path('violation/<int:violation_id>/print-receipt/', views.print_receipt, name='print_receipt'),
    path('violation/<int:violation_id>/payment-detail-modal/', views.payment_detail_modal, name='payment_detail_modal'),

    # Adjudication approval URLs
    path('pending-approvals/', views.pending_approvals, name='pending_approvals'),
    path('violation/<int:violation_id>/approve-adjudication/', views.approve_adjudication, name='approve_adjudication'),
    path('violation/<int:violation_id>/reject-adjudication/', views.reject_adjudication, name='reject_adjudication'),
    path('violation/<int:violation_id>/adjudicator-notes/', views.get_adjudicator_notes, name='get_adjudicator_notes'),

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
    
    # Add this line in the urlpatterns list
    path('user/', include('traffic_violation_system.user_portal.urls', namespace='user_portal')),

    # Educational materials app
    path('educational/', include('traffic_violation_system.educational.urls', namespace='educational')),

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
    path('operators/template/excel/', views.operator_template_excel, name='operator_template_excel'),
    
    # Operator Application System
    path('operator/apply/', views.operator_apply, name='operator_apply'),
    path('operator/application/status/', views.operator_application_status, name='operator_application_status'),
    path('operator/dashboard/', views.operator_dashboard, name='operator_dashboard'),
    path('operator/applications/manage/', views.operator_applications_manage, name='operator_applications_manage'),
    path('operator/application/<int:application_id>/review/', views.operator_application_review, name='operator_application_review'),

    # API Endpoints
    path('api/', include('api.urls')),

    # Add API endpoints for searching operators and drivers
    path('api/search-operators/', views.api_search_operators, name='api_search_operators'),
    path('api/search-drivers/', views.api_search_drivers, name='api_search_drivers'),
    path('api/get-operator/', views.api_get_operator, name='api_get_operator'),
    path('api/get-driver/', views.api_get_driver, name='api_get_driver'),

    # Vehicle and Driver Routes - fix to use operator_ prefix and appropriate view names
    path('operator/vehicles/register/', views.operator_register_vehicle, name='operator_register_vehicle'),
    path('operator/vehicles/<int:vehicle_id>/edit/', views.operator_edit_vehicle, name='edit_vehicle'),
    path('operator/vehicles/<int:vehicle_id>/delete/', views.operator_delete_vehicle, name='delete_vehicle'),
    path('operator/check-potpot-number/', views.check_potpot_number_unique, name='check_potpot_number_unique'),

    path('operator/drivers/register/', views.operator_register_driver, name='register_driver'),
    path('operator/drivers/<int:driver_id>/edit/', views.operator_edit_driver, name='edit_driver'),
    path('operator/drivers/<int:driver_id>/delete/', views.operator_delete_driver, name='delete_driver'),

    path('operator/assignments/', views.operator_assignment_list, name='assignment_list'),
    path('operator/assignments/create/', views.operator_assign_driver_to_vehicle, name='assign_driver_to_vehicle'),
    path('operator/assignments/<int:assignment_id>/end/', views.operator_end_driver_assignment, name='end_driver_assignment'),

    # Admin driver management routes
    path('management/drivers/', views.admin_driver_list, name='admin_driver_list'),
    path('management/drivers/export/', views.driver_export_excel, name='driver_export_excel'),
    path('management/drivers/template/', views.driver_template_excel, name='driver_template_excel'),
    path('management/drivers/create/', views.driver_create, name='driver_create'),
    path('management/drivers/<int:pk>/update/', views.driver_update, name='driver_update'),
    path('management/drivers/<int:pk>/delete/', views.driver_delete, name='driver_delete'),
    path('management/drivers/<int:pk>/', views.driver_detail, name='driver_detail'),
    path('management/drivers/import/', views.driver_import, name='driver_import'),

    # Admin report management routes
    path('management/reports/', views.admin_report_list, name='admin_report_list'),
    path('management/reports/<int:report_id>/dispute/', views.admin_report_dispute, name='admin_report_dispute'),
    path('management/reports/<int:report_id>/update-status/', views.admin_report_update_status, name='admin_report_update_status'),
    path('management/reports/<int:report_id>/view/', views.admin_report_view, name='admin_report_view'),
    path('management/reports/export/', views.admin_report_export, name='admin_report_export'),

    # General driver route that redirects based on user role
    path('driver/', views.driver_list, name='driver_list'),

    # Add this near the end of the file, before adding static/media URLs
    path('debug/media/', views.debug_media, name='debug_media'),

    # Adjudication dashboard
    path('adjudication/dashboard/', views.adjudication_dashboard, name='adjudication_dashboard'),
    path('adjudication/rejected/', views.rejected_adjudications, name='rejected_adjudications'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)