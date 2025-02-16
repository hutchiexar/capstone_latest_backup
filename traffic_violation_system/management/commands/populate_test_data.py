from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from traffic_violation_system.models import UserProfile, Violation, Violator, Announcement
from datetime import timedelta
import random
import string

class Command(BaseCommand):
    help = 'Populates the database with test data'

    def generate_phone(self):
        return f"09{''.join(random.choices(string.digits, k=9))}"

    def generate_plate_number(self):
        letters = ''.join(random.choices(string.ascii_uppercase, k=3))
        numbers = ''.join(random.choices(string.digits, k=3))
        return f"{letters} {numbers}"

    def generate_license_number(self):
        letters = ''.join(random.choices(string.ascii_uppercase, k=1))
        numbers = ''.join(random.choices(string.digits, k=2))
        more_letters = ''.join(random.choices(string.ascii_uppercase, k=5))
        more_numbers = ''.join(random.choices(string.digits, k=5))
        return f"{letters}{numbers}-{more_letters}{more_numbers}"

    def handle(self, *args, **kwargs):
        # Create admin user
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123',
            first_name='Admin',
            last_name='User'
        )
        admin_profile = admin_user.userprofile
        admin_profile.role = 'ADMIN'
        admin_profile.phone_number = self.generate_phone()
        admin_profile.address = '123 Admin Street, Davao City'
        admin_profile.latitude = 7.190708
        admin_profile.longitude = 125.455341
        admin_profile.last_location_update = timezone.now()
        admin_profile.is_active_duty = True
        admin_profile.save()

        # Create supervisor user
        supervisor_user = User.objects.create_user(
            username='supervisor',
            email='supervisor@example.com',
            password='supervisor123',
            first_name='Super',
            last_name='Visor'
        )
        supervisor_profile = supervisor_user.userprofile
        supervisor_profile.role = 'SUPERVISOR'
        supervisor_profile.phone_number = self.generate_phone()
        supervisor_profile.address = '456 Supervisor Ave, Davao City'
        supervisor_profile.latitude = 7.191708
        supervisor_profile.longitude = 125.456341
        supervisor_profile.last_location_update = timezone.now()
        supervisor_profile.is_active_duty = True
        supervisor_profile.save()

        # Create enforcer users
        enforcer_locations = [
            (7.192708, 125.457341),
            (7.193708, 125.458341),
            (7.194708, 125.459341),
            (7.195708, 125.460341),
            (7.196708, 125.461341),
            (7.197708, 125.462341),  # Additional enforcer locations
            (7.198708, 125.463341),
            (7.199708, 125.464341)
        ]

        for i, location in enumerate(enforcer_locations, 1):
            enforcer_user = User.objects.create_user(
                username=f'enforcer{i}',
                email=f'enforcer{i}@example.com',
                password=f'enforcer{i}123',
                first_name=f'Enforcer',
                last_name=f'Number {i}'
            )
            enforcer_profile = enforcer_user.userprofile
            enforcer_profile.role = 'ENFORCER'
            enforcer_profile.phone_number = self.generate_phone()
            enforcer_profile.address = f'{i}00 Enforcer Street, Davao City'
            enforcer_profile.latitude = location[0]
            enforcer_profile.longitude = location[1]
            enforcer_profile.last_location_update = timezone.now()
            enforcer_profile.is_active_duty = True
            enforcer_profile.save()

        # Create violators and violations
        violation_types = [choice[0] for choice in Violation.VIOLATION_CHOICES]
        vehicle_types = [
            'Toyota Vios', 'Honda Civic', 'Mitsubishi Mirage', 'Suzuki Celerio', 'Hyundai Accent',
            'Toyota Fortuner', 'Mitsubishi Montero', 'Ford Ranger', 'Isuzu D-Max', 'Nissan Navara',
            'Toyota Innova', 'Honda City', 'Suzuki Ertiga', 'Mitsubishi Xpander', 'Hyundai Starex'
        ]
        colors = ['Red', 'Blue', 'White', 'Black', 'Silver', 'Gray', 'Green', 'Yellow', 'Brown', 'Orange']
        locations = [
            'Roxas Avenue',
            'San Pedro Street',
            'JP Laurel Avenue',
            'CM Recto Street',
            'Quirino Avenue',
            'Magallanes Street',  # Additional locations
            'Pichon Street',
            'Ilustre Street',
            'Bonifacio Street',
            'Anda Street',
            'Jacinto Street',
            'Bolton Street',
            'Pelayo Street',
            'Rizal Street',
            'Legaspi Street'
        ]

        # Create more violators and violations
        for i in range(50):  # Increased from 20 to 50 violators
            first_names = ['Juan', 'Maria', 'Pedro', 'Ana', 'Jose', 'Rosa', 'Carlos', 'Sofia', 'Miguel', 'Isabel']
            last_names = ['Santos', 'Cruz', 'Reyes', 'Garcia', 'Torres', 'Lopez', 'Ramos', 'Flores', 'Gonzales', 'Mendoza']
            
            violator = Violator.objects.create(
                first_name=random.choice(first_names),
                last_name=random.choice(last_names),
                license_number=self.generate_license_number(),
                phone_number=self.generate_phone(),
                address=f'{i}00 {random.choice(locations)}, Davao City'
            )

            # Create 2-5 violations for each violator
            for _ in range(random.randint(2, 5)):
                violation_date = timezone.now() - timedelta(days=random.randint(0, 60))  # Increased date range
                fine_amount = random.choice([500, 750, 1000, 1500, 2000, 2500, 3000])  # More varied fine amounts
                
                # Weight the status distribution
                status_weights = [
                    ('PENDING', 0.4),
                    ('PAID', 0.3),
                    ('SETTLED', 0.2),
                    ('OVERDUE', 0.1)
                ]
                status = random.choices(
                    [s[0] for s in status_weights],
                    weights=[s[1] for s in status_weights]
                )[0]

                violation = Violation.objects.create(
                    violator=violator,
                    violation_date=violation_date,
                    location=random.choice(locations),
                    violation_type=random.choice(violation_types),
                    fine_amount=fine_amount,
                    status=status,
                    description=f'Violation occurred at {random.choice(locations)}. Driver was caught {random.choice(["speeding", "running a red light", "illegal parking", "no license", "expired registration"])}.',
                    payment_due_date=violation_date + timedelta(days=7),
                    enforcer=random.choice(User.objects.filter(userprofile__role='ENFORCER')),
                    enforcer_signature_date=violation_date,
                    vehicle_type=random.choice(vehicle_types),
                    classification=random.choice(['Private', 'Public', 'Government', 'Commercial']),
                    plate_number=self.generate_plate_number(),
                    color=random.choice(colors),
                    registration_number=f"REG-{''.join(random.choices(string.digits, k=6))}",
                    registration_date=violation_date - timedelta(days=random.randint(30, 365)),
                    vehicle_owner=f"{random.choice(first_names)} {random.choice(last_names)}",
                    vehicle_owner_address=f"{random.randint(100, 999)} {random.choice(locations)}, Davao City"
                )

                # Add receipt details for paid violations
                if status == 'PAID':
                    violation.receipt_number = f"REC-{''.join(random.choices(string.digits, k=6))}"
                    violation.receipt_date = violation_date + timedelta(days=random.randint(1, 5))
                    violation.save()

        # Create announcements with more varied content
        priorities = ['LOW', 'MEDIUM', 'HIGH']
        announcement_titles = [
            'Traffic Advisory: Road Closure',
            'New Traffic Violation Penalties',
            'System Maintenance Schedule',
            'Holiday Traffic Guidelines',
            'Important: New Traffic Rules',
            'Traffic Enforcer Training Schedule',
            'Public Advisory: Special Events',
            'System Update Notice',
            'Emergency Traffic Advisory',
            'Payment System Upgrade Notice'
        ]
        
        for i in range(10):  # Increased from 5 to 10 announcements
            created_date = timezone.now() - timedelta(days=random.randint(0, 30))
            Announcement.objects.create(
                title=announcement_titles[i],
                content=f'This is an important announcement regarding {announcement_titles[i].lower()}. Please read carefully and follow the guidelines provided.',
                created_by=random.choice([admin_user, supervisor_user]),
                priority=random.choice(priorities),
                is_active=random.choice([True, True, True, False]),  # 75% chance of being active
                created_at=created_date,
                updated_at=created_date + timedelta(days=random.randint(0, 5))
            )

        self.stdout.write(self.style.SUCCESS('Successfully populated test data')) 