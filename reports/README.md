# Reports Module

This module provides role-based reporting functionality for the Traffic Violation System.

## Features

- **Role-Based Access Control**: Reports are accessible based on user role (Admin, Supervisor, Enforcement Officer, Finance Staff, Adjudicator, Educator)
- **Multiple Report Types**: 
  - Violation Statistics
  - Revenue Reports
  - User Activity
  - Educational Analytics
- **Report Scheduling**: Reports can be scheduled to run automatically at different frequencies:
  - Daily
  - Weekly
  - Monthly
- **PDF Generation**: Reports can be exported to PDF format
- **Data Visualization**: Charts and graphs for better data analysis

## Implementation Details

### Database Models

- **Report**: Defines report metadata, query templates, and visualization options
- **ReportPermission**: Role-based access control for reports
- **ReportSchedule**: Scheduling configuration for reports
- **GeneratedReport**: Storage for generated PDF reports

### Views

- **reports_dashboard**: Main dashboard showing available reports by category
- **report_generator**: Form for generating reports with date range and export options
- **view_report**: View a previously generated report
- **schedule_report**: Schedule a report for periodic generation
- **cancel_schedule**: Cancel a scheduled report

### Templates

- **dashboard.html**: Main dashboard UI showing reports by category
- **generator.html**: Form for generating reports with date range selection
- **schedule.html**: Form for scheduling reports
- **pdf_template.html**: Template for PDF report generation

## Setup

1. Add the reports app to INSTALLED_APPS in settings.py
2. Run migrations: `python manage.py migrate reports`
3. Create sample reports: `python manage.py create_sample_reports`

## Dependencies

- Django
- xhtml2pdf (for PDF generation)
- Chart.js (for data visualization)

## To-Do

1. Implement real data queries instead of placeholder data
2. Add email notification integration for scheduled reports
3. Enhance chart generation with actual data visualization
4. Add report caching for better performance
5. Create management command to run scheduled reports
6. Implement role synchronization with user profiles
7. Add pagination for long reports
8. Create report templates for different view formats (print, mobile, etc.)
9. Add filtering options for reports
10. Implement export to Excel/CSV formats

## Installation

1. Ensure xhtml2pdf is installed: `pip install xhtml2pdf`
2. Run migrations: `python manage.py migrate reports`
3. Create sample reports: `python manage.py create_sample_reports`
4. Start the server: `python manage.py runserver` 