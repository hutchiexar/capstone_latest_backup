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



class Violator(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    license_number = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.license_number}"

    class Meta:
        unique_together = ['license_number']  # Ensure unique license numbers


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

    violator = models.ForeignKey(Violator, on_delete=models.CASCADE)
    violation_date = models.DateTimeField(default=timezone.now)
    location = models.CharField(max_length=200)
    violation_type = models.CharField(max_length=100, choices=VIOLATION_CHOICES)
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='violations/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    description = models.TextField(blank=True)
    payment_due_date = models.DateField(null=True, blank=True)
    enforcer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='issued_violations')
    enforcer_signature_date = models.DateTimeField(null=True, blank=True)
    violator_signature = models.ImageField(upload_to='signatures/', null=True, blank=True)
    violator_signature_date = models.DateTimeField(null=True, blank=True)
    vehicle_type = models.CharField(max_length=100, blank=True, null=True, verbose_name='Type/Make of Vehicle')
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
        return json.loads(self.violation_types)


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
    enforcer_id = models.CharField(max_length=10, unique=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='USER')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    is_active_duty = models.BooleanField(default=False)
    license_number = models.CharField(max_length=20, null=True, blank=True)

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
        return f"{self.user.get_full_name()} - {self.enforcer_id}"

    def save(self, *args, **kwargs):
        if not self.qr_code:
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
    
    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.action}"


class Announcement(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    priority = models.CharField(max_length=20, choices=[
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High')
    ], default='MEDIUM')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title