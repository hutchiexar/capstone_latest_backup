import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import models
from traffic_violation_system.models import UserProfile, Violation

class Command(BaseCommand):
    help = 'Checks and fixes media paths for existing records'

    def handle(self, *args, **options):
        self.stdout.write('Starting media path validation...')
        
        media_root = settings.MEDIA_ROOT
        self.stdout.write(f'Using MEDIA_ROOT: {media_root}')
        
        # Ensure media directory exists
        if not os.path.exists(media_root):
            os.makedirs(media_root, exist_ok=True)
            self.stdout.write(self.style.SUCCESS(f'Created media directory: {media_root}'))
        
        # Ensure subdirectories exist
        for subdir in ['avatars', 'signatures', 'driver_photos', 'vehicle_photos', 'secondary_photos', 'qr_codes']:
            subdir_path = os.path.join(media_root, subdir)
            if not os.path.exists(subdir_path):
                os.makedirs(subdir_path, exist_ok=True)
                self.stdout.write(self.style.SUCCESS(f'Created subdirectory: {subdir_path}'))
        
        # Check user profile avatars
        self.stdout.write('Checking user profile avatars...')
        profiles_with_avatars = UserProfile.objects.exclude(avatar='').exclude(avatar__isnull=True)
        self.stdout.write(f'Found {profiles_with_avatars.count()} profiles with avatars')
        
        for profile in profiles_with_avatars:
            try:
                if profile.avatar and hasattr(profile.avatar, 'path'):
                    # Check if file exists
                    if not os.path.exists(profile.avatar.path):
                        self.stdout.write(self.style.WARNING(
                            f'Avatar file not found for {profile.user.username}: {profile.avatar.path}'
                        ))
                    else:
                        self.stdout.write(f'Avatar file exists for {profile.user.username}: {profile.avatar.path}')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error checking avatar for {profile.user.username}: {str(e)}'))
        
        # Check violation images
        self.stdout.write('Checking violation images...')
        violations_with_images = Violation.objects.filter(
            models.Q(image__isnull=False) | 
            models.Q(driver_photo__isnull=False) | 
            models.Q(vehicle_photo__isnull=False) | 
            models.Q(secondary_photo__isnull=False) | 
            models.Q(violator_signature__isnull=False)
        ).exclude(image='').exclude(driver_photo='').exclude(vehicle_photo='').exclude(secondary_photo='').exclude(violator_signature='')
        
        self.stdout.write(f'Found {violations_with_images.count()} violations with images')
        
        for violation in violations_with_images:
            for field_name in ['image', 'driver_photo', 'vehicle_photo', 'secondary_photo', 'violator_signature']:
                field = getattr(violation, field_name)
                if field and hasattr(field, 'path'):
                    try:
                        if not os.path.exists(field.path):
                            self.stdout.write(self.style.WARNING(
                                f'Violation image not found for {violation.id} ({field_name}): {field.path}'
                            ))
                        else:
                            self.stdout.write(f'Violation image exists for {violation.id} ({field_name}): {field.path}')
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(
                            f'Error checking {field_name} for violation {violation.id}: {str(e)}'
                        ))
        
        self.stdout.write(self.style.SUCCESS('Media path validation completed')) 