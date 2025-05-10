from django.urls import path, include, re_path
from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from . import views, violation_type_views, activity_views
from .user_portal import views as user_portal_views
from . import operator_views
from traffic_violation_system.operator_views import operator_print_slip, operator_create_with_potpots, operator_enable, operator_print_own_slip
from .submit_violations_for_approval import submit_violations_for_approval
from . import adjudication_views, adjudication_history_views
from .educational import views as educational_views
from . import views_qr_code
from . import views_driver_verify
from .views_email_verification import (
    verify_email,
    verify_code,
    resend_verification,
    verification_pending,
    verification_required,
    verification_success,
    verification_failed,
    verification_expired
)
from .views_qr_ticket.views import prepare_driver_ticket, prepare_user_ticket
from .views_qr_ticket.issue_direct import issue_direct_ticket, violation_qr_code_print_view, direct_ticket_form
from .views_violation_qr import violation_qr_code_image, get_violation_qr_info, register_with_violations, register_with_direct_violation
from .views_registration import register
from . import receipt_views
from . import api_views
from . import updated_dashboard
from educational_analytics import educational_analytics, educational_analytics_by_range
from django.contrib.auth.tokens import default_token_generator
from .views_password_reset import get_email_by_username, BrevoPasswordResetForm

# DEBUG VIEW for troubleshooting - this will be removed later
@csrf_exempt
def debug_password_reset_route(request):
    """Simple debug view to test password reset routing"""
    return HttpResponse("""
        <html>
            <head><title>Password Reset Route Debug</title></head>
            <body>
                <h1>Password Reset Route is Working!</h1>
                <p>If you can see this page, the routing to password reset is functional.</p>
                <p>Go to the <a href="/accounts/password_reset/">actual password reset page</a>.</p>
                <hr>
                <h3>Debug Info:</h3>
                <pre>
                Path: {0}
                User: {1}
                Authenticated: {2}
                </pre>
            </body>
        </html>
    """.format(
        request.path,
        request.user.username if request.user.is_authenticated else "Anonymous",
        request.user.is_authenticated
    ))

urlpatterns = [
    # Landing Pages
    path('', views.landing_home, name='landing_home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('contact/', views.contact, name='contact'),
    path('track/', views.track_violation, name='track_violation'),
    
    # User Authentication
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/register/', register, name='register'),
    path('accounts/profile/', views.profile, name='profile'),
    path('accounts/profile/edit/', views.edit_profile, name='edit_profile'),
    path('accounts/get-email-by-username/', get_email_by_username, name='get_email_by_username'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    
    # User Management
    path('users/', views.users_list, name='users_list'),
    path('users/create/', views.create_user, name='create_user'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<int:user_id>/modal/', views.user_detail_modal, name='user_detail_modal'),
    path('user/notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    
    # Activity History
    path('activity-history/', activity_views.activity_history, name='activity_history'),
    
    # Operator Management
    path('operators/', views.operator_list, name='operator_list'),
    path('operators/<int:pk>/', views.operator_detail, name='operator_detail'),
    path('operators/create/', operator_views.operator_create_with_potpots, name='operator_create'),
    path('operators/update/<int:pk>/', operator_views.operator_update_with_vehicles, name='operator_update'),
    path('operators/<int:pk>/delete/', views.operator_delete, name='operator_delete'),
    path('operators/<int:pk>/enable/', operator_views.operator_enable, name='operator_enable'),
    path('operators/<int:operator_id>/vehicles/', views.operator_vehicles, name='operator_vehicles'),
    path('operators/import/', views.operator_import, name='operator_import'),
    path('operators/import/confirm/', views.operator_import_confirm, name='operator_import_confirm'),
    path('operators/export/excel/', views.operator_export_excel, name='operator_export_excel'),
    path('operators/template/excel/', views.operator_template_excel, name='operator_template_excel'),
    path('operators/<int:pk>/print/', operator_print_slip, name='operator_print_slip'),
    path('operator/print-slip/', operator_print_own_slip, name='operator_print_own_slip'),
    
    # Operator Application System
    path('operator/apply/', views.operator_apply, name='operator_apply'),
    path('operator/application/status/', views.operator_application_status, name='operator_application_status'),
    path('operator/applications/manage/', views.operator_applications_manage, name='operator_applications_manage'),
    path('operator/application/<int:application_id>/review/', views.operator_application_review, name='operator_application_review'),
    
    # Admin Driver Management
    path('management/drivers/', views.admin_driver_list, name='admin_driver_list'),
    path('management/drivers/export/', views.driver_export_excel, name='driver_export_excel'), 
    path('management/drivers/template/', views.driver_template_excel, name='driver_template_excel'),
    path('management/drivers/create/', views.driver_create, name='driver_create'),
    path('management/drivers/<int:pk>/update/', views.driver_update, name='driver_update'),
    path('management/drivers/<int:pk>/delete/', views.driver_disable, name='driver_delete'),
    path('management/drivers/<int:pk>/enable/', views.driver_enable, name='driver_enable'),
    path('management/drivers/<int:pk>/', views.driver_detail, name='driver_detail'),
    path('management/drivers/import/', views.driver_import, name='driver_import'),
    
    # Password Reset URLs
    path('accounts/password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done'),
        token_generator=default_token_generator,
        from_email=settings.DEFAULT_FROM_EMAIL,
        html_email_template_name='registration/password_reset_email.html',
        form_class=BrevoPasswordResetForm,
        extra_context={'title': 'Password Reset'}
    ), name='password_reset'),
    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete'),
        token_generator=default_token_generator,
        post_reset_login=False,
        reset_url_token='set-password',
    ), name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Email verification URLs
    path('verification/verify/<uuid:token>/', verify_email, name='verify_email'),
    path('verification/verify-code/', verify_code, name='verify_code'),
    path('verification/pending/', verification_pending, name='verification_pending'),
    path('verification/required/', verification_required, name='verification_required'),
    path('verification/success/', verification_success, name='verification_success'),
    path('verification/failed/', verification_failed, name='verification_failed'),
    path('verification/expired/', verification_expired, name='verification_expired'),
    path('verification/resend/', resend_verification, name='resend_verification'),
    
    # Announcements
    path('announcements/', views.announcements_list, name='announcements_list'),
    path('announcements/create/', views.create_announcement, name='create_announcement'),
    path('announcements/edit/<int:announcement_id>/', views.edit_announcement, name='edit_announcement'),
    path('announcements/delete/<int:announcement_id>/', views.delete_announcement, name='delete_announcement'),
    path('announcements/<int:announcement_id>/resend-notification/', views.resend_announcement_notification, name='resend_announcement_notification'),
    path('announcements/<int:announcement_id>/reset-popup/', views.reset_popup_announcement, name='reset_popup_announcement'),
    path('announcements/api/<int:announcement_id>/', views.get_announcement_details, name='get_announcement_details'),
    
    # Dashboard URLs
    path('admin-dashboard/', updated_dashboard.admin_dashboard, name='admin_dashboard'),
    path('operator/dashboard/', views.operator_dashboard, name='operator_dashboard'),
    path('adjudication/dashboard/', views.adjudication_dashboard, name='adjudication_dashboard'),
    
    # Enforcer Tracking URLs
    path('enforcer-map/', views.enforcer_map, name='enforcer_map'),
    path('qr/<str:enforcer_id>/', views_qr_code.qr_profile_view, name='qr_profile_view'),
    path('qr/user/<str:enforcer_id>/', views_qr_code.qr_user_data, name='qr_user_data'),
    path('qr/user/<str:enforcer_id>/ticket/', prepare_user_ticket, name='prepare_user_ticket'),
    path('qr-scanner/', views_qr_code.qr_scanner, name='qr_scanner'),
    
    # Approvals
    path('pending-approvals/', views.pending_approvals, name='pending_approvals'),
    
    # Payment Processing
    path('payment-processing/', views.payment_processing, name='payment_processing'),
    path('payments/', views.payment_records, name='payment_records'),
    path('payments/export-excel/', views.export_payment_records_excel, name='export_payment_records_excel'),
    path('payments/export-pdf/', views.export_payment_records_pdf, name='export_payment_records_pdf'),
    path('webhook/payment/', views.payment_webhook, name='payment_webhook'),
    
    # Adjudication URLs
    path('adjudication/', views.adjudication_list, name='adjudication_list'),
    path('adjudication/list/', views.adjudication_list, name='adjudication_list'),
    path('adjudication/rejected/', views.rejected_adjudications, name='rejected_adjudications'),
    path('adjudication/violator/<int:violator_id>/', adjudication_views.adjudication_page, name='adjudication_page'),
    path('adjudication/ticket/adjudicate/', adjudication_views.adjudicate_ticket, name='adjudicate_ticket'),
    path('adjudication/violator/<int:violator_id>/submit/', adjudication_views.submit_all_adjudications, name='submit_all_adjudications'),
    path('adjudication/violation/<int:violation_id>/data/', adjudication_views.get_violation_data, name='get_violation_data'),
    
    # Reports URLs
    path('management/reports/', views.admin_report_list, name='admin_report_list'),
    path('management/reports/<int:report_id>/dispute/', views.admin_report_dispute, name='admin_report_dispute'),
    path('management/reports/<int:report_id>/update-status/', views.admin_report_update_status, name='admin_report_update_status'),
    path('management/reports/<int:report_id>/view/', views.admin_report_view, name='admin_report_view'),
    path('management/reports/export/', views.admin_report_export, name='admin_report_export'),
    path('management/reports/<int:report_id>/', views.admin_report_view, name='admin_report_detail'),
    path('management/reports/<int:report_id>/update/', views.admin_report_update_status, name='admin_report_update'),
    
    # Driver verification
    path('driver/<str:driver_id>/verify/', views_driver_verify.driver_verify, name='driver_verify'),
    path('drivers/search/', views_driver_verify.search_drivers, name='search_drivers'),
    path('driver/<str:driver_id>/ticket/', prepare_driver_ticket, name='prepare_driver_ticket'),
    
    # Violation Management
    path('upload-violation/', views.upload_violation, name='upload_violation'),
    path('issue-ticket/', views.issue_ticket, name='issue_ticket'),
    path('violations/', views.violations_list, name='violations_list'),
    path('violations/<int:violation_id>/update-status/', views.update_violation_status, name='update_violation_status'),
    path('violations/search-violators/', views.search_violators, name='search_violators'),
    path('ncap-violations/', views.ncap_violations_list, name='ncap_violations_list'),
    path('ncap-violations/create/', views.create_ncap_violation, name='create_ncap_violation'),
    path('ncap-violations/save/', views.save_ncap_violation, name='save_ncap_violation'),
    path('submit_violations_for_approval/', submit_violations_for_approval, name='submit_violations_for_approval'),
    path('violation/<int:violation_id>/', views.violation_detail, name='violation_detail'),
    path('violation/<int:violation_id>/modal/', views.violation_detail_modal, name='violation_detail_modal'),
    path('violation/<int:violation_id>/payment-info/', views.violation_payment_info, name='violation_payment_info'),
    path('violation/<int:violation_id>/process-payment/', views.process_payment, name='process_payment'),
    path('violation/<int:violation_id>/record-payment/', views.record_payment, name='record_payment'),
    path('violation/<int:violation_id>/print/', views.print_violation_form, name='print_violation_form'),
    path('violation/<int:violation_id>/print-receipt/', views.print_receipt, name='print_receipt'),
    path('violation/<int:violation_id>/payment-detail-modal/', views.payment_detail_modal, name='payment_detail_modal'),
    path('violation/<int:violation_id>/submit-adjudication/', views.submit_adjudication, name='submit_adjudication'),
    path('violation/<int:violation_id>/approve-adjudication/', views.approve_adjudication, name='approve_adjudication'),
    path('violation/<int:violation_id>/reject-adjudication/', views.reject_adjudication, name='reject_adjudication'),
    path('violation/<int:violation_id>/adjudicator-notes/', views.get_adjudicator_notes, name='get_adjudicator_notes'),
    path('violation/<int:violation_id>/receipt-summary/', receipt_views.receipt_summary_view, name='receipt_summary'),
    path('violation/batch-receipt-summary/<str:violation_ids>/', receipt_views.batch_receipt_summary_view, name='batch_receipt_summary'),
    path('violation/<int:violation_id>/adjudication-details/', adjudication_views.get_adjudication_details, name='get_adjudication_details'),
    path('violation/<int:violation_id>/redirect-to-adjudication/', adjudication_views.redirect_to_adjudication_page, name='redirect_to_adjudication_page'),
    
    # QR Code routes
    path('violation/<int:violation_id>/qr-print/', violation_qr_code_print_view, name='violation_qr_code_print_view'),
    path('violation/<int:violation_id>/qr-image/', violation_qr_code_image, name='violation_qr_code_image'),
    path('violation/qr-info/<str:hash_id>/', get_violation_qr_info, name='get_violation_qr_info'),
    path('register/violations/<str:hash_id>/', register_with_violations, name='register_with_violations'),
    path('register/violations/direct/<int:violation_id>/', register_with_direct_violation, name='register_with_direct_violation'),
    
    # Direct ticket issue with session data
    path('violations/issue-direct-ticket/', direct_ticket_form, name='issue_direct_ticket'),
    path('violations/issue-direct-ticket/<int:violation_id>/', issue_direct_ticket, name='issue_direct_ticket_with_id'),
    
    # API Routes
    path('api/statistics/<str:time_range>/', views.get_statistics, name='get_statistics'),
    path('api/announcements/popup/', views.get_popup_announcement, name='get_popup_announcement'),
    path('api/announcements/<int:announcement_id>/acknowledge/', views.acknowledge_announcement, name='api_acknowledge_announcement'),
    path('api/announcements/<int:announcement_id>/mark-seen/', views.mark_announcement_seen, name='mark_announcement_seen'),
    path('announcements/api/<int:announcement_id>/', views.get_announcement_details, name='get_announcement_details'),
    path('api/update-location/', views.update_location, name='update_location'),
    path('api/get-enforcer-locations/', views.get_enforcer_locations, name='get_enforcer_locations'),
    path('api/get-enforcer-path/', views.get_enforcer_path, name='get_enforcer_path'),
    path('api/', include('api.urls')),
    path('api/search-operators/', views.api_search_operators, name='api_search_operators'),
    path('api/search-drivers/', views.api_search_drivers, name='api_search_drivers'),
    path('api/get-operator/', views.api_get_operator, name='api_get_operator'),
    path('api/get-driver/', views.api_get_driver, name='api_get_driver'),
    path('api/adjudication-statistics/<str:timeframe>/', api_views.adjudication_statistics_api, name='adjudication_statistics_api'),
    path('api/educational-analytics/', educational_analytics, name='educational_analytics'),
    path('api/educational-analytics/<str:time_range>/', educational_analytics_by_range, name='educational_analytics_by_range'),
    
    # Other app includes
    path('driver/', views.driver_list, name='driver_list'),
    path('user/', include('traffic_violation_system.user_portal.urls', namespace='user_portal')),
    path('educational/', include('traffic_violation_system.educational.urls', namespace='educational')),
    path('', include('traffic_violation_system.adjudication_history_urls')),
    
    # Violation Types Management
    path('management/violation-types/', violation_type_views.violation_types, name='violation_types'),
    path('management/violation-types/add/', violation_type_views.add_violation_type, name='add_violation_type'),
    path('management/violation-types/edit/<int:type_id>/', violation_type_views.edit_violation_type, name='edit_violation_type'),
    path('management/violation-types/delete/<int:type_id>/', violation_type_views.delete_violation_type, name='delete_violation_type'),
    path('management/violation-types/export/', violation_type_views.export_violation_types, name='export_violation_types'),
    
    # Signature management
    path('get-signature/<str:filename>/', views.get_signature, name='get_signature'),
    path('save-signature/', views.save_signature, name='save_signature'),
    
    # Debug URL for password reset troubleshooting
    path('debug-password-reset/', debug_password_reset_route, name='debug_password_reset'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 