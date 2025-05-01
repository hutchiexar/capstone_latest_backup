import os
import django
from django.db import transaction

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CAPSTONE_PROJECT.settings')
django.setup()

from django.contrib.auth.models import User
from traffic_violation_system.models import UserProfile
from traffic_violation_system.views import generate_enforcer_id  # Import your enforcer ID generator

def create_missing_profiles():
    """Create UserProfile objects for any User that doesn't have one"""
    print("Checking for users without profiles...")
    users_without_profiles = []
    
    # Find all users without a profile
    for user in User.objects.all():
        try:
            # Try to access profile (will raise exception if it doesn't exist)
            profile = user.userprofile
        except User.userprofile.RelatedObjectDoesNotExist:
            users_without_profiles.append(user)
    
    print(f"Found {len(users_without_profiles)} users without profiles.")
    
    # Create profiles for users that need them
    with transaction.atomic():
        for user in users_without_profiles:
            print(f"Creating profile for {user.username}")
            profile = UserProfile.objects.create(
                user=user,
                enforcer_id=generate_enforcer_id(),
                phone_number='',
                address='',
                role='USER',
                is_email_verified=False  # Default to not verified
            )
            profile.save()
            
            # Generate QR code
            try:
                profile.generate_qr_code()
                profile.save()
                print(f"  QR code generated successfully")
            except Exception as e:
                print(f"  Error generating QR code: {str(e)}")
    
    print("Process completed!")

if __name__ == "__main__":
    create_missing_profiles() 