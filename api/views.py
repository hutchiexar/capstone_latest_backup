from django.http import JsonResponse
from django.contrib.auth.models import User
from django.db.models import Q, Value as V
from django.db.models.functions import Concat
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from traffic_violation_system.models import UserProfile, Violator, Violation
import logging

# Set up logger
logger = logging.getLogger(__name__)

@require_GET
@login_required
@csrf_exempt
def search_users(request):
    """
    API endpoint for searching users and violators by name, license number, or other fields.
    
    Query parameters:
    - q: Search query string (required)
    - search_by: Field to search by (optional, defaults to 'all')
    - limit: Maximum number of results to return (optional, defaults to 5)
    
    Returns:
    - JSON response with matched users and violators
    """
    try:
        query = request.GET.get('q', '').strip()
        search_by = request.GET.get('search_by', 'all')
        limit = int(request.GET.get('limit', 5))
        
        logger.debug(f"Search request - query: '{query}', search_by: '{search_by}', limit: {limit}")
        
        if not query:
            return JsonResponse({'results': []})
        
        results = []
        
        try:
            # Search in UserProfile model
            users = User.objects.select_related('userprofile').filter(is_active=True)
            
            # Apply filters based on search_by parameter
            if search_by == 'license':
                # Add explicit filter to exclude records with null or empty license numbers
                users = users.filter(
                    Q(userprofile__license_number__icontains=query) & 
                    ~Q(userprofile__license_number__exact='') & 
                    ~Q(userprofile__license_number__isnull=True)
                )
                logger.debug(f"Filtering users by license number: '{query}'")
            elif search_by == 'first_name':
                users = users.filter(first_name__icontains=query)
            elif search_by == 'last_name':
                users = users.filter(last_name__icontains=query)
            else:
                users = users.filter(
                    Q(first_name__icontains=query) | 
                    Q(last_name__icontains=query) | 
                    (Q(userprofile__license_number__icontains=query) & ~Q(userprofile__license_number__exact='') & ~Q(userprofile__license_number__isnull=True)) |
                    Q(userprofile__phone_number__icontains=query) |
                    Q(userprofile__contact_number__icontains=query)
                )
            
            # Add user results
            for user in users[:limit]:
                try:
                    # Check if profile exists
                    if not hasattr(user, 'userprofile'):
                        logger.warning(f"User {user.id} ({user.username}) has no userprofile")
                        continue
                        
                    profile = user.userprofile
                    
                    # Check if the user has a valid license
                    license_number = getattr(profile, 'license_number', '') or ''
                    has_license = bool(license_number) and license_number.strip() != ''
                    
                    results.append({
                        'id': user.id,
                        'first_name': user.first_name or '',
                        'last_name': user.last_name or '',
                        'source': 'user',
                        'license_number': license_number,
                        'phone_number': getattr(profile, 'contact_number', getattr(profile, 'phone_number', '')) or '',
                        'address': getattr(profile, 'address', '') or '',
                        'has_license': has_license
                    })
                except Exception as e:
                    logger.error(f"Error processing user {user.id}: {str(e)}")
                    # Continue processing other users even if this one fails
            
            logger.debug(f"Found {len(results)} user results for query '{query}'")
        except Exception as e:
            logger.error(f"Error searching users: {str(e)}")
        
        try:
            # If we need more results to reach the limit, search in Violator model
            if len(results) < limit:
                remaining_limit = limit - len(results)
                
                # Search in Violator model
                violators = Violator.objects.all()
                
                if search_by == 'license':
                    # Add explicit filter to exclude records with null or empty license numbers
                    violators = violators.filter(
                        Q(license_number__icontains=query) &
                        ~Q(license_number__exact='') &
                        ~Q(license_number__isnull=True)
                    )
                    logger.debug(f"Filtering violators by license number: '{query}'")
                elif search_by == 'first_name':
                    violators = violators.filter(first_name__icontains=query)
                elif search_by == 'last_name':
                    violators = violators.filter(last_name__icontains=query)
                else:
                    violators = violators.filter(
                        Q(first_name__icontains=query) | 
                        Q(last_name__icontains=query) | 
                        (Q(license_number__icontains=query) & ~Q(license_number__exact='') & ~Q(license_number__isnull=True)) |
                        Q(phone_number__icontains=query)
                    )
                
                # Add violator results
                violator_count = 0
                for violator in violators[:remaining_limit]:
                    try:
                        # Check if the violator has a valid license
                        license_number = violator.license_number or ''
                        has_license = bool(license_number) and license_number.strip() != ''
                        
                        results.append({
                            'id': f"v_{violator.id}",  # Prefix with 'v_' to distinguish from user IDs
                            'first_name': violator.first_name or '',
                            'last_name': violator.last_name or '',
                            'source': 'violator',
                            'license_number': license_number,
                            'phone_number': violator.phone_number or '',
                            'address': violator.address or '',
                            'has_license': has_license
                        })
                        violator_count += 1
                    except Exception as e:
                        logger.error(f"Error processing violator {getattr(violator, 'id', 'unknown')}: {str(e)}")
                        # Continue processing other violators even if this one fails
                
                logger.debug(f"Found {violator_count} violator results for query '{query}'")
        except Exception as e:
            logger.error(f"Error searching violators: {str(e)}")
        
        # Sort results by relevance (exact match first, then partial match)
        def sort_key(item):
            # Get values with fallback to empty string for None values
            first_name = item.get('first_name', '') or ''
            last_name = item.get('last_name', '') or ''
            license_number = item.get('license_number', '') or ''
            
            # Log potential issues for debugging
            if not isinstance(first_name, str):
                logger.warning(f"Non-string first_name detected: {type(first_name)} - {first_name}")
                first_name = str(first_name) if first_name is not None else ''
                
            if not isinstance(last_name, str):
                logger.warning(f"Non-string last_name detected: {type(last_name)} - {last_name}")
                last_name = str(last_name) if last_name is not None else ''
                
            if not isinstance(license_number, str):
                logger.warning(f"Non-string license_number detected: {type(license_number)} - {license_number}")
                license_number = str(license_number) if license_number is not None else ''
            
            # Convert query to lowercase once
            query_lower = query.lower()
            
            try:
                # Exact match in name or license gets highest priority
                if (first_name.lower() == query_lower or 
                    last_name.lower() == query_lower or 
                    license_number.lower() == query_lower):
                    return 0
                # Starts with gets second priority
                elif (first_name.lower().startswith(query_lower) or 
                      last_name.lower().startswith(query_lower) or 
                      license_number.lower().startswith(query_lower)):
                    return 1
                # Contains gets lowest priority
                else:
                    return 2
            except Exception as e:
                logger.error(f"Error in sort_key: {e} - Item values: first_name={first_name}, last_name={last_name}, license_number={license_number}")
                return 3  # Default to lowest priority on error
        
        results.sort(key=sort_key)
        
        logger.debug(f"Returning {len(results)} total results for query '{query}'")
        return JsonResponse({'results': results})
    
    except Exception as e:
        logger.error(f"Unhandled exception in search_users: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': 'An error occurred during the search',
            'message': str(e)
        }, status=500)

@csrf_exempt
def check_repeat_violator(request):
    """
    API endpoint to check if a violator has previous unsettled violations
    """
    try:
        # Get all identification parameters
        license_number = request.POST.get('license_number', '')
        user_id = request.POST.get('user_id', '')
        source = request.POST.get('source', '')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        # Use a set to track unique violation IDs
        violation_ids = set()
        
        # Check for violations using license number if provided
        if license_number:
            logger.debug(f"Checking violations by license: {license_number}")
            license_violations = Violation.objects.filter(
                violator__license_number=license_number,
                status__in=['PENDING', 'ADJUDICATED', 'APPROVED', 'OVERDUE']
            )
            # Add violation IDs to our set
            violation_ids.update(license_violations.values_list('id', flat=True))
        
        # Check for violations using user ID if provided for registered users
        if user_id and source == 'user':
            try:
                logger.debug(f"Checking violations by user ID: {user_id}")
                user_violations = Violation.objects.filter(
                    user_account_id=user_id,
                    status__in=['PENDING', 'ADJUDICATED', 'APPROVED', 'OVERDUE']
                )
                # Add violation IDs to our set
                violation_ids.update(user_violations.values_list('id', flat=True))
            except Exception as e:
                logger.error(f"Error checking user violations: {str(e)}")
        
        # Check for violations using name if provided
        if first_name and last_name:
            try:
                logger.debug(f"Checking violations by name: {first_name} {last_name}")
                name_violations = Violation.objects.filter(
                    violator__first_name__iexact=first_name,
                    violator__last_name__iexact=last_name,
                    status__in=['PENDING', 'ADJUDICATED', 'APPROVED', 'OVERDUE']
                )
                # Add violation IDs to our set
                violation_ids.update(name_violations.values_list('id', flat=True))
            except Exception as e:
                logger.error(f"Error checking name-based violations: {str(e)}")
        
        # Get all the unique violations from our collected IDs
        unsettled_count = len(violation_ids)
        violation_details = []
        
        if unsettled_count > 0:
            # Get the full details for the violations, using our unique IDs
            # Get most recent violations first, limited to 3
            latest_violations = Violation.objects.filter(
                id__in=violation_ids
            ).order_by('-violation_date')[:3]
            
            for violation in latest_violations:
                try:
                    violation_details.append({
                        'id': violation.id,
                        'date': violation.violation_date.strftime('%b %d, %Y') if violation.violation_date else 'Unknown',
                        'type': ', '.join(violation.violations.split(',')[:2]) if violation.violations else 'Unspecified',
                        'status': violation.status,
                        'fine_amount': str(violation.fine_amount) if violation.fine_amount else 'N/A'
                    })
                except Exception as e:
                    logger.error(f"Error processing violation detail: {str(e)}")
        
        return JsonResponse({
            'is_repeat_violator': unsettled_count > 0,
            'unsettled_count': unsettled_count,
            'violation_details': violation_details
        })
        
    except Exception as e:
        logger.error(f"Error checking for repeat violator: {str(e)}")
        return JsonResponse({
            'is_repeat_violator': False,
            'unsettled_count': 0,
            'violation_details': [],
            'error': str(e)
        })

@require_GET
@login_required
def get_violation_images(request, violation_id):
    """
    API endpoint to retrieve violation images for a specific violation
    
    Returns JSON with image URLs for:
    - Main image
    - Driver photo
    - Vehicle photo
    - Secondary photo (ID)
    """
    try:
        violation = Violation.objects.get(id=violation_id)
        
        # Check if user has permission to view this violation
        if not (request.user.is_staff or request.user.is_superuser or 
                violation.user_account == request.user or 
                (hasattr(request.user, 'userprofile') and 
                 request.user.userprofile.is_enforcer)):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        images = {
            'image': violation.image.url if violation.image else None,
            'driver_photo': violation.driver_photo.url if violation.driver_photo else None,
            'vehicle_photo': violation.vehicle_photo.url if violation.vehicle_photo else None,
            'secondary_photo': violation.secondary_photo.url if violation.secondary_photo else None,
        }
        
        return JsonResponse(images)
    except Violation.DoesNotExist:
        return JsonResponse({'error': 'Violation not found'}, status=404)
    except Exception as e:
        logger.error(f"Error retrieving violation images: {str(e)}")
        return JsonResponse({'error': 'An error occurred while retrieving images'}, status=500) 