import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CAPSTONE_PROJECT.settings')
django.setup()

from django.contrib.sessions.models import Session
from traffic_violation_system.models import Announcement

# Clear all sessions
deleted_count = Session.objects.all().delete()
print(f"All sessions cleared: {deleted_count}")

# Reset all popup announcements
popup_announcements = Announcement.objects.filter(is_popup=True)
for announcement in popup_announcements:
    announcement.save()  # This updates the updated_at field
    print(f"Reset announcement: {announcement.id} - {announcement.title}")

print("Session and announcement reset complete.") 