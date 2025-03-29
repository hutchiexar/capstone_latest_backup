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

@require_POST
@login_required
@csrf_exempt
def check_repeat_violator(request):
    """
    API endpoint to check if a violator has previous unsettled violations
    """
    try:
        license_number = request.POST.get('license_number', '')
        user_id = request.POST.get('user_id', '')
        source = request.POST.get('source', '')
        
        unsettled_violations = []
        
        # If a license number is provided, check violations for that license
        if license_number:
            unsettled_violations = Violation.objects.filter(
                violator__license_number=license_number,
                status__in=['PENDING', 'ADJUDICATED', 'APPROVED', 'OVERDUE']
            )
        
        # If a user ID is provided and it's a registered user, also check their violations
        if user_id and source == 'user':
            try:
                user_violations = Violation.objects.filter(
                    user_account_id=user_id,
                    status__in=['PENDING', 'ADJUDICATED', 'APPROVED', 'OVERDUE']
                )
                
                if user_violations.exists():
                    # Combine both sets if license violations were found
                    if unsettled_violations:
                        # Convert to lists to avoid queryset issues
                        combined_ids = set(list(unsettled_violations.values_list('id', flat=True)) + 
                                        list(user_violations.values_list('id', flat=True)))
                        unsettled_violations = Violation.objects.filter(id__in=combined_ids)
                    else:
                        unsettled_violations = user_violations
            except Exception as e:
                logger.error(f"Error checking user violations: {str(e)}")
        
        # Count unsettled violations
        unsettled_count = unsettled_violations.count()
        
        return JsonResponse({
            'is_repeat_violator': unsettled_count > 0,
            'unsettled_count': unsettled_count
        })
        
    except Exception as e:
        logger.error(f"Error checking for repeat violator: {str(e)}")
        return JsonResponse({
            'is_repeat_violator': False,
            'unsettled_count': 0,
            'error': str(e)
        }) 