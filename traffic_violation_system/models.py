from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import math
import uuid
import qrcode
from io import BytesIO
from django.core.files import File
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
import random
from django.db.models.signals import post_save
from django.dispatch import receiver
import json
import os
from traffic_violation_system.user_portal.models import UserViolationManager



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


class ViolationType(models.Model):
    """Model to store violation types and their associated fine amounts"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100, choices=[
        ('LICENSING', 'Licensing Violations'),
        ('REGISTRATION', 'Registration & Accessories'),
        ('DIMENSION', 'Dimensions & Load Limits'),
        ('FRANCHISE', 'Franchise & Permits'),
        ('OTHER', 'Other Violations')
    ])
    classification = models.CharField(
        max_length=50,
        choices=[
            ('REGULAR', 'Regular Violations'),
            ('NCAP', 'NCAP')
        ],
        default='REGULAR',
        help_text="Classification of violation (Regular for direct tickets, NCAP for uploaded violations)"
    )
    is_active = models.BooleanField(default=True)
    is_ncap = models.BooleanField(default=False, help_text="Whether this violation type is for NCAP (Non-Contact Apprehension Program)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Violation Type"
        verbose_name_plural = "Violation Types"
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} (₱{self.amount})"
    
    def save(self, *args, **kwargs):
        # Ensure is_ncap and classification stay in sync
        if self.classification == 'NCAP':
            self.is_ncap = True
        else:
            self.is_ncap = False
        super().save(*args, **kwargs)


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
    active = models.BooleanField(default=True)
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
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('ADJUDICATED', 'Adjudicated'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('PAID', 'Paid'),
        ('SETTLED', 'Settled'),
        ('CONTESTED', 'Contested'),
        ('HEARING_SCHEDULED', 'Hearing Scheduled'),
        ('DISMISSED', 'Dismissed'),
        ('EXPIRED', 'Expired'),
        ('ISSUED_DIRECT', 'Issued Direct'),  # Added for direct ticket issuance
    )

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
    
    # Add custom manager
    objects = models.Manager()  # The default manager
    user_violations = UserViolationManager()  # Custom manager for user violations

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
    violation_type_obj = models.ForeignKey(ViolationType, on_delete=models.SET_NULL, null=True, blank=True, 
                                        related_name='violations', verbose_name="Violation Type")
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
    original_violation_types = models.TextField(blank=True, null=True, help_text="Original violation types before adjudication (stored as JSON)")
    original_fine_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Original fine amount before adjudication")
    removed_violations = models.TextField(blank=True, null=True, help_text="Violations removed during adjudication with reasons (stored as JSON)")
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

    # Signature fields
    signature_refused = models.BooleanField(default=False, help_text="Whether the violator refused to sign")
    refusal_note = models.TextField(blank=True, null=True, help_text="Reason for signature refusal")
    signature_file = models.CharField(max_length=255, blank=True, null=True, help_text="Filename or path of the signature file")
    
    # Direct ticket fields
    direct_ticket_details = models.TextField(blank=True, null=True)
    citation_number = models.CharField(max_length=50, blank=True, null=True)
    issue_date = models.DateField(null=True, blank=True)
    court_date = models.DateField(null=True, blank=True)
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_direct_tickets')

    # New fields
    qr_hash = models.ForeignKey('ViolatorQRHash', on_delete=models.SET_NULL, null=True, blank=True, related_name='violations')

    def save(self, *args, **kwargs):
        if not self.payment_due_date:
            self.payment_due_date = timezone.now() + timezone.timedelta(days=7)
        
        # If using a ViolationType object and this is a new record or the type changed, update the fine amount
        if self.violation_type_obj and (not self.pk or 'violation_type_obj' in kwargs.get('update_fields', [])):
            # Set the fine amount from the violation type, but only if not manually overridden
            if not self.fine_amount or self.fine_amount == 0:
                self.fine_amount = self.violation_type_obj.amount
                
            # If in a Traffic Discipline Zone, double the fine amount
            if self.is_tdz_violation:
                self.fine_amount *= 2
        
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
        ('EDUCATOR', 'Educator'),
        ('ADJUDICATOR', 'Adjudicator'),
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
    is_driver = models.BooleanField(default=False)
    operator_since = models.DateTimeField(null=True, blank=True)
    birthdate = models.DateField(null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=100, null=True, blank=True)
    emergency_contact_number = models.CharField(max_length=15, null=True, blank=True)
    is_email_verified = models.BooleanField(default=False)
    
    def generate_qr_code(self):
        """Generate QR code for user profile"""
        try:
            import qrcode
            from io import BytesIO
            from django.core.files.base import ContentFile
            
            # Create QR code instance
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            
            # Add data to QR code (user ID and username for identification)
            qr_data = f"uid:{self.user.id}-{self.user.username}"
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Create an image from the QR Code
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save the image to a BytesIO object
            buffer = BytesIO()
            img.save(buffer)
            buffer.seek(0)
            
            # Create a Django-friendly image file
            filename = f"qr_{self.user.username}.png"
            self.qr_code.save(filename, ContentFile(buffer.read()), save=False)
            
        except ImportError:
            # Log that qrcode package is not installed
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("qrcode package not installed, QR code not generated")
        except Exception as e:
            # Log any other errors
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating QR code: {str(e)}")

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
            'EDUCATOR': [
                'Manage educational content',
                'Create and edit topics',
                'Manage categories',
                'Create and manage quizzes',
                'View learning analytics',
            ],
            'ADJUDICATOR': [
                'Review violations',
                'Adjudicate violations',
                'Modify violation status',
                'Schedule hearings',
                'Generate adjudication reports',
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
        # Handle enforcer_id if not already set
        is_new = not self.pk
        if is_new and not self.enforcer_id and self.role == 'ENFORCER':
            self.enforcer_id = generate_enforcer_id()
            
        # Call the real save method
        super().save(*args, **kwargs)
        
        # Generate and save QR code only once or when updating necessary info
        if not self.qr_code or is_new or 'license_number' in kwargs.get('update_fields', []):
            self.generate_qr_code()

    def calculate_age(self):
        """Calculate age based on birthdate"""
        from datetime import date
        if self.birthdate:
            today = date.today()
            return today.year - self.birthdate.year - ((today.month, today.day) < (self.birthdate.month, self.birthdate.day))
        return None


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        from .views import generate_enforcer_id  # Import here to avoid circular import
        UserProfile.objects.create(
            user=instance,
            enforcer_id=generate_enforcer_id(),
            phone_number='',
            address='',
            is_email_verified=False  # Set email verification to False by default
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
        ('EDUCATOR', 'Educators'),
        ('ADJUDICATOR', 'Adjudicators'),
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
    new_pd_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    license_number = models.CharField(max_length=50, blank=True, null=True)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    birthdate = models.DateField(blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_number = models.CharField(max_length=20, blank=True, null=True)
    active = models.BooleanField(default=True)
    expiration_date = models.DateField(blank=True, null=True)
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

    def get_expiration_status(self):
        """Return the expiration status of the driver's license"""
        if not self.expiration_date:
            return "UNKNOWN"
        
        today = timezone.now().date()
        thirty_days_from_now = today + timezone.timedelta(days=30)
        
        if self.expiration_date < today:
            return "EXPIRED"
        elif self.expiration_date <= thirty_days_from_now:
            return "EXPIRING_SOON"
        else:
            return "VALID"

    def save(self, *args, **kwargs):
        # Generate PD number if not provided
        if not self.new_pd_number:
            self.new_pd_number = self.generate_pd_number()
        
        # Set expiration date to 1 year from creation if not provided
        if not self.expiration_date and self.created_at:
            # Convert to date object if it's a datetime
            created_date = self.created_at.date() if hasattr(self.created_at, 'date') else self.created_at
            self.expiration_date = created_date + timezone.timedelta(days=365)
        # If it's a new driver (no created_at yet), expiration will be set after save
        
        super().save(*args, **kwargs)
        
        # For newly created drivers, set expiration date after save
        if not self.expiration_date:
            self.expiration_date = self.created_at.date() + timezone.timedelta(days=365)
            # Save again, but avoid infinite recursion
            Driver.objects.filter(pk=self.pk).update(expiration_date=self.expiration_date)


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
                                     related_name='processed_operator_applications')
    extra_data = models.TextField(blank=True, null=True, help_text="JSON-encoded additional data such as number of units")
    
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


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    verification_code = models.CharField(max_length=8, blank=True, null=True, help_text="One-time verification code sent via email")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def __str__(self):
        return f"Verification token for {self.user.username}"
    
    def is_valid(self):
        return timezone.now() <= self.expires_at
    
    def save(self, *args, **kwargs):
        # Set expiration date to 24 hours from creation if not set
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        
        # Generate a random alphanumeric verification code if not set
        if not self.verification_code:
            import random
            import string
            # Generate a random 6-character alphanumeric code
            chars = string.ascii_uppercase + string.digits
            self.verification_code = ''.join(random.choice(chars) for _ in range(6))
            
        super().save(*args, **kwargs)


class ViolatorQRHash(models.Model):
    """
    This model stores the QR code hash that links multiple violations for the same violator.
    It allows a single QR code to be used for multiple tickets and directs users to a registration page.
    """
    # Unique hash ID used in QR code URLs
    hash_id = models.CharField(max_length=64, unique=True, db_index=True)
    
    # Violator information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    license_number = models.CharField(max_length=20, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    
    # Registration status
    registered = models.BooleanField(default=False)
    user_account = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='qr_hashes')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # Optional expiration date
    
    def __str__(self):
        return f"QR Hash for {self.first_name} {self.last_name} ({self.hash_id})"
    
    def get_violations(self):
        """Get all violations associated with this QR hash"""
        return Violation.objects.filter(qr_hash=self)
    
    def get_register_url(self):
        """Get the URL for the registration page with this hash"""
        from django.urls import reverse
        return reverse('register_with_violations', kwargs={'hash_id': self.hash_id})
    
    def get_total_fine(self):
        """Get the total fine amount for all violations"""
        return sum(v.fine_amount for v in self.get_violations())
    
    def generate_hash(first_name, last_name, license_number=None):
        """Generate a unique hash based on violator information"""
        import uuid
        import hashlib
        import logging
        
        # Get logger
        logger = logging.getLogger(__name__)
        logger.info(f"ViolatorQRHash.generate_hash called for: {first_name} {last_name}, license: {license_number}")
        
        # Standardize inputs
        first_name = first_name.strip().lower() if first_name else "unknown"
        last_name = last_name.strip().lower() if last_name else "unknown"
        license_number = license_number.strip().upper().replace(' ', '') if license_number else None
        
        # First, try to find an existing hash based on identifying information
        # The calling code should handle database interactions, so this remains a static method
        try:
            from django.apps import apps
            ViolatorQRHash = apps.get_model('traffic_violation_system', 'ViolatorQRHash')
            
            # Check for existing hash based on license number or name
            existing_hash = None
            
            # First check by license number if available
            if license_number:
                logger.info(f"Looking for existing QR hash by license number: {license_number}")
                existing_hash = ViolatorQRHash.objects.filter(
                    license_number__iexact=license_number
                ).first()
                if existing_hash:
                    logger.info(f"REUSING existing QR hash by license number: {existing_hash.hash_id} for {first_name} {last_name}")
                    return existing_hash.hash_id
            
            # If no match by license, try by name
            if first_name != "unknown" and last_name != "unknown":
                logger.info(f"Looking for existing QR hash by name: {first_name} {last_name}")
                existing_hash = ViolatorQRHash.objects.filter(
                    first_name__iexact=first_name,
                    last_name__iexact=last_name
                ).first()
                if existing_hash:
                    logger.info(f"REUSING existing QR hash by name: {existing_hash.hash_id} for {first_name} {last_name}")
                    return existing_hash.hash_id
                
        except Exception as e:
            # If there's any error during lookup, continue with new hash creation
            logger.error(f"Error looking up existing QR hash: {str(e)}")
            pass
        
        # Create a base string with violator information that's deterministic
        # (same input will always produce same output)
        base = f"{first_name}:{last_name}"
        if license_number:
            base += f":{license_number}"
            
        # Use a salt to add some security but ensure same input produces same hash
        salt = "traffic-violation-system-salt-2023"  # Static salt
        base += f":{salt}"
        
        # Create a SHA-256 hash and take the first 16 characters
        hash_id = hashlib.sha256(base.encode()).hexdigest()[:16]
        logger.info(f"CREATING new QR hash: {hash_id} for {first_name} {last_name}")
        return hash_id