from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Violation
from django.db.models import Sum
import logging

logger = logging.getLogger(__name__)

@login_required
def receipt_summary_view(request, violation_id):
    """
    View for displaying a receipt summary for a single violation payment
    """
    violation = get_object_or_404(Violation, id=violation_id)
    
    # Ensure the violation is paid
    if violation.status != 'PAID':
        messages.error(request, "Cannot generate receipt for unpaid violation")
        return redirect('payment_processing')
    
    # Create context for the template
    context = {
        'violation': violation,
        'payment': {
            'receipt_number': violation.receipt_number,
            'receipt_date': violation.receipt_date,
            'payment_amount': violation.payment_amount or violation.fine_amount,
            'processed_by': violation.processed_by
        }
    }
    
    logger.info(f"Generated receipt summary for violation #{violation_id}")
    return render(request, 'payments/receipt_summary_single.html', context)


@login_required
def batch_receipt_summary_view(request, violation_ids):
    """
    View for displaying a receipt summary for multiple violation payments
    """
    # Convert comma-separated string to list
    violation_id_list = violation_ids.split(',')
    
    # Get all violations
    violations = Violation.objects.filter(id__in=violation_id_list)
    
    # Ensure all violations are paid
    unpaid_violations = violations.exclude(status='PAID')
    if unpaid_violations.exists():
        messages.error(request, "Cannot generate receipt for unpaid violations")
        return redirect('payment_processing')
    
    # Extract common receipt information from the first violation
    first_violation = violations.first()
    if not first_violation:
        messages.error(request, "No valid violations found")
        return redirect('payment_processing')
        
    receipt_number = first_violation.receipt_number
    receipt_date = first_violation.receipt_date
    processed_by = first_violation.processed_by.get_full_name() if first_violation.processed_by else "System"
    
    # Calculate total amount
    total_amount = sum(v.payment_amount or v.fine_amount for v in violations)
    
    # Get violator name from the first violation
    violator_name = first_violation.violator.get_full_name() if first_violation.violator else "Unknown"
    
    # Collect all violation types
    all_violation_types = set()
    violation_data = []
    
    for v in violations:
        # Get violation types for this violation
        v_types = v.get_violation_types()
        for vt in v_types:
            all_violation_types.add(vt)
        
        # Add violation data
        violation_data.append({
            'id': v.id,
            'violation_types': v_types,
            'amount': v.payment_amount or v.fine_amount
        })
    
    # Create context for the template
    context = {
        'violations': violation_data,
        'violator_name': violator_name,
        'receipt_number': receipt_number,
        'receipt_date': receipt_date,
        'processed_by': processed_by,
        'violation_types': sorted(all_violation_types),
        'total_amount': total_amount
    }
    
    logger.info(f"Generated batch receipt summary for violations: {violation_ids}")
    return render(request, 'payments/receipt_summary_batch.html', context) 