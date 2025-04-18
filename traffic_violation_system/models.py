from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image
from django.db.models.signals import post_save
from django.dispatch import receiver
import json
import os
import uuid
from django.core.exceptions import ValidationError



class Violator(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    license_number = models.CharField(max_length=20, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.license_number or 'No License'}"
        
    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        return f"{self.first_name} {self.last_name}"

    class Meta:
        indexes = [
            models.Index(fields=['first_name', 'last_name']),
            models.Index(fields=['license_number']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['license_number'],
                name='unique_non_empty_license',
                condition=models.Q(license_number__isnull=False) & ~models.Q(license_number='')
            )
        ]


def get_ncap_image_path(instance, filename):
    """
    Custom function to generate a clean filename for NCAP violation images.
    Uses UUID to ensure uniqueness and removes special characters.
    """
    # Get the file extension
    ext = filename.split('.')[-1]
    # Generate a new filename with UUID for uniqueness
    new_filename = f"ncap_{uuid.uuid4().hex[:10]}.{ext}"
    # Return the upload path
    return os.path.join('violations', new_filename)


class Operator(models.Model):
    """Model to store operator information"""
    last_name = models.CharField(max_length=100, db_index=True)
    first_name = models.CharField(max_length=100, db_index=True)
    middle_initial = models.CharField(max_length=10, blank=True, null=True)
    address = models.TextField()
    old_pd_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="Old P.O. Number")
    new_pd_number = models.CharField(max_length=50, unique=True, verbose_name="New P.O. Number")
    po_number = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="Permit Operator Number")
    # Foreign key to operator type (will be added later as requested)
    # operator_type = models.ForeignKey(OperatorType, on_delete=models.PROTECT, related_name='operators')
    # Foreign key to user account (will be added later as requested)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='operator_profile')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Operator'
        verbose_name_plural = 'Operators'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['new_pd_number']),
        ]

    def __str__(self):
        return f"{self.last_name}, {self.first_name} {self.middle_initial or ''} - {self.new_pd_number}"

    def full_name(self):
        mi = f" {self.middle_initial}." if self.middle_initial else ""
        return f"{self.first_name}{mi} {self.last_name}"


class Violation(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ADJUDICATED', 'Adjudicated'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('PAID', 'Paid'),
        ('SETTLED', 'Settled'),
        ('OVERDUE', 'Overdue'),
    ]

    VIOLATION_CHOICES = [
        ('Illegal Parking', 'Illegal Parking (DTS)'),
        ('Entering Prohibited Zones', 'Entering Prohibited Zones'),
        ('Obstruction', 'Obstruction'),
        ('Unlicensed Driver', 'Unlicensed Driver'),
        ('Permitting Hitching', 'Permitting Hitching/Over Loading Passenger(s)'),
        ('Unregistered MV', 'Unregistered MV'),
        ('Refusal to Convey', 'Refusal to convey to proper destination'),
        ('Discourteous Driver', 'Discourteous driver/Conduct'),
        ('Defective Lights', 'No/Defective Lights'),
        ('Expired OR/CR', 'Expired OR/CR'),
        ('No License', 'Failure to Carry DL'),
        ('No Permit', 'No MAYOR\'S PERMIT/MTOP/POP/PDP'),
        ('Overcharging', 'Overcharging'),
        ('DUI', 'Driving under the influence of liquor/drugs'),
        ('Defective Muffler', 'Operating a vehicle with Defective Muffler'),
        ('Dilapidated', 'Operating a Dilapidated Motorcab'),
        ('Reckless Driving', 'Reckless Driving'),
        ('Others', 'Others')
    ]

    VEHICLE_CLASSIFICATIONS = [
        ('Private', 'Private'),
        ('Public', 'Public'),
        ('Government', 'Government'),
        ('Commercial', 'Commercial')
    ]

    # Add a submission tracking field
    submission_id = models.CharField(max_length=36, blank=True, null=True, 
                                   help_text="UUID to track violations submitted together")
    
    # Driver's Details
    novr_number = models.CharField(max_length=50, blank=True, null=True)
    pin_number = models.CharField(max_length=50, blank=True, null=True)
    pd_number = models.CharField(max_length=50, blank=True, null=True)
    driver_photo = models.ImageField(upload_to='driver_photos/', blank=True, null=True)
    driver_address = models.TextField(blank=True, null=True)
    driver_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Operator's Details
    potpot_number = models.CharField(max_length=50, blank=True, null=True)
    operator = models.ForeignKey(Operator, on_delete=models.SET_NULL, null=True, blank=True, related_name='violations')
    operator_address = models.TextField(blank=True, null=True)
    operator_name = models.CharField(max_length=200, blank=True, null=True)
    operator_pd_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Additional Violation Details
    street_name = models.CharField(max_length=200, blank=True, null=True)
    landmark = models.CharField(max_length=200, blank=True, null=True)
    violation_code = models.CharField(max_length=10, blank=True, null=True)
    violation_time = models.TimeField(null=True, blank=True)
    vehicle_photo = models.ImageField(upload_to='vehicle_photos/', blank=True, null=True)
    secondary_photo = models.ImageField(upload_to='secondary_photos/', blank=True, null=True)
    
    # Existing Fields
    violator = models.ForeignKey(Violator, on_delete=models.CASCADE, related_name='violations')
    user_account = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='account_violations',
                                   help_text="If the violator is a registered user, link violation to their account")
    enforcer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='issued_violations')
    violation_date = models.DateTimeField(default=timezone.now)
    location = models.CharField(max_length=200)
    violation_type = models.TextField(help_text="Type of violation or comma-separated list of violations")
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_tdz_violation = models.BooleanField(default=False, help_text="Whether the violation occurred in a Traffic Discipline Zone, which doubles the fine")
    image = models.ImageField(upload_to=get_ncap_image_path, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    description = models.TextField(blank=True)
    payment_due_date = models.DateField(null=True, blank=True)
    enforcer_signature_date = models.DateTimeField(null=True, blank=True)
    violator_signature = models.ImageField(upload_to='signatures/', null=True, blank=True)
    violator_signature_date = models.DateTimeField(null=True, blank=True)
    vehicle_type = models.CharField(max_length=100, choices=[
        ('Jeepney', 'Jeepney'),
        ('Tricycle', 'Tricycle'),
        ('Potpot', 'Potpot'),
        ('Other', 'Other')
    ], default='Tricycle')
    classification = models.CharField(max_length=20, choices=VEHICLE_CLASSIFICATIONS, blank=True, null=True)
    plate_number = models.CharField(max_length=20, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    registration_number = models.CharField(max_length=50, blank=True, null=True)
    registration_date = models.DateField(null=True, blank=True)
    vehicle_owner = models.CharField(max_length=200, blank=True, null=True)
    vehicle_owner_address = models.TextField(blank=True, null=True)
    violation_types = models.TextField(default='[]')  # Store JSON as text
    receipt_number = models.CharField(max_length=50, blank=True, null=True)
    receipt_date = models.DateField(blank=True, null=True)
    payment_remarks = models.TextField(blank=True, null=True)

    # Adjudication fields
    adjudicated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='adjudicated_violations')
    adjudication_date = models.DateTimeField(null=True, blank=True)
    adjudication_remarks = models.TextField(blank=True, null=True)
    
    # Approval fields
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approved_violations')
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Payment fields
    payment_date = models.DateTimeField(null=True, blank=True)
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='processed_payments')

    def save(self, *args, **kwargs):
        if not self.payment_due_date:
            self.payment_due_date = timezone.now() + timezone.timedelta(days=7)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Citation {self.id} - {self.violator.license_number}"

    class Meta:
        ordering = ['-violation_date']

    def set_violation_types(self, types_list):
        self.violation_types = json.dumps(types_list)

    def get_violation_types(self):
        """Get a list of violation types for this violation."""
        try:
            # First try to get from the violation_types JSON field
            violation_types_json = self.violation_types
            if violation_types_json and violation_types_json != '[]':
                violation_types = json.loads(violation_types_json)
                if isinstance(violation_types, list) and violation_types:
                    return violation_types
            
            # If that's empty, use the violation_type field
            if self.violation_type:
                # If it's a comma-separated list, split it
                if ',' in self.violation_type:
                    return [vt.strip() for vt in self.violation_type.split(',')]
                return [self.violation_type]
            
            # Fallback
            return []
        except (json.JSONDecodeError, Exception):
            # Fallback to just using the violation_type field as a single item
            return [self.violation_type] if self.violation_type else []
    
    def get_violation_type_display(self):
        """
        For backwards compatibility after changing violation_type to TextField.
        Returns the violation type string directly.
        """
        return self.violation_type


class Payment(models.Model):
    violation = models.OneToOneField(Violation, on_delete=models.CASCADE)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100)

    def __str__(self):
        return f"Payment for Violation {self.violation.id}"


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('ENFORCER', 'Traffic Enforcer'),
        ('SUPERVISOR', 'Supervisor'),
        ('TREASURER', 'Treasurer'),
        ('CLERK', 'Office Clerk'),
        ('USER', 'Regular User'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    enforcer_id = models.CharField(max_length=10, unique=True, blank=True, null=True)  # Allow blank/null temporarily during creation
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone_number = models.CharField(max_length=15)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField()
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='USER')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    is_active_duty = models.BooleanField(default=False)
    license_number = models.CharField(max_length=20, null=True, blank=True)
    is_operator = models.BooleanField(default=False)
    operator_since = models.DateTimeField(null=True, blank=True)

    def get_permissions(self):
        permissions = {
            'ADMIN': [
                'Full system access',
                'User management',
                'System configuration',
                'Reports and analytics',
            ],
            'ENFORCER': [
                'Issue tickets',
                'Upload violations',
                'View assigned cases',
            ],
            'SUPERVISOR': [
                'View all violations',
                'Manage enforcers',
                'Generate reports',
            ],
            'TREASURER': [
                'Process payments',
                'Record payments',
                'View approved violations',
                'Generate payment reports',
            ],
            'CLERK': [
                'Process payments',
                'View violations',
                'Generate basic reports',
            ],
            'USER': [
                'View own violations',
                'Pay violations',
                'File reports',
                'Update profile',
            ]
        }
        return permissions.get(self.role, [])

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.enforcer_id or 'No ID'}"

    def save(self, *args, **kwargs):
        # Generate enforcer_id if it's not set
        if not self.enforcer_id:
            # Try to generate an enforcer ID or use a fallback
            try:
                from django.utils import timezone
                import random
                prefix = 'ENF'
                # Create a more unique fallback ID using timestamp and random number
                timestamp = int(timezone.now().timestamp())
                random_suffix = random.randint(1000, 9999)
                self.enforcer_id = f"{prefix}{timestamp % 10000}{random_suffix}"
                
                # Check if this enforcer_id already exists, and if so, generate a new one
                collision_count = 0
                while UserProfile.objects.filter(enforcer_id=self.enforcer_id).exists():
                    random_suffix = random.randint(1000, 9999)
                    self.enforcer_id = f"{prefix}{timestamp % 10000}{random_suffix}"
                    collision_count += 1
                    if collision_count > 10:  # Prevent infinite loops
                        self.enforcer_id = f"{prefix}{timestamp}{random_suffix}"
                        break
            except Exception as e:
                # Last resort fallback
                import uuid
                self.enforcer_id = f"ENF{str(uuid.uuid4())[:7]}"
        
        # Validate license number format for regular users
        if self.role == 'USER' and self.license_number:
            import re
            if not re.match(r'^[A-Z0-9-]+$', self.license_number):
                raise ValidationError('License number should contain only uppercase letters, numbers, and hyphens')
                
        # Generate QR code for profile
        if not self.qr_code:
            try:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(f"Enforcer ID: {self.enforcer_id}\nName: {self.user.get_full_name()}")
                qr.make(fit=True)

                img = qr.make_image(fill_color="black", back_color="white")
                blob = BytesIO()
                img.save(blob, 'PNG')
                self.qr_code.save(f'qr_{self.enforcer_id}.png', File(blob), save=False)
            except Exception as e:
                # Handle exception if QR code generation fails
                pass
        
        super().save(*args, **kwargs)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        from .views import generate_enforcer_id  # Import here to avoid circular import
        UserProfile.objects.create(
            user=instance,
            enforcer_id=generate_enforcer_id(),
            phone_number='',
            address=''
        )

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()


class ActivityLog(models.Model):
    CATEGORY_CHOICES = [
        ('general', 'General'),
        ('violation', 'Violation'),
        ('user', 'User'),
        ('payment', 'Payment'),
        ('system', 'System'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.action}"


class Announcement(models.Model):
    CATEGORY_CHOICES = [
        ('GENERAL', 'General'),
        ('POLICY', 'Policy Update'),
        ('SYSTEM', 'System Update'),
        ('EMERGENCY', 'Emergency'),
        ('EVENT', 'Event'),
    ]
    
    AUDIENCE_CHOICES = [
        ('ALL', 'All Users'),
        ('ADMIN', 'Administrators'),
        ('ENFORCER', 'Traffic Enforcers'),
        ('SUPERVISOR', 'Supervisors'),
        ('TREASURER', 'Treasurers'),
        ('CLERK', 'Office Clerks'),
        ('USER', 'Regular Users'),
    ]
    
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High')
    ]
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='GENERAL')
    target_audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default='ALL')
    is_popup = models.BooleanField(default=False)
    requires_acknowledgment = models.BooleanField(default=False)
    publish_date = models.DateTimeField(null=True, blank=True)
    expiration_date = models.DateTimeField(null=True, blank=True)
    geographic_area = models.CharField(max_length=255, blank=True, null=True)
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
        
    def get_category_display(self):
        """Return the display value for the category"""
        for code, name in self.CATEGORY_CHOICES:
            if code == self.category:
                return name
        return self.category


class AnnouncementAcknowledgment(models.Model):
    """Model to track which users have acknowledged which announcements"""
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    acknowledged_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['announcement', 'user']
        verbose_name = 'Announcement Acknowledgment'
        verbose_name_plural = 'Announcement Acknowledgments'
        
    def __str__(self):
        return f"{self.user.username} acknowledged {self.announcement.title}"

class LocationHistory(models.Model):
    """Model to track location history for enforcers"""
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='location_history')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy = models.FloatField(blank=True, null=True)
    heading = models.FloatField(blank=True, null=True)
    speed = models.FloatField(blank=True, null=True)
    is_active_duty = models.BooleanField(default=True)
    battery_level = models.FloatField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    device_info = models.JSONField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Location History'
        verbose_name_plural = 'Location Histories'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['user_profile', 'timestamp']),
        ]
        
    def __str__(self):
        return f"{self.user_profile.user.get_full_name()} - {self.timestamp}"


class OperatorType(models.Model):
    """Model to store different types of operators (Potpot, Jeepney, Tricycle, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Operator Type'
        verbose_name_plural = 'Operator Types'
        ordering = ['name']

    def __str__(self):
        return self.name


class Vehicle(models.Model):
    """Model to store vehicle information linked to an operator"""
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE)
    old_pd_number = models.CharField(max_length=50, blank=True, null=True)
    new_pd_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    potpot_number = models.CharField(max_length=50, blank=True, null=True, help_text="Potpot identification number")
    vehicle_type = models.CharField(max_length=100, choices=[
        ('Jeepney', 'Jeepney'),
        ('Tricycle', 'Tricycle'),
        ('Potpot', 'Potpot'),
        ('Other', 'Other')
    ], default='Tricycle')
    plate_number = models.CharField(max_length=20, blank=True, null=True)
    engine_number = models.CharField(max_length=50, blank=True, null=True)
    chassis_number = models.CharField(max_length=50, blank=True, null=True)
    capacity = models.PositiveIntegerField(default=4, blank=True, null=True)
    year_model = models.CharField(max_length=4, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Vehicle'
        verbose_name_plural = 'Vehicles'
        ordering = ['operator__last_name', 'operator__first_name', 'new_pd_number']
        
    def __str__(self):
        return f"{self.new_pd_number or 'No PD Number'} - {self.operator.full_name()}"

    def generate_pd_number(self):
        """Generate a unique PD number for this vehicle"""
        # Format: PD-{random_1_to_3_digits}
        import random
        while True:
            random_suffix = str(random.randint(1, 999))
            new_pd = f"PD-{random_suffix}"
            # Check if this PD number exists in either Vehicles or Drivers
            if not Vehicle.objects.filter(new_pd_number=new_pd).exists() and not Driver.objects.filter(new_pd_number=new_pd).exists():
                return new_pd

    def save(self, *args, **kwargs):
        # No longer auto-generating PD number
        super().save(*args, **kwargs)


class Driver(models.Model):
    """Model representing a driver"""
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    middle_initial = models.CharField(max_length=10, blank=True, null=True)
    address = models.TextField()
    old_pd_number = models.CharField(max_length=20, blank=True, null=True)
    new_pd_number = models.CharField(max_length=20, unique=True)
    license_number = models.CharField(max_length=50, blank=True, null=True)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    emergency_contact = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_number = models.CharField(max_length=20, blank=True, null=True)
    active = models.BooleanField(default=True)
    operator = models.ForeignKey(Operator, on_delete=models.SET_NULL, null=True, blank=True, related_name='drivers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.last_name}, {self.first_name} ({self.new_pd_number})"
    
    def get_full_name(self):
        """Return the driver's full name"""
        if self.middle_initial:
            return f"{self.first_name} {self.middle_initial}. {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    def generate_pd_number(self):
        """Generate a unique PD number for this driver"""
        # Format: PD-{random_1_to_3_digits}
        import random
        while True:
            random_suffix = str(random.randint(1, 999))
            new_pd = f"PD-{random_suffix}"
            # Check if this PD number exists in either Drivers or Vehicles
            if not Driver.objects.filter(new_pd_number=new_pd).exists() and not Vehicle.objects.filter(new_pd_number=new_pd).exists():
                return new_pd

    def save(self, *args, **kwargs):
        # Generate PD number if not provided
        if not self.new_pd_number:
            self.new_pd_number = self.generate_pd_number()
        super().save(*args, **kwargs)


class DriverVehicleAssignment(models.Model):
    """Model to track the relationship between drivers and vehicles with history"""
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='vehicle_assignments')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='driver_assignments')
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Driver-Vehicle Assignment'
        verbose_name_plural = 'Driver-Vehicle Assignments'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.driver} assigned to {self.vehicle}"
    
    def end_assignment(self):
        """End this assignment"""
        self.end_date = timezone.now()
        self.is_active = False
        self.save()


class OperatorApplication(models.Model):
    """Model to store operator applications with necessary documentation"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='operator_applications')
    business_permit = models.FileField(upload_to='permits/')
    police_clearance = models.FileField(upload_to='police_clearance/', null=True, blank=True, help_text="Police clearance certificate")
    barangay_certificate = models.FileField(upload_to='barangay_certificate/', null=True, blank=True, help_text="Barangay certificate")
    cedula = models.FileField(upload_to='cedula/', null=True, blank=True, help_text="Community Tax Certificate (Cedula)")
    cenro_tickets = models.FileField(upload_to='cenro_tickets/', null=True, blank=True, help_text="CENRO permits/tickets")
    mayors_permit = models.FileField(upload_to='mayors_permits/', blank=True, null=True)
    other_documents = models.FileField(upload_to='operator_docs/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                     related_name='processed_applications')
    
    class Meta:
        verbose_name = 'Operator Application'
        verbose_name_plural = 'Operator Applications'
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"Application by {self.user.username} ({self.get_status_display()})"


class ViolationCertificate(models.Model):
    """Model to store certificate information for violations"""
    violation = models.OneToOneField(Violation, on_delete=models.CASCADE, related_name='certificate')
    operations_officer = models.CharField(max_length=100, blank=True, null=True)
    ctm_officer = models.CharField(max_length=100, blank=True, null=True)
    certificate_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Certificate for Violation {self.violation.id}"