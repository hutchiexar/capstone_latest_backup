from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from reports.models import Report, ReportPermission, REPORT_TYPES, ROLES

class Command(BaseCommand):
    help = 'Create sample reports for testing'

    def handle(self, *args, **options):
        # Create sample reports
        self.create_sample_reports()
        self.stdout.write(self.style.SUCCESS('Successfully created sample reports'))

    def create_sample_reports(self):
        # Create reports for each report type
        violation_reports = [
            {
                'name': 'Monthly Violation Summary',
                'description': 'Summary of violations recorded in the past month, grouped by violation type.',
                'type': 'violation',
                'query_template': 'SELECT violation_type, COUNT(*) as count FROM violations GROUP BY violation_type',
                'chart_enabled': True,
                'chart_type': 'bar',
                'roles': ['admin', 'supervisor', 'enforcer']
            },
            {
                'name': 'Violations by Location',
                'description': 'Analysis of violations by location to identify high-violation areas.',
                'type': 'violation',
                'query_template': 'SELECT location, COUNT(*) as count FROM violations GROUP BY location ORDER BY count DESC',
                'chart_enabled': True,
                'chart_type': 'pie',
                'roles': ['admin', 'supervisor']
            },
        ]

        revenue_reports = [
            {
                'name': 'Revenue Summary',
                'description': 'Summary of revenue collected from violations, grouped by payment method.',
                'type': 'revenue',
                'query_template': 'SELECT payment_method, SUM(amount) as total FROM payments GROUP BY payment_method',
                'chart_enabled': True,
                'chart_type': 'pie',
                'roles': ['admin', 'finance']
            },
            {
                'name': 'Outstanding Payments',
                'description': 'List of outstanding payments for violations that are past due.',
                'type': 'revenue',
                'query_template': 'SELECT * FROM violations WHERE status = "OVERDUE" AND payment_status = "UNPAID"',
                'chart_enabled': False,
                'chart_type': None,
                'roles': ['admin', 'finance', 'supervisor']
            },
        ]

        activity_reports = [
            {
                'name': 'User Activity Summary',
                'description': 'Summary of user activity in the system, including login times and actions performed.',
                'type': 'activity',
                'query_template': 'SELECT user_id, COUNT(*) as actions FROM user_activity GROUP BY user_id',
                'chart_enabled': True,
                'chart_type': 'bar',
                'roles': ['admin', 'supervisor']
            },
            {
                'name': 'Enforcement Officer Performance',
                'description': 'Performance metrics for enforcement officers, including number of violations recorded.',
                'type': 'activity',
                'query_template': 'SELECT user_id, COUNT(*) as violations FROM violations GROUP BY recorder_id',
                'chart_enabled': True,
                'chart_type': 'bar',
                'roles': ['admin', 'supervisor']
            },
        ]

        education_reports = [
            {
                'name': 'Educational Course Completion',
                'description': 'Completion rates for educational courses by topic.',
                'type': 'education',
                'query_template': 'SELECT course_id, COUNT(*) as completions FROM course_completions GROUP BY course_id',
                'chart_enabled': True,
                'chart_type': 'bar',
                'roles': ['admin', 'educator', 'supervisor']
            },
            {
                'name': 'Education Topic Performance',
                'description': 'Performance metrics for educational topics, including pass rates and completion times.',
                'type': 'education',
                'query_template': 'SELECT topic_id, AVG(score) as avg_score FROM topic_completions GROUP BY topic_id',
                'chart_enabled': True,
                'chart_type': 'line',
                'roles': ['admin', 'educator']
            },
        ]

        # Combine all reports
        all_reports = violation_reports + revenue_reports + activity_reports + education_reports

        # Create each report and its permissions
        for report_data in all_reports:
            report, created = Report.objects.get_or_create(
                name=report_data['name'],
                defaults={
                    'description': report_data['description'],
                    'type': report_data['type'],
                    'query_template': report_data['query_template'],
                    'chart_enabled': report_data['chart_enabled'],
                    'chart_type': report_data['chart_type'],
                }
            )

            if created:
                self.stdout.write(f'Created report: {report.name}')
            else:
                self.stdout.write(f'Report already exists: {report.name}')

            # Create permissions for this report
            for role in report_data['roles']:
                permission, p_created = ReportPermission.objects.get_or_create(
                    report=report,
                    role=role
                )
                if p_created:
                    self.stdout.write(f'  Added permission for role: {role}')

        # Ensure we have some user groups for testing
        for role_code, role_name in ROLES:
            group, created = Group.objects.get_or_create(name=role_name)
            if created:
                self.stdout.write(f'Created group: {role_name}') 