from .models import ActivityLog

def log_activity(user, action, details='', category='general'):
    """
    Enhanced utility function to log user activities with categories
    """
    ActivityLog.objects.create(
        user=user,
        action=action,
        details=details,
        category=category
    ) 