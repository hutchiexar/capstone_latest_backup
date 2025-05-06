# Fix for urls.py - Replace the last part of the file with this code:

    # Educational analytics API endpoints
    path('api/educational-analytics/', educational_analytics, name='educational_analytics'),
    path('api/educational-analytics/<str:time_range>/', educational_analytics_by_range, name='educational_analytics_by_range'),
    
    # Adjudication details API endpoint
    path('violation/<int:violation_id>/adjudication-details/', adjudication_views.get_adjudication_details, name='get_adjudication_details'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 