import json
import logging
import traceback
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from .models import Violation
from .views import log_activity, is_supervisor

logger = logging.getLogger(__name__)

def can_submit_violations(user):
    """Check if user has permission to submit violations for approval"""
    try:
        # Check if userprofile exists
        if not hasattr(user, 'userprofile'):
            logger.error(f"User {user.username} has no userprofile")
            return False
        
        # Check if role exists in userprofile
        if not hasattr(user.userprofile, 'role'):
            logger.error(f"User {user.username}'s userprofile has no role attribute")
            return False
        
        # Check role permissions
        return (user.userprofile.role in ['ADJUDICATOR', 'SUPERVISOR', 'ADMIN'])
    except Exception as e:
        logger.error(f"Error checking permissions for user {user.username}: {str(e)}")
        return False

@login_required
def submit_violations_for_approval(request):
    # Print debug information
    print(f"DEBUG: User {request.user.username} is attempting to submit violations for approval")
    print(f"DEBUG: User has roles: {getattr(request.user.userprofile, 'role', 'NO_ROLE_FOUND')}")
    
    # Check permissions manually instead of using decorator
    if not can_submit_violations(request.user):
        return JsonResponse({
            'status': 'error',
            'message': 'Permission denied: You do not have access to submit violations for approval'
        }, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
    
    try:
        # Parse request body as JSON
        data = json.loads(request.body)
        violations_to_submit = data.get('violations', [])
        
        logger.info(f"User {request.user.username} is submitting {len(violations_to_submit)} violations for approval")
        
        if not violations_to_submit:
            return JsonResponse({
                'status': 'error',
                'message': 'No violations provided for submission'
            })
        
        # Process each violation
        processed_count = 0
        errors = []
        
        for violation_data in violations_to_submit:
            citation_id_raw = violation_data.get('citation_id')
            
            try:
                # Try to parse citation ID as integer
                try:
                    citation_id = int(citation_id_raw)
                except (ValueError, TypeError):
                    logger.error(f"Invalid citation ID format: {citation_id_raw}")
                    errors.append(f"Invalid citation ID format: {citation_id_raw}")
                    continue
                
                # Debug information
                logger.debug(f"Processing citation ID: {citation_id} (raw: {citation_id_raw})")
                print(f"DEBUG: Processing citation ID: {citation_id} (raw: {citation_id_raw})")
                
                # Find the violation by ID
                logger.debug(f"Looking up violation with ID {citation_id}")
                violation = Violation.objects.get(id=citation_id)
                
                # Update the violation status to ADJUDICATED
                violation.status = 'ADJUDICATED'
                violation.adjudicated_by = request.user
                violation.adjudication_date = timezone.now()
                
                logger.debug(f"Saving violation {citation_id}")
                violation.save()
                
                # Log the activity
                try:
                    log_activity(
                        user=request.user,
                        action='Submitted for Approval',
                        details=f'Submitted Violation #{citation_id} for approval',
                        category='violation'
                    )
                except Exception as log_error:
                    logger.error(f"Error logging activity for violation {citation_id}: {str(log_error)}")
                    errors.append(f"Activity logging error for {citation_id}: {str(log_error)}")
                
                processed_count += 1
                
            except Violation.DoesNotExist:
                error_msg = f"Violation with ID {citation_id} not found during submission for approval"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
            except Exception as violation_error:
                error_msg = f"Error processing violation {citation_id}: {str(violation_error)}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
        
        # Return success response
        response_data = {
            'status': 'success',
            'message': f'Successfully submitted {processed_count} violation(s) for approval',
            'processed_count': processed_count
        }
        
        if errors:
            response_data['warnings'] = errors
            
        logger.info(f"Successfully processed {processed_count} violations for approval")
        return JsonResponse(response_data)
            
    except json.JSONDecodeError:
        error_msg = "Invalid JSON data in request"
        logger.error(error_msg)
        return JsonResponse({
            'status': 'error',
            'message': error_msg
        }, status=400)
    except Exception as e:
        error_msg = f"Error in submit_violations_for_approval: {str(e)}"
        logger.error(error_msg)
        # Log the full traceback for debugging
        logger.error(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=500)
