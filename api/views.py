from django.http import JsonResponse
from django.contrib.auth.models import User
from django.db.models import Q, Value as V
from django.db.models.functions import Concat
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from traffic_violation_system.models import UserProfile, Violator, Violation, Driver
import logging
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.core.paginator import Paginator

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

@require_GET
@login_required
def search_driver_by_pd(request, pd_number):
    """
    API endpoint to search for driver by PD number and return their violation history.
    This function is only accessible to operators.
    
    URL parameters:
    - pd_number: The PD number of the driver to search for
    
    Query parameters:
    - include_all: If 'true', include violations from drivers who don't have user accounts
    
    Returns:
    - JSON response with driver information and violations categorized as regular and NCAP
    """
    try:
        # Check if the user has a userprofile
        if not hasattr(request.user, 'userprofile'):
            return JsonResponse({
                'error': 'User profile not found',
                'message': 'Your user account is missing a profile'
            }, status=400)
            
        # Check if the is_operator attribute exists and if the user is an operator
        if not getattr(request.user.userprofile, 'is_operator', False):
            return JsonResponse({
                'error': 'Permission denied',
                'message': 'Only operators can search for driver violations'
            }, status=403)
        
        # Get the include_all parameter
        include_all = request.GET.get('include_all', 'false').lower() == 'true'
        logger.debug(f"Searching for driver with PD number: {pd_number}, include_all: {include_all}")
        
        # Get driver by PD number
        try:
            # Try both new_pd_number and old_pd_number fields
            driver = None
            
            # First, try to find exact matches
            try:
                driver = Driver.objects.filter(
                    Q(new_pd_number__iexact=pd_number) | Q(old_pd_number__iexact=pd_number)
                ).first()
            except Exception as e:
                logger.error(f"Error during exact PD number query: {str(e)}")
            
            # If exact match fails, try contains search
            if not driver:
                try:
                    driver = Driver.objects.filter(
                        Q(new_pd_number__icontains=pd_number) | Q(old_pd_number__icontains=pd_number)
                    ).first()
                except Exception as e:
                    logger.error(f"Error during contains PD number query: {str(e)}")
            
            if not driver:
                return JsonResponse({
                    'error': 'Driver not found',
                    'message': f'No driver found with PD number: {pd_number}'
                }, status=404)
                
            logger.debug(f"Found driver: {driver.first_name} {driver.last_name} (ID: {driver.id})")
            
        except Exception as e:
            logger.error(f"Error finding driver by PD number: {str(e)}", exc_info=True)
            return JsonResponse({
                'error': 'Error finding driver',
                'message': str(e)
            }, status=500)
        
        # Get all violations for this driver
        regular_violations = []
        ncap_violations = []
        all_found_violations = []
        search_debug_info = {}
        
        try:
            # Check if the driver has a valid name
            driver_id = driver.id
            driver_first_name = getattr(driver, 'first_name', '')
            driver_last_name = getattr(driver, 'last_name', '')
            driver_new_pd = getattr(driver, 'new_pd_number', '') or ''
            driver_old_pd = getattr(driver, 'old_pd_number', '') or ''
            driver_license = getattr(driver, 'license_number', '') or ''
            
            search_debug_info = {
                'driver_id': driver_id,
                'driver_name': f"{driver_first_name} {driver_last_name}",
                'pd_numbers': [driver_new_pd, driver_old_pd],
                'license_number': driver_license,
                'search_strategies_used': [],
                'include_all': include_all
            }
            
            logger.debug(f"Searching violations for driver ID: {driver_id}, PD numbers: {driver_new_pd}, {driver_old_pd}")
            
            # Try multiple search strategies
            
            # Strategy 1: Search by violator's PD number (direct field)
            try:
                if hasattr(Violator, 'pd_number'):
                    pd_violations = []
                    # Try new PD number
                    if driver_new_pd:
                        new_pd_violations = list(Violation.objects.filter(
                            violator__pd_number__iexact=driver_new_pd
                        ).order_by('-violation_date').select_related('violator'))
                        pd_violations.extend(new_pd_violations)
                        search_debug_info['search_strategies_used'].append(f"violator__pd_number={driver_new_pd} (found {len(new_pd_violations)})")
                    
                    # Try old PD number
                    if driver_old_pd:
                        old_pd_violations = list(Violation.objects.filter(
                            violator__pd_number__iexact=driver_old_pd
                        ).order_by('-violation_date').select_related('violator'))
                        pd_violations.extend(old_pd_violations)
                        search_debug_info['search_strategies_used'].append(f"violator__pd_number={driver_old_pd} (found {len(old_pd_violations)})")
                        
                    if pd_violations:
                        logger.debug(f"Found {len(pd_violations)} violations by PD number")
                        all_found_violations.extend(pd_violations)
            except Exception as e:
                logger.error(f"Error in strategy 1 (PD number search): {str(e)}")
                search_debug_info['search_strategies_used'].append(f"violator__pd_number ERROR: {str(e)}")
            
            # Strategy 2: Search by license number
            try:
                if driver_license and hasattr(Violator, 'license_number'):
                    license_violations = list(Violation.objects.filter(
                        violator__license_number__iexact=driver_license
                    ).order_by('-violation_date').select_related('violator'))
                    
                    if license_violations:
                        logger.debug(f"Found {len(license_violations)} violations by license number")
                        all_found_violations.extend(license_violations)
                        search_debug_info['search_strategies_used'].append(f"violator__license_number={driver_license} (found {len(license_violations)})")
            except Exception as e:
                logger.error(f"Error in strategy 2 (license number search): {str(e)}")
                search_debug_info['search_strategies_used'].append(f"violator__license_number ERROR: {str(e)}")
            
            # Strategy 3: Search by name (if both first and last name are present)
            try:
                if driver_first_name and driver_last_name:
                    name_violations = list(Violation.objects.filter(
                        violator__first_name__iexact=driver_first_name,
                        violator__last_name__iexact=driver_last_name
                    ).order_by('-violation_date').select_related('violator'))
                    
                    if name_violations:
                        logger.debug(f"Found {len(name_violations)} violations by name")
                        all_found_violations.extend(name_violations)
                        search_debug_info['search_strategies_used'].append(f"violator name={driver_first_name} {driver_last_name} (found {len(name_violations)})")
            except Exception as e:
                logger.error(f"Error in strategy 3 (name search): {str(e)}")
                search_debug_info['search_strategies_used'].append(f"violator name ERROR: {str(e)}")
            
            # Strategy 4: If driver has a direct relation to violations
            try:
                if hasattr(Driver, 'violations'):
                    driver_direct_violations = list(driver.violations.all().order_by('-violation_date'))
                    if driver_direct_violations:
                        logger.debug(f"Found {len(driver_direct_violations)} violations by direct relation")
                        all_found_violations.extend(driver_direct_violations)
                        search_debug_info['search_strategies_used'].append(f"driver.violations (found {len(driver_direct_violations)})")
            except Exception as e:
                logger.error(f"Error in strategy 4 (direct relation): {str(e)}")
                search_debug_info['search_strategies_used'].append(f"driver.violations ERROR: {str(e)}")
            
            # Strategy 5: Try reverse relation from Violator to Driver
            try:
                if hasattr(Violator, 'driver'):
                    driver_violator_violations = list(Violation.objects.filter(
                        violator__driver=driver
                    ).order_by('-violation_date').select_related('violator'))
                    
                    if driver_violator_violations:
                        logger.debug(f"Found {len(driver_violator_violations)} violations by driver-violator relation")
                        all_found_violations.extend(driver_violator_violations)
                        search_debug_info['search_strategies_used'].append(f"violator__driver={driver_id} (found {len(driver_violator_violations)})")
            except Exception as e:
                logger.error(f"Error in strategy 5 (violator-driver relation): {str(e)}")
                search_debug_info['search_strategies_used'].append(f"violator__driver ERROR: {str(e)}")
            
            # Strategy 6: Try searching by driver directly (if Violation has driver field)
            try:
                if hasattr(Violation, 'driver'):
                    direct_driver_violations = list(Violation.objects.filter(
                        driver=driver
                    ).order_by('-violation_date'))
                    
                    if direct_driver_violations:
                        logger.debug(f"Found {len(direct_driver_violations)} violations by direct driver field")
                        all_found_violations.extend(direct_driver_violations)
                        search_debug_info['search_strategies_used'].append(f"violation.driver={driver_id} (found {len(direct_driver_violations)})")
            except Exception as e:
                logger.error(f"Error in strategy 6 (direct driver field): {str(e)}")
                search_debug_info['search_strategies_used'].append(f"violation.driver ERROR: {str(e)}")
                
            # Strategy 7: Search by PD number directly on the Violation model
            try:
                pd_field_violations = []
                # Try pd_number field
                if hasattr(Violation, 'pd_number'):
                    # Try with new PD number
                    if driver_new_pd:
                        new_pd_direct_violations = list(Violation.objects.filter(
                            pd_number__iexact=driver_new_pd
                        ).order_by('-violation_date'))
                        pd_field_violations.extend(new_pd_direct_violations)
                        search_debug_info['search_strategies_used'].append(f"pd_number={driver_new_pd} (found {len(new_pd_direct_violations)})")
                    
                    # Try with old PD number
                    if driver_old_pd:
                        old_pd_direct_violations = list(Violation.objects.filter(
                            pd_number__iexact=driver_old_pd
                        ).order_by('-violation_date'))
                        pd_field_violations.extend(old_pd_direct_violations)
                        search_debug_info['search_strategies_used'].append(f"pd_number={driver_old_pd} (found {len(old_pd_direct_violations)})")
                
                if pd_field_violations:
                    logger.debug(f"Found {len(pd_field_violations)} violations by direct PD number field")
                    all_found_violations.extend(pd_field_violations)
            except Exception as e:
                logger.error(f"Error in strategy 7 (direct PD number field): {str(e)}")
                search_debug_info['search_strategies_used'].append(f"direct pd_number ERROR: {str(e)}")
            
            # Debug count of total violations found
            search_debug_info['total_found'] = len(all_found_violations)
            
            # Remove duplicates by creating a dict with violation ID as key
            unique_violations = {}
            for violation in all_found_violations:
                if violation.id not in unique_violations:
                    unique_violations[violation.id] = violation
                    
            all_violations = list(unique_violations.values())
            logger.debug(f"Total unique violations found: {len(all_violations)}")
            search_debug_info['unique_violations'] = len(all_violations)
            
            # Process violations 
            for violation in all_violations:
                try:
                    # Skip violations without user_account if include_all is False
                    user_account = getattr(violation, 'user_account', None)
                    if not include_all and user_account is None:
                        logger.debug(f"Skipping violation {violation.id} because it has no user account and include_all is False")
                        continue
                    
                    # Get violation type using multiple possible field names
                    violation_type = None
                    for field_name in ['violation_type', 'violations', 'violation']:
                        if hasattr(violation, field_name):
                            field_value = getattr(violation, field_name)
                            if field_value:
                                violation_type = field_value
                                break
                    
                    # If we still don't have a violation type, try getting it from related models
                    if not violation_type and hasattr(violation, 'violation_types'):
                        related_types = violation.violation_types.all()
                        if related_types:
                            violation_type = ", ".join([vt.name for vt in related_types])
                    
                    # Fallback
                    if not violation_type:
                        violation_type = "Unknown Violation"
                    
                    # Build violation data
                    violation_data = {
                        'id': violation.id,
                        'violation_date': violation.violation_date,
                        'violation_type': violation_type,
                        'location': getattr(violation, 'location', 'Unknown'),
                        'status': getattr(violation, 'status', 'Unknown'),
                        'fine_amount': getattr(violation, 'fine_amount', 0),
                        'plate_number': getattr(violation, 'plate_number', ''),
                        'potpot_number': getattr(violation, 'potpot_number', ''),
                    }
                    
                    # Check different ways to identify NCAP violations
                    is_ncap = False
                    
                    # Check direct field
                    if hasattr(violation, 'is_ncap'):
                        is_ncap = getattr(violation, 'is_ncap', False)
                    
                    # Check violation type for camera-related keywords
                    if not is_ncap and violation_type:
                        # Keywords that indicate camera-captured violations
                        camera_keywords = ['camera', 'ncap', 'photo', 'video', 'cctv']
                        
                        # Common camera-captured violations
                        common_ncap_violations = [
                            'helmet', 'no helmet', 
                            'red light', 'traffic light', 
                            'stop sign', 'stop light',
                            'speeding', 'speed limit',
                            'seatbelt', 'no seatbelt',
                            'lane violation'
                        ]
                        
                        # Check for camera keywords
                        if any(keyword.lower() in violation_type.lower() for keyword in camera_keywords):
                            is_ncap = True
                        
                        # Check for common NCAP violation types
                        if any(violation_phrase.lower() in violation_type.lower() for violation_phrase in common_ncap_violations):
                            is_ncap = True
                            logger.debug(f"Identified as NCAP violation based on common violation type: {violation_type}")
                    
                    # Check violation category if it exists
                    if not is_ncap and hasattr(violation, 'category'):
                        category = getattr(violation, 'category', '').lower()
                        if 'camera' in category or 'ncap' in category:
                            is_ncap = True
                    
                    if is_ncap:
                        ncap_violations.append(violation_data)
                    else:
                        regular_violations.append(violation_data)
                except Exception as e:
                    logger.error(f"Error processing violation ID {violation.id}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error getting violations: {str(e)}", exc_info=True)
            search_debug_info['error'] = str(e)
        
        # Prepare driver information with safer attribute access
        try:
            driver_data = {
                'id': driver.id,
                'first_name': getattr(driver, 'first_name', ''),
                'last_name': getattr(driver, 'last_name', ''),
                'middle_initial': getattr(driver, 'middle_initial', ''),
                'license_number': getattr(driver, 'license_number', ''),
                'pd_number': driver_new_pd or driver_old_pd or '',
                'address': getattr(driver, 'address', ''),
                'contact_number': getattr(driver, 'contact_number', ''),
                'user_account': False,  # Default to false since we're looking at drivers without accounts
            }
            
            # Check if this driver has a user account (via lookup by license number)
            try:
                if driver.license_number and User.objects.filter(userprofile__license_number=driver.license_number).exists():
                    driver_data['user_account'] = True
                    logger.debug(f"Driver has a User account linked via license number")
            except Exception as e:
                logger.error(f"Error checking for user account: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error preparing driver data: {str(e)}", exc_info=True)
            driver_data = {
                'id': driver.id,
                'first_name': 'Error retrieving data',
                'last_name': '',
            }
        
        # Return the response
        logger.debug(f"Returning response with {len(regular_violations)} regular violations and {len(ncap_violations)} NCAP violations")
        return JsonResponse({
            'driver': driver_data,
            'regular_violations': regular_violations,
            'ncap_violations': ncap_violations,
            'debug_info': search_debug_info
        })
        
    except Exception as e:
        logger.error(f"Error in search_driver_by_pd: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': 'An error occurred during the search',
            'message': str(e)
        }, status=500)

@csrf_exempt
def check_registration_violations(request):
    """
    API endpoint to check for violations that should be linked to a new user during registration.
    Searches for violations that match the license number, first name, or last name provided,
    and are not yet claimed by any user.
    
    POST parameters:
    - license_number: The license number to check (optional)
    - first_name: The first name to check (required)
    - last_name: The last name to check (required)
    
    Returns:
    - JSON response with matching violations
    """
    try:
        # Get parameters from request
        license_number = request.POST.get('license_number', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        
        logger.debug(f"Checking registration violations - license: '{license_number}', name: '{first_name} {last_name}'")
        
        if not first_name or not last_name:
            return JsonResponse({
                'success': False,
                'message': 'First name and last name are required',
                'violations': []
            })
            
        # Build the base query
        # Look for violations that:
        # 1. Are not claimed (user_account is null)
        # 2. Match license number OR (first name AND last name)
        # 3. Are in a status that makes sense to claim
        query = Violation.objects.filter(
            user_account__isnull=True,  # Not claimed by any user
            status__in=['PENDING', 'ADJUDICATED', 'APPROVED', 'OVERDUE']  # Active violations
        )
        
        # Add filters based on provided information
        filters = Q()
        
        # If license number is provided, add it to the filters
        if license_number:
            logger.debug(f"Adding license filter: {license_number}")
            filters |= Q(violator__license_number__iexact=license_number)
        
        # Add name filters - both first and last name must match
        if first_name and last_name:
            logger.debug(f"Adding name filter: {first_name} {last_name}")
            name_filter = Q(violator__first_name__iexact=first_name) & Q(violator__last_name__iexact=last_name)
            filters |= name_filter
        
        # Apply filters to the query
        if filters:
            query = query.filter(filters)
        else:
            # If no valid filters, return empty results
            return JsonResponse({
                'success': True,
                'message': 'No search criteria provided',
                'violations': []
            })
            
        # Execute query and format results
        matching_violations = []
        for v in query:
            try:
                # Get violation information
                matching_violations.append({
                    'id': v.id,
                    'violation_code': v.violation_code or 'N/A',
                    'description': v.description or v.violation_type or 'Unknown violation',
                    'date': v.violation_date.strftime('%Y-%m-%d') if v.violation_date else 'Unknown',
                    'time': v.violation_date.strftime('%H:%M') if v.violation_date else 'Unknown',
                    'location': v.location or 'Unknown location',
                    'fine_amount': f"PHP {v.fine_amount}" if v.fine_amount else 'Unknown',
                    'status': v.status or 'PENDING',
                    'violator_name': f"{v.violator.first_name} {v.violator.last_name}" if v.violator else 'Unknown'
                })
            except Exception as e:
                logger.error(f"Error processing violation {v.id}: {str(e)}")
        
        logger.debug(f"Found {len(matching_violations)} matching violations")
        
        return JsonResponse({
            'success': True,
            'message': f"Found {len(matching_violations)} matching violations",
            'violations': matching_violations
        })
        
    except Exception as e:
        logger.error(f"Error in check_registration_violations: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f"An error occurred: {str(e)}",
            'violations': []
        }, status=500) 