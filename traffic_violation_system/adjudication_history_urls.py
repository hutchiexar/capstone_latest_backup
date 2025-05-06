from django.urls import path
from . import adjudication_history_views

# URL patterns for adjudication history
urlpatterns = [
    path('adjudication-history/', adjudication_history_views.adjudication_history, name='adjudication_history'),
    path('adjudication-history/<int:violation_id>/', adjudication_history_views.adjudication_detail, name='adjudication_detail'),
    path('adjudication-history/export/', adjudication_history_views.export_adjudication_history, name='export_adjudication_history'),
] 