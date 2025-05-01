# Utils package for traffic_violation_system 

from ..models import ActivityLog

def log_activity(user, action, details='', category='general', ip_address=None):
    """
    Enhanced utility function to log user activities with categories and IP address
    """
    ActivityLog.objects.create(
        user=user,
        action=action,
        details=details,
        category=category,
        ip_address=ip_address
    ) 