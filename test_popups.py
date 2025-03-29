import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CAPSTONE_PROJECT.settings')
django.setup()

# Import models after Django setup
from django.utils import timezone
from django.db.models import Q
from traffic_violation_system.models import Announcement

# Get current time
current_time = timezone.now()

print("Checking for active popup announcements...")
print(f"Current time: {current_time}")

# Get all active popup announcements
active_popups = Announcement.objects.filter(
    is_active=True, 
    is_popup=True
).filter(
    # Check for publish and expiration dates
    Q(publish_date__isnull=True) | Q(publish_date__lte=current_time)
).filter(
    Q(expiration_date__isnull=True) | Q(expiration_date__gt=current_time)
).order_by('-created_at')

print(f"Found {active_popups.count()} active popup announcements:")

for popup in active_popups:
    print(f"- {popup.id}: {popup.title} (Created: {popup.created_at})")
    print(f"  Active: {popup.is_active}, Popup: {popup.is_popup}")
    print(f"  Publish date: {popup.publish_date}, Expiration date: {popup.expiration_date}")
    print(f"  Target audience: {popup.target_audience}")
    print("")

# Check all announcements with is_popup=True
all_popups = Announcement.objects.filter(is_popup=True)
print(f"\nAll announcements with is_popup=True: {all_popups.count()}")
for popup in all_popups:
    print(f"- {popup.id}: {popup.title} (Active: {popup.is_active})")
    print(f"  Publish date: {popup.publish_date}, Expiration date: {popup.expiration_date}")
    print("")

print("Debug complete.") 