import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Creates a superuser from environment variables if no superusers exist'

    def handle(self, *args, **options):
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.SUCCESS('Superuser already exists'))
            return

        admin_username = os.getenv('DJANGO_ADMIN_USERNAME', 'admin')
        admin_email = os.getenv('DJANGO_ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.getenv('DJANGO_ADMIN_PASSWORD')

        if not admin_password:
            self.stdout.write(self.style.ERROR('Admin password not set in environment variables (DJANGO_ADMIN_PASSWORD)'))
            return

        User.objects.create_superuser(
            username=admin_username,
            email=admin_email,
            password=admin_password
        )

        self.stdout.write(self.style.SUCCESS(f'Superuser {admin_username} created successfully')) 