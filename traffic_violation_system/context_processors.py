from django.db.models import Q
from traffic_violation_system.user_portal.models import UserNotification

def user_notifications(request):
    """Add unread notification count and recent notifications to the context"""
    context = {
        'unread_notification_count': 0,
        'recent_notifications': [],
    }
    
    if request.user.is_authenticated:
        # Count unread notifications
        context['unread_notification_count'] = UserNotification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        # Get recent notifications for the dropdown menu (limit to 5)
        context['recent_notifications'] = UserNotification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]
    
    return context 