from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports_dashboard, name='reports_dashboard'),
    path('violation-reports/', views.admin_violation_report, name='admin_violation_report'),
    path('violation-reports/export/', views.admin_violation_export, name='admin_violation_export'),
    path('violation-reports/download/', views.admin_violation_download, name='admin_violation_download'),
    path('financial/', views.financial_report, name='financial_report'),
    path('financial/export/', views.financial_report_export, name='financial_report_export'),
    path('enforcer-activity/', views.enforcer_activity_report, name='enforcer_activity_report'),
    path('enforcer-activity/export/', views.enforcer_activity_export, name='enforcer_activity_export'),
    path('user-statistics/', views.user_statistics_report, name='user_statistics_report'),
    path('user-statistics/export/', views.user_statistics_export, name='user_statistics_export'),
    path('adjudication/', views.adjudication_report, name='adjudication_report'),
    path('adjudication/export/', views.adjudication_export, name='adjudication_export'),
] 