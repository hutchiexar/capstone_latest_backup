from django.urls import path, include
from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Landing Pages
    path('', views.landing_home, name='landing_home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('contact/', views.contact, name='contact'),

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
    path('adjudication/', views.adjudication_list, name='adjudication_list'),
    path('violation/<int:violation_id>/adjudicate/', views.adjudication_form, name='adjudication_form'),
    path('violation/<int:violation_id>/submit-adjudication/', views.submit_adjudication, name='submit_adjudication'),

    # Announcement URLs
    path('announcements/', views.announcements_list, name='announcements_list'),
    path('announcements/create/', views.create_announcement, name='create_announcement'),
    path('announcements/edit/<int:announcement_id>/', views.edit_announcement, name='edit_announcement'),
    path('announcements/delete/<int:announcement_id>/', views.delete_announcement, name='delete_announcement'),

    # Enforcer Tracking URLs
    path('enforcer-map/', views.enforcer_map, name='enforcer_map'),
    path('api/update-location/', views.update_location, name='update_location'),
    path('api/get-enforcer-locations/', views.get_enforcer_locations, name='get_enforcer_locations'),

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

    # Add this line in the urlpatterns list
    path('user/', include('traffic_violation_system.user_portal.urls', namespace='user_portal')),

    path('scan-document/', views.scan_document, name='scan_document'),
]