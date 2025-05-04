from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

REPORT_TYPES = [
    ('violation', 'Violation Statistics'),
    ('revenue', 'Revenue Reports'),
    ('activity', 'User Activity'),
    ('education', 'Educational Analytics')
]

ROLES = [
    ('admin', 'Administrator'),
    ('supervisor', 'Supervisor'),
    ('enforcer', 'Enforcement Officer'),
    ('finance', 'Finance Staff'),
    ('adjudicator', 'Adjudicator'),
    ('educator', 'Educator')
]

class Report(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    type = models.CharField(max_length=20, choices=REPORT_TYPES)
    query_template = models.TextField(help_text="SQL query template or report definition")
    chart_enabled = models.BooleanField(default=False)
    chart_type = models.CharField(max_length=20, blank=True, null=True, choices=[
        ('bar', 'Bar Chart'),
        ('line', 'Line Chart'),
        ('pie', 'Pie Chart'),
        ('doughnut', 'Doughnut Chart')
    ])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['type', 'name']
    
class ReportPermission(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='permissions')
    role = models.CharField(max_length=20, choices=ROLES)
    
    def __str__(self):
        return f"{self.report.name} - {self.get_role_display()}"
    
    class Meta:
        unique_together = ['report', 'role']
    
class ReportSchedule(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='schedules')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='report_schedules')
    frequency = models.CharField(max_length=20, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ])
    next_run = models.DateTimeField()
    email_recipients = models.TextField(blank=True, help_text="Comma-separated list of email addresses")
    is_active = models.BooleanField(default=True)
    parameters = models.JSONField(default=dict, blank=True, help_text="Report parameters in JSON format")
    
    def __str__(self):
        return f"{self.report.name} - {self.frequency} - {self.user.username}"
    
    def save(self, *args, **kwargs):
        # Set next_run if it's not set
        if not self.next_run:
            self.next_run = timezone.now()
        super().save(*args, **kwargs)
    
class GeneratedReport(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='generated_reports')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='generated_reports')
    schedule = models.ForeignKey(ReportSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_reports')
    generated_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='reports/')
    parameters = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"{self.report.name} - {self.generated_at.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        ordering = ['-generated_at']
