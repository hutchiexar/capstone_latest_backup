from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Q
import json
import csv
from datetime import datetime
import xlsxwriter
from io import BytesIO

from .models import Violation, Violator

def is_admin_or_supervisor(user):
    """Check if user is admin or supervisor"""
    return user.is_staff or user.is_superuser or user.groups.filter(name='Supervisor').exists()

@login_required
@user_passes_test(is_admin_or_supervisor)
def adjudication_history(request):
    """
    View for displaying adjudication history
    """
    # Get all adjudicators for the filter dropdown
    adjudicators = User.objects.filter(
        adjudicated_violations__isnull=False
    ).distinct()
    
    # Get filter parameters
    adjudicator_id = request.GET.get('adjudicator')
    
    # Base query - all adjudicated violations
    violations = Violation.objects.filter(
        adjudicated_by__isnull=False
    ).select_related('violator', 'adjudicated_by').order_by('-adjudication_date')
    
    # Apply filters if provided
    if adjudicator_id:
        violations = violations.filter(adjudicated_by_id=adjudicator_id)
    
    context = {
        'violations': violations,
        'adjudicators': adjudicators,
        'selected_adjudicator': adjudicator_id,
    }
    
    return render(request, 'violations/adjudication_history.html', context)

@login_required
@user_passes_test(is_admin_or_supervisor)
def adjudication_detail(request, violation_id):
    """
    View for displaying detailed information about a specific adjudication
    """
    violation = get_object_or_404(Violation, id=violation_id)
    
    # Get original violation types
    original_violation_types = []
    if hasattr(violation, 'original_violation_types') and violation.original_violation_types:
        try:
            original_violation_types = json.loads(violation.original_violation_types)
        except (json.JSONDecodeError, TypeError):
            pass
    
    # Get current violation types
    current_violation_types = violation.get_violation_types()
    
    # Get removed violations and their reasons
    removed_violations = {}
    if hasattr(violation, 'removed_violations') and violation.removed_violations:
        try:
            raw_removed_violations = json.loads(violation.removed_violations)
            
            # Standardize the removed_violations structure 
            # Some entries might be strings, some might be objects with reason/amount
            for vtype, details in raw_removed_violations.items():
                if isinstance(details, dict):
                    # Already in the correct format
                    removed_violations[vtype] = details
                elif isinstance(details, str):
                    # Convert string to proper format
                    removed_violations[vtype] = {
                        'reason': details,
                        'amount': None
                    }
                else:
                    # Default fallback
                    removed_violations[vtype] = {
                        'reason': str(details),
                        'amount': None
                    }
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Error parsing removed_violations: {e}")
            pass
    
    # Create a set of actually removed violations by comparing original with current
    actually_removed_types = set()
    if original_violation_types:
        actually_removed_types = set(original_violation_types) - set(current_violation_types)
    
    # Check for any missing removed violations that aren't in the removed_violations dict
    for vtype in actually_removed_types:
        if vtype not in removed_violations:
            removed_violations[vtype] = {
                'reason': 'No reason provided',
                'amount': None
            }
    
    context = {
        'violation': violation,
        'original_violation_types': original_violation_types,
        'current_violation_types': current_violation_types,
        'removed_violations': removed_violations,
        'actually_removed_types': actually_removed_types,
    }
    
    return render(request, 'violations/adjudication_detail.html', context)

@login_required
@user_passes_test(is_admin_or_supervisor)
def export_adjudication_history(request):
    """
    Export adjudication history data to CSV or Excel
    """
    # Get filter parameters
    adjudicator_id = request.GET.get('adjudicator')
    export_format = request.GET.get('format', 'xlsx')
    
    # Base query - all adjudicated violations
    violations = Violation.objects.filter(
        adjudicated_by__isnull=False
    ).select_related('violator', 'adjudicated_by').order_by('-adjudication_date')
    
    # Apply filters if provided
    if adjudicator_id:
        violations = violations.filter(adjudicated_by_id=adjudicator_id)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if export_format == 'csv':
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="adjudication_history_{timestamp}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Violation ID', 'Violator', 'Original Amount', 'Final Amount', 
                         'Adjudicator', 'Adjudication Date', 'Notes'])
        
        for v in violations:
            writer.writerow([
                v.id,
                f"{v.violator.first_name} {v.violator.last_name}",
                v.original_fine_amount,
                v.fine_amount,
                v.adjudicated_by.get_full_name(),
                v.adjudication_date.strftime('%Y-%m-%d %H:%M'),
                v.adjudication_remarks
            ])
        
        return response
    else:
        # Create Excel file in memory
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Adjudication History')
        
        # Add header with formatting
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1})
        headers = ['Violation ID', 'Violator', 'Original Amount', 'Final Amount', 
                   'Adjudicator', 'Adjudication Date', 'Notes']
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Add data
        for row, v in enumerate(violations, start=1):
            worksheet.write(row, 0, v.id)
            worksheet.write(row, 1, f"{v.violator.first_name} {v.violator.last_name}")
            worksheet.write(row, 2, float(v.original_fine_amount) if v.original_fine_amount else 0.0)
            worksheet.write(row, 3, float(v.fine_amount) if v.fine_amount else 0.0)
            worksheet.write(row, 4, v.adjudicated_by.get_full_name())
            worksheet.write(row, 5, v.adjudication_date.strftime('%Y-%m-%d %H:%M'))
            worksheet.write(row, 6, v.adjudication_remarks or '')
        
        # Format columns
        worksheet.set_column(0, 0, 12)  # Violation ID
        worksheet.set_column(1, 1, 30)  # Violator
        worksheet.set_column(2, 3, 15)  # Amounts
        worksheet.set_column(4, 4, 25)  # Adjudicator
        worksheet.set_column(5, 5, 20)  # Date
        worksheet.set_column(6, 6, 50)  # Notes
        
        workbook.close()
        
        # Create response
        output.seek(0)
        response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="adjudication_history_{timestamp}.xlsx"'
        
        return response 