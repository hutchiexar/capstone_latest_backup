from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib.auth.models import User

import io
import os
from datetime import timedelta

from reports.models import ReportSchedule
from reports.views import generate_report_data, generate_pdf

class Command(BaseCommand):
    help = 'Run scheduled reports that are due for execution'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force run all scheduled reports regardless of next_run date',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        now = timezone.now()
        
        # Get active schedules
        if force:
            self.stdout.write(self.style.WARNING('Force running all scheduled reports'))
            schedules = ReportSchedule.objects.filter(is_active=True)
        else:
            self.stdout.write('Running scheduled reports due for execution')
            schedules = ReportSchedule.objects.filter(is_active=True, next_run__lte=now)
        
        self.stdout.write(f'Found {schedules.count()} scheduled reports to run')
        
        # Process each schedule
        for schedule in schedules:
            self.process_schedule(schedule, now)
            
        self.stdout.write(self.style.SUCCESS('Successfully processed scheduled reports'))

    def process_schedule(self, schedule, now):
        self.stdout.write(f'Processing scheduled report: {schedule.report.name} for {schedule.user.username}')
        
        try:
            # Generate report data
            report_data = generate_report_data(schedule.report, schedule.parameters)
            
            # Generate PDF
            pdf_file = generate_pdf(schedule.report, report_data, schedule.parameters)
            
            # Save generated report
            filename = f"report_{schedule.report.id}_{now.strftime('%Y%m%d%H%M%S')}.pdf"
            generated_report = schedule.report.generated_reports.create(
                user=schedule.user,
                schedule=schedule,
                parameters=schedule.parameters
            )
            generated_report.pdf_file.save(filename, pdf_file)
            
            self.stdout.write(self.style.SUCCESS(f'Generated report #{generated_report.id}'))
            
            # Send email if recipients are specified
            if schedule.email_recipients:
                self.send_email_report(schedule, generated_report, pdf_file)
            
            # Update the next run time based on frequency
            self.update_next_run(schedule)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error processing report: {str(e)}'))

    def send_email_report(self, schedule, generated_report, pdf_file):
        """Send the report via email to recipients."""
        recipients = [email.strip() for email in schedule.email_recipients.split(',') if email.strip()]
        
        if not recipients:
            self.stdout.write('No valid email recipients found, skipping email')
            return
        
        try:
            email = EmailMessage(
                subject=f'Scheduled Report: {schedule.report.name}',
                body=f"""
Hello,

Your scheduled report "{schedule.report.name}" has been generated.
Please find the attached PDF report.

This is an automated message.
                """,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                to=recipients
            )
            
            # Attach the PDF
            pdf_file.seek(0)
            email.attach(
                filename=os.path.basename(generated_report.pdf_file.name),
                content=pdf_file.read(),
                mimetype='application/pdf'
            )
            
            email.send()
            self.stdout.write(self.style.SUCCESS(f'Email sent to {", ".join(recipients)}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error sending email: {str(e)}'))

    def update_next_run(self, schedule):
        """Update the next run time based on frequency."""
        now = timezone.now()
        
        if schedule.frequency == 'daily':
            next_run = now + timedelta(days=1)
        elif schedule.frequency == 'weekly':
            next_run = now + timedelta(days=7)
        else:  # monthly
            # Add one month (approximately)
            next_run = now + timedelta(days=30)
        
        schedule.next_run = next_run
        schedule.save()
        self.stdout.write(f'Updated next run to {next_run}') 