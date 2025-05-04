from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Dashboard and report listing
    path('', views.reports_dashboard, name='dashboard'),
    
    # Report generation
    path('generate/<int:report_id>/', views.report_generator, name='generator'),
    path('view/<int:report_id>/', views.view_report, name='view_report'),
    
    # Report scheduling
    path('schedule/<int:report_id>/', views.schedule_report, name='schedule'),
    path('cancel-schedule/<int:schedule_id>/', views.cancel_schedule, name='cancel_schedule'),
] 