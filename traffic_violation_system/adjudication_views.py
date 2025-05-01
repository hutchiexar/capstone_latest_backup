from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_protect
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib import messages
import json
import logging

from .models import Violation, Violator, ActivityLog, ViolationType

logger = logging.getLogger(__name__)

def is_adjudicator(user):
    """Check if the user is an adjudicator or admin"""
    return user.is_staff or user.groups.filter(name='Adjudicator').exists() or user.is_superuser


@login_required
@user_passes_test(is_adjudicator)
@csrf_protect
def adjudication_page(request, violator_id):
    """
    View for the adjudication page that loads violator data and associated violations.
    
    Args:
        request: HTTP request object
        violator_id: ID of the violator whose violations need to be adjudicated
        
    Returns:
        Rendered adjudication page template with context
    """
    # Get the violator
    violator = get_object_or_404(Violator, id=violator_id)
    
    # Build query for pending violations using Q objects to avoid nested unions
    # This is compatible with older MySQL versions
    # Include REJECTED status to allow re-adjudication
    query = Q(status__in=['PENDING', 'REJECTED'])
    query &= (
        Q(violator=violator) |  # Direct matches
        (Q(violator__first_name__iexact=violator.first_name) & 
         Q(violator__last_name__iexact=violator.last_name))
    )
    
    # Add license number condition if available
    if violator.license_number:
        query |= Q(violator__license_number=violator.license_number, status__in=['PENDING', 'REJECTED'])
    
    # Get all pending and rejected violations in a single query
    pending_violations = Violation.objects.filter(query).order_by('-violation_date').distinct()
    
    # Build query for adjudicated violations
    adj_query = Q(status__in=['ADJUDICATED', 'APPROVED'])
    adj_query &= (
        Q(violator=violator) |  # Direct matches
        (Q(violator__first_name__iexact=violator.first_name) & 
         Q(violator__last_name__iexact=violator.last_name))
    )
    
    # Add license number condition if available
    if violator.license_number:
        adj_query |= Q(violator__license_number=violator.license_number, status__in=['ADJUDICATED', 'APPROVED'])
    
    # Get all adjudicated violations in a single query
    adjudicated_violations = Violation.objects.filter(adj_query).order_by('-adjudication_date').distinct()
    
    # Log what we found for debugging
    logger.info(f"Found {pending_violations.count()} pending/rejected violations for violator {violator.id} - {violator.get_full_name()}")
    logger.info(f"Found {adjudicated_violations.count()} adjudicated violations for violator {violator.id}")
    
    # Get all violation types and their amounts from the database
    violation_types_data = {}
    for vt in ViolationType.objects.filter(is_active=True):
        violation_types_data[vt.name] = float(vt.amount)
    
    logger.info(f"Retrieved {len(violation_types_data)} violation types with amounts from database")
    
    # Prepare violations data for the template
    pending_violations_data = []
    for violation in pending_violations:
        # Get violation types
        violation_types = violation.get_violation_types()
        
        # Create a map of violation types to their database amounts
        violation_type_amounts = {}
        for vtype in violation_types:
            if vtype in violation_types_data:
                violation_type_amounts[vtype] = violation_types_data[vtype]
        
        # Prepare data structure
        violation_data = {
            'id': violation.id,
            'ticket_id': violation.id,  # Using ID as ticket_id since there's no separate ticket_id field
            'violation_date': violation.violation_date,
            'fine_amount': violation.fine_amount,
            'violation_types': json.dumps(violation_types),
            'violation_type_amounts': json.dumps(violation_type_amounts),
            'location': violation.location,
            'status': violation.status,
            'violator_name': f"{violation.violator.first_name} {violation.violator.last_name}",
            'is_exact_match': violation.violator.id == violator.id,
            'is_rejected': violation.status == 'REJECTED',
            'rejection_reason': violation.rejection_reason if hasattr(violation, 'rejection_reason') else None,
        }
        pending_violations_data.append(violation_data)
    
    # Prepare adjudicated violations data
    adjudicated_violations_data = []
    for violation in adjudicated_violations:
        violation_data = {
            'id': violation.id,
            'ticket_id': violation.id,
            'adjudication_date': violation.adjudication_date,
            'fine_amount': violation.fine_amount,
            'violation_types': json.dumps(violation.get_violation_types()),
            'adjudication_remarks': violation.adjudication_remarks,
            'status': violation.status,
            'adjudicated_by': violation.adjudicated_by.get_full_name() if violation.adjudicated_by else 'Unknown',
            'violator_name': f"{violation.violator.first_name} {violation.violator.last_name}",
            'is_exact_match': violation.violator.id == violator.id,
        }
        adjudicated_violations_data.append(violation_data)
    
    # Prepare context for template
    context = {
        'violator': violator,
        'violations': pending_violations_data,
        'violations_count': len(pending_violations_data),
        'adjudicated_violations': adjudicated_violations_data,
        'adjudicated_count': len(adjudicated_violations_data),
        'violation_types_amounts': violation_types_data,  # Pass all violation type amounts to the template
    }
    
    return render(request, 'violations/adjudication_page.html', context)


@login_required
@user_passes_test(is_adjudicator)
@csrf_protect
def adjudicate_ticket(request):
    """
    Process a single ticket adjudication.
    
    Args:
        request: HTTP request object containing POST data
        
    Returns:
        JsonResponse with status of the adjudication
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method. POST expected.")
    
    try:
        # Get POST data
        data = json.loads(request.body)
        ticket_id = data.get('ticket_id')
        violation_types = data.get('violation_types', [])
        penalty_amount = data.get('penalty_amount', 0)
        notes = data.get('notes', '')
        
        # Input validation
        if not ticket_id:
            return JsonResponse({'status': 'error', 'message': 'Ticket ID is required'}, status=400)
        
        # Get the violation
        violation = get_object_or_404(Violation, id=ticket_id)
        
        # Check if already adjudicated - allow REJECTED status to be re-adjudicated
        if violation.status in ['ADJUDICATED', 'APPROVED']:
            return JsonResponse({
                'status': 'error', 
                'message': f'This ticket has already been adjudicated (Status: {violation.status})'
            }, status=400)
        
        # Get original violation types
        original_types = violation.get_violation_types()
        
        # Determine removed violations
        removed_violations = [v for v in original_types if v not in violation_types]
        
        # Save the original violation types if this is the first adjudication (not a re-adjudication)
        if not violation.original_violation_types:
            violation.original_violation_types = json.dumps(original_types)
        
        # Save the original fine amount if this is the first adjudication (not a re-adjudication)
        if violation.original_fine_amount is None:
            violation.original_fine_amount = violation.fine_amount
        
        # Record previous status for logging
        previous_status = violation.status
        
        # Update the violation
        violation.status = 'ADJUDICATED'
        violation.fine_amount = float(penalty_amount)
        violation.adjudication_remarks = notes
        violation.adjudicated_by = request.user
        violation.adjudication_date = timezone.now()
        
        # Clear rejection reason if this was previously rejected
        if hasattr(violation, 'rejection_reason') and previous_status == 'REJECTED':
            violation.rejection_reason = None
        
        # Update violation types if any were removed
        if removed_violations:
            violation.set_violation_types(violation_types)
            
        # Save the updated violation
        violation.save()
        
        # Log the adjudication
        log_details = f"Adjudicated violation #{violation.id} - Amount: ₱{penalty_amount}, "
        if previous_status == 'REJECTED':
            log_details += f"Re-adjudicated from REJECTED status, "
            
        # Special handling for empty violation types
        if not violation_types:
            log_details += "NO VIOLATIONS SELECTED, "
            
        log_details += f"Removed: {', '.join(removed_violations) if removed_violations else 'None'}"
        
        ActivityLog.objects.create(
            user=request.user,
            action="ADJUDICATION",
            details=log_details,
            category="violation"
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Ticket successfully adjudicated',
            'ticket_id': ticket_id,
            'adjudication_date': violation.adjudication_date.isoformat(),
            'adjudicated_by': request.user.get_full_name(),
            'was_rejected': previous_status == 'REJECTED'
        })
        
    except Violation.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Violation not found'}, status=404)
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': f'Invalid data format: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f"Error in adjudicate_ticket: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@user_passes_test(is_adjudicator)
@csrf_protect
def submit_all_adjudications(request, violator_id):
    """
    Process final submission of all adjudications for a violator.
    
    Args:
        request: HTTP request object
        violator_id: ID of the violator whose adjudications are being finalized
        
    Returns:
        JSON response or redirect depending on request type
    """
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method. POST expected.")
    
    try:
        # Get the violator
        violator = get_object_or_404(Violator, id=violator_id)
        
        # Build query for pending violations with Q objects
        query = Q(status__in=['PENDING', 'REJECTED'])
        query &= (
            Q(violator=violator) | 
            (Q(violator__first_name__iexact=violator.first_name) & 
             Q(violator__last_name__iexact=violator.last_name))
        )
        
        # Add license number condition if available
        if violator.license_number:
            query |= Q(violator__license_number=violator.license_number, status__in=['PENDING', 'REJECTED'])
        
        # Check if there are any pending or rejected violations
        pending_count = Violation.objects.filter(query).distinct().count()
        
        if pending_count > 0:
            error_message = f"There are still {pending_count} pending or rejected violations. Please adjudicate all violations before submitting."
            
            # Return error response based on request type
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error_message}, status=400)
            else:
                messages.error(request, error_message)
                return redirect('adjudication_page', violator_id=violator_id)
        
        # Build query for adjudicated violations
        adj_query = Q(status='ADJUDICATED')
        adj_query &= (
            Q(violator=violator) | 
            (Q(violator__first_name__iexact=violator.first_name) & 
             Q(violator__last_name__iexact=violator.last_name))
        )
        
        # Add license number condition if available
        if violator.license_number:
            adj_query |= Q(violator__license_number=violator.license_number, status='ADJUDICATED')
        
        # Get all adjudicated violations for this violator
        adjudicated_violations = Violation.objects.filter(adj_query).distinct()
        
        # Count how many were processed
        processed_count = adjudicated_violations.count()
        
        if processed_count == 0:
            error_message = "No adjudications to submit."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error_message}, status=400)
            else:
                messages.error(request, error_message)
                return redirect('adjudication_page', violator_id=violator_id)
        
        # Log the batch submission
        ActivityLog.objects.create(
            user=request.user,
            action="BATCH_ADJUDICATION_SUBMISSION",
            details=f"Submitted {processed_count} adjudications for violator {violator.get_full_name()}",
            category="violation"
        )
        
        success_message = f"Successfully submitted {processed_count} adjudications for {violator.get_full_name()}"
        
        # Return success response based on request type
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success', 
                'message': success_message,
                'processed_count': processed_count
            })
        else:
            messages.success(request, success_message)
            return redirect('adjudication_list')
            
    except Exception as e:
        logger.error(f"Error in submit_all_adjudications: {str(e)}")
        error_message = str(e)
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': error_message}, status=500)
        else:
            messages.error(request, f"Error: {error_message}")
            return redirect('adjudication_page', violator_id=violator_id)


@login_required
@user_passes_test(is_adjudicator)
def get_violation_data(request, violation_id):
    """
    Get detailed data for a specific violation.
    
    Args:
        request: HTTP request object
        violation_id: ID of the violation to retrieve
        
    Returns:
        JSON response with violation data
    """
    try:
        violation = get_object_or_404(Violation, id=violation_id)
        
        # Prepare the response data
        violation_data = {
            'id': violation.id,
            'ticket_id': violation.id,
            'violation_date': violation.violation_date.isoformat(),
            'fine_amount': str(violation.fine_amount),
            'violation_types': violation.get_violation_types(),
            'location': violation.location,
            'status': violation.status,
            'violator': {
                'id': violation.violator.id,
                'name': violation.violator.get_full_name(),
                'license_number': violation.violator.license_number
            }
        }
        
        # Add rejection reason if it exists and violation was rejected
        if violation.status == 'REJECTED' and hasattr(violation, 'rejection_reason'):
            violation_data['rejection_reason'] = violation.rejection_reason
        
        return JsonResponse({'status': 'success', 'data': violation_data})
        
    except Violation.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Violation not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in get_violation_data: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@user_passes_test(is_adjudicator)
def redirect_to_adjudication_page(request, violation_id):
    """
    Redirect from the old adjudication interface to the new one.
    
    Args:
        request: HTTP request object
        violation_id: ID of the violation to redirect
        
    Returns:
        Redirect to the new adjudication page
    """
    # Get the violation
    violation = get_object_or_404(Violation, id=violation_id)
    
    # Get the violator ID
    violator_id = violation.violator.id
    
    # Redirect to the new adjudication page
    return redirect('adjudication_page', violator_id=violator_id) 