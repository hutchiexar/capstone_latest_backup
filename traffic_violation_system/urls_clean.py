from django.urls import path, include, re_path
from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from . import views, violation_type_views, activity_views
from .user_portal import views as user_portal_views
from . import operator_views
from traffic_violation_system.operator_views import operator_print_slip, operator_create_with_potpots, operator_enable, operator_print_own_slip
from .submit_violations_for_approval import submit_violations_for_approval
from . import adjudication_views, adjudication_history_views
from .educational import views as educational_views
from . import views_qr_code
from . import views_driver_verify
from .views_qr_ticket.views import prepare_driver_ticket, prepare_user_ticket
from .views_qr_ticket.issue_direct import issue_direct_ticket, violation_qr_code_print_view, direct_ticket_form
from .views_registration import register
from . import receipt_views
from . import api_views
from . import updated_dashboard
from educational_analytics import educational_analytics, educational_analytics_by_range

urlpatterns = [
    # Existing patterns kept for reference
    path('', views.landing_home, name='landing_home'),
    
    # QR Code print view - this is the one we need to add
    path('violation/<int:violation_id>/qr-print/', violation_qr_code_print_view, name='violation_qr_code_print_view'),
    
    # Direct ticket issue with session data
    path('violations/issue-direct-ticket/', direct_ticket_form, name='issue_direct_ticket'),
    path('violations/issue-direct-ticket/<int:violation_id>/', issue_direct_ticket, name='issue_direct_ticket_with_id'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 