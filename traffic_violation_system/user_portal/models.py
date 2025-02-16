from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

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
    def get_active_violations(self, user):
        return self.filter(
            violator__license_number=user.userprofile.license_number,
            status__in=['PENDING', 'ADJUDICATED', 'APPROVED']
        )

    def get_due_soon_violations(self, user):
        seven_days_from_now = timezone.now() + timezone.timedelta(days=7)
        return self.filter(
            violator__license_number=user.userprofile.license_number,
            status__in=['PENDING', 'ADJUDICATED', 'APPROVED'],
            payment_due_date__lte=seven_days_from_now
        )

    def get_total_paid(self, user):
        return self.filter(
            violator__license_number=user.userprofile.license_number,
            status='PAID'
        ).aggregate(
            total=models.Sum('fine_amount')
        )['total'] or 0 