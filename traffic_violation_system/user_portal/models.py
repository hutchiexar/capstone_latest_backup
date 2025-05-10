from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q

class UserNotification(models.Model):
    NOTIFICATION_TYPES = [
        ('VIOLATION', 'New Violation'),
        ('PAYMENT', 'Payment Reminder'),
        ('STATUS', 'Status Update'),
        ('SYSTEM', 'System Notification'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    reference_id = models.IntegerField(null=True, blank=True)  # For linking to violations or other objects

    def clean(self):
        """Validate the notification type is one of the allowed choices"""
        valid_types = [choice[0] for choice in self.NOTIFICATION_TYPES]
        if self.type not in valid_types:
            raise ValidationError({'type': f"'{self.type}' is not a valid notification type. Valid types are: {', '.join(valid_types)}"})
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def get_icon(self):
        icons = {
            'VIOLATION': 'gavel',
            'PAYMENT': 'payments',
            'STATUS': 'update',
            'SYSTEM': 'info',
        }
        return icons.get(self.type, 'notifications')

    def get_icon_color(self):
        colors = {
            'VIOLATION': '#dc3545',
            'PAYMENT': '#198754',
            'STATUS': '#0d6efd',
            'SYSTEM': '#6c757d',
        }
        return colors.get(self.type, '#6c757d')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_display()} for {self.user.get_full_name()}"


class UserReport(models.Model):
    REPORT_TYPES = [
        ('COMPLAINT', 'Traffic Complaint'),
        ('SUGGESTION', 'Improvement Suggestion'),
        ('INQUIRY', 'General Inquiry'),
        ('DISPUTE', 'Violation Dispute'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    type = models.CharField(max_length=20, choices=REPORT_TYPES)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200, blank=True)
    incident_date = models.DateTimeField(null=True, blank=True)
    attachment = models.FileField(upload_to='reports/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For tracking responses and resolution
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_reports'
    )
    resolution_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def mark_resolved(self, notes, user):
        self.status = 'RESOLVED'
        self.resolution_notes = notes
        self.resolved_at = timezone.now()
        self.assigned_to = user
        self.save()

        # Create notification for user
        UserNotification.objects.create(
            user=self.user,
            type='SYSTEM',
            message=f'Your report "{self.subject}" has been resolved.'
        )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_display()} - {self.subject}"


class UserViolationManager(models.Manager):
    def get_queryset(self):
        """
        Override the default queryset to ensure this manager is properly used with the Violation model
        """
        return super().get_queryset()
        
    def get_active_violations(self, user):
        """Get active violations for a user"""
        from django.db.models import Q
        
        if not hasattr(user, 'userprofile') or not user.userprofile.license_number:
            return self.filter(
                user_account=user,
                status__in=['PENDING', 'ADJUDICATED', 'APPROVED']
            )
            
        return self.filter(
            Q(violator__license_number=user.userprofile.license_number) | Q(user_account=user),
            status__in=['PENDING', 'ADJUDICATED', 'APPROVED']
        )

    def get_due_soon_violations(self, user):
        """Get violations due soon for a user"""
        from django.db.models import Q
        seven_days_from_now = timezone.now() + timezone.timedelta(days=7)
        
        if not hasattr(user, 'userprofile') or not user.userprofile.license_number:
            return self.filter(
                user_account=user,
                status__in=['PENDING', 'ADJUDICATED', 'APPROVED'],
                payment_due_date__lte=seven_days_from_now
            )
            
        return self.filter(
            Q(violator__license_number=user.userprofile.license_number) | Q(user_account=user),
            status__in=['PENDING', 'ADJUDICATED', 'APPROVED'],
            payment_due_date__lte=seven_days_from_now
        )

    def get_total_paid(self, user):
        """Get total paid amount for a user"""
        from django.db.models import Q, Sum
        
        if not hasattr(user, 'userprofile') or not user.userprofile.license_number:
            return self.filter(
                user_account=user,
                status='PAID'
            ).aggregate(
                total=Sum('fine_amount')
            )['total'] or 0
            
        return self.filter(
            Q(violator__license_number=user.userprofile.license_number) | Q(user_account=user),
            status='PAID'
        ).aggregate(
            total=Sum('fine_amount')
        )['total'] or 0
        
    def get_user_violations(self, user):
        """
        Get all violations associated with this user, either by license number,
        directly associated with the user account, or through QR hashes
        """
        from django.db.models import Q
        import logging
        logger = logging.getLogger(__name__)
        
        # If user doesn't have a profile or license number, just filter by user account
        if not hasattr(user, 'userprofile'):
            return self.filter(user_account=user)
            
        # Log that we're getting violations for this user
        logger.info(f"Getting violations for user: {user.username} (ID: {user.id})")
            
        # Build a query for all possible ways this user could be connected to violations
        query = Q(user_account=user)
        
        # Add license number check if license number exists
        if user.userprofile.license_number:
            # Standardize the license number format for consistent matching
            std_license = user.userprofile.license_number.strip().upper().replace(' ', '')
            query |= Q(violator__license_number__iexact=std_license)
            logger.info(f"Adding license number filter: {std_license}")
            
            # Also try the original format in case it's stored differently
            if std_license != user.userprofile.license_number:
                query |= Q(violator__license_number__iexact=user.userprofile.license_number)
                logger.info(f"Adding original license number filter: {user.userprofile.license_number}")
        
        # If user is a driver, check for driver PD number
        if user.userprofile.is_driver:
            # Try to get the driver's PD number from the Driver model
            try:
                from traffic_violation_system.models import Driver
                drivers = Driver.objects.filter(
                    Q(first_name__iexact=user.first_name, last_name__iexact=user.last_name) |
                    Q(license_number__iexact=user.userprofile.license_number if user.userprofile.license_number else 'nomatch')
                )
                if drivers.exists():
                    driver = drivers.first()
                    if driver.new_pd_number:
                        query |= Q(pd_number=driver.new_pd_number)
                        logger.info(f"Adding PD number filter: {driver.new_pd_number}")
            except Exception as e:
                # If there's an error, just log it and continue without this part of the filter
                logger.error(f"Error getting driver PD number: {str(e)}")

        # Add check for QR hashes registered to this user
        try:
            from traffic_violation_system.models import ViolatorQRHash
            
            # Get all QR hashes registered to this user
            qr_hashes = ViolatorQRHash.objects.filter(user_account=user)
            
            if qr_hashes.exists():
                # Add a filter for violations linked to any of the user's QR hashes
                logger.info(f"Found {qr_hashes.count()} QR hashes for user {user.username}")
                qr_hash_ids = list(qr_hashes.values_list('id', flat=True))
                query |= Q(qr_hash__in=qr_hash_ids)
                logger.info(f"Adding QR hash filter with IDs: {qr_hash_ids}")
                
                # Log individual QR hashes for debugging
                for qr_hash in qr_hashes:
                    violations_count = self.filter(qr_hash=qr_hash).count()
                    logger.info(f"QR hash {qr_hash.hash_id} (ID: {qr_hash.id}) has {violations_count} linked violations")
                    
                    # For each violation linked to this QR hash, check if it's already associated with the user
                    linked_violations = self.filter(qr_hash=qr_hash)
                    for violation in linked_violations:
                        if violation.user_account_id != user.id:
                            logger.warning(f"Violation ID {violation.id} with QR hash {qr_hash.hash_id} is not directly linked to user {user.username}. Current user_account: {violation.user_account_id}")
        except Exception as e:
            logger.error(f"Error checking QR hashes for user: {str(e)}")
            
        # Add check for violations with matching violator name
        try:
            full_name = f"{user.first_name} {user.last_name}".strip().lower()
            if full_name and full_name != " ":
                query |= Q(violator__first_name__iexact=user.first_name, violator__last_name__iexact=user.last_name)
                logger.info(f"Adding name filter for: {user.first_name} {user.last_name}")
                
                # Also check driver_name field which sometimes contains the full name
                query |= Q(driver_name__icontains=full_name)
                logger.info(f"Adding driver_name filter for: {full_name}")
        except Exception as e:
            logger.error(f"Error adding name filters: {str(e)}")
        
        # Return violations matching any of the conditions
        violations = self.filter(query).distinct()
        logger.info(f"Found {violations.count()} total violations for user {user.username}")
        
        # Enhanced logging for each found violation
        for v in violations:
            v_license = getattr(v.violator, 'license_number', 'Unknown') if hasattr(v, 'violator') and v.violator else 'No violator'
            v_name = f"{getattr(v.violator, 'first_name', '')} {getattr(v.violator, 'last_name', '')}" if hasattr(v, 'violator') and v.violator else 'No violator'
            v_hash_id = v.qr_hash.hash_id if v.qr_hash else 'No QR hash'
            v_user_id = v.user_account.id if v.user_account else 'Not linked'
            
            logger.info(f"Violation ID {v.id}: License={v_license}, Name={v_name}, QR Hash={v_hash_id}, User ID={v_user_id}")
            
            # If this violation has a QR hash but is not directly linked to the user, link it now
            if v.qr_hash and v.qr_hash.user_account_id == user.id and (not v.user_account or v.user_account.id != user.id):
                try:
                    logger.warning(f"Fixing missing user account link for violation {v.id} - linking to user {user.username}")
                    v.user_account = user
                    v.save(update_fields=['user_account'])
                except Exception as e:
                    logger.error(f"Error fixing user account link for violation {v.id}: {str(e)}")
        
        return violations


class VehicleRegistration(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registered_vehicles')
    or_number = models.CharField(max_length=50, unique=True)  # OR Number
    cr_number = models.CharField(max_length=50, unique=True)  # CR Number
    plate_number = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=100)
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year_model = models.CharField(max_length=4)
    color = models.CharField(max_length=50)
    classification = models.CharField(max_length=20, choices=[
        ('Private', 'Private'),
        ('Public', 'Public'),
        ('Government', 'Government'),
        ('Commercial', 'Commercial')
    ])
    registration_date = models.DateField()
    expiry_date = models.DateField()
    or_cr_image = models.ImageField(upload_to='or_cr_images/')
    capacity = models.PositiveIntegerField(default=4)  # Default to 4 passengers
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.plate_number} - {self.vehicle_type}"

    class Meta:
        ordering = ['-created_at']


class OperatorViolationLookup(models.Model):
    """Model to track when vehicle owners look up operators to check their violation history"""
    vehicle_owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='operator_lookups')
    operator_license = models.CharField(max_length=20)  # License number of the operator being looked up
    operator_name = models.CharField(max_length=200)    # Name of the operator being looked up
    lookup_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-lookup_date']
        
    def __str__(self):
        return f"{self.vehicle_owner.get_full_name()} looked up {self.operator_name} on {self.lookup_date}"


class DriverApplication(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='driver_applications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Required documents
    cttmo_seminar_certificate = models.FileField(upload_to='driver_applications/cttmo_certificates/', blank=False)
    xray_results = models.FileField(upload_to='driver_applications/xray_results/', blank=False)
    medical_certificate = models.FileField(upload_to='driver_applications/medical_certificates/', blank=False)
    police_clearance = models.FileField(upload_to='driver_applications/police_clearance/', blank=False)
    mayors_permit = models.FileField(upload_to='driver_applications/mayors_permit/', blank=False)
    other_documents = models.FileField(upload_to='driver_applications/other_documents/', blank=True, null=True)
    
    # Application tracking fields
    submitted_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_driver_applications')
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Driver Application'
        verbose_name_plural = 'Driver Applications'
    
    def __str__(self):
        return f"Driver Application by {self.user.get_full_name()} ({self.status})"
    
    def mark_as_processed(self, processed_by, status, notes=None):
        self.status = status
        self.processed_by = processed_by
        self.processed_at = timezone.now()
        if notes:
            self.notes = notes
        self.save()
        
        # Update user's status based on application outcome
        if status == 'APPROVED':
            profile = self.user.userprofile
            profile.is_driver = True
            profile.save()
            
            # Create Driver record with auto-generated PD number
            from traffic_violation_system.models import Driver
            
            # Create a new Driver record if one doesn't already exist for this user
            try:
                # Check if driver already exists with this user's data
                existing_drivers = Driver.objects.filter(
                    first_name=self.user.first_name,
                    last_name=self.user.last_name
                )
                
                if not existing_drivers.exists():
                    # Generate a PD number
                    import random
                    while True:
                        random_suffix = str(random.randint(1, 999)).zfill(3)  # Ensure 3 digits with leading zeros
                        pd_number = f"PD-{random_suffix}"
                        # Check if this PD number already exists
                        if not Driver.objects.filter(new_pd_number=pd_number).exists():
                            break
                    
                    # Create new driver record
                    driver = Driver.objects.create(
                        first_name=self.user.first_name,
                        last_name=self.user.last_name,
                        address=profile.address,
                        new_pd_number=pd_number,
                        license_number=profile.license_number,
                        contact_number=profile.contact_number or profile.phone_number,
                        active=True
                    )
                    
                    # Update notification message to include PD number
                    notification_message = f'Your application to become a driver has been approved. Your PD number is {pd_number}.'
                else:
                    # Driver already exists
                    driver = existing_drivers.first()
                    notification_message = f'Your application to become a driver has been approved. Your PD number is {driver.new_pd_number}.'
                    
            except Exception as e:
                # Log the error but continue with approval
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating driver record: {str(e)}")
                notification_message = 'Your application to become a driver has been approved.'
            
            # Send notification to user
            UserNotification.objects.create(
                user=self.user,
                type='SYSTEM',
                message=notification_message,
                reference_id=self.id
            )
        elif status == 'REJECTED':
            # Send notification to user
            UserNotification.objects.create(
                user=self.user,
                type='SYSTEM',
                message=f'Your application to become a driver has been rejected. Reason: {notes}',
                reference_id=self.id
            ) 