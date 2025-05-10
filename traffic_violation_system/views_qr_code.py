from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from .models import UserProfile, Driver, Vehicle, DriverVehicleAssignment, Violation, Operator, ViolatorQRHash
from django.contrib.auth.models import User
from django.db.models import Q
from django.conf import settings
import logging
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.utils import timezone
import io
import qrcode
from django.urls import reverse
from django.contrib import messages

# Directly import the VehicleRegistration model to ensure it's available
try:
    from traffic_violation_system.user_portal.models import VehicleRegistration
except ImportError:
    try:
        from user_portal.models import VehicleRegistration
    except ImportError:
        VehicleRegistration = None

# Set up logger
logger = logging.getLogger(__name__)

# Add this function after the imports section, before other functions
def search_existing_users(first_name, last_name, license_number=None):
    """
    Search for existing users with the same name or license number.
    
    Args:
        first_name: First name to search for
        last_name: Last name to search for
        license_number: Optional license number to search for
    
    Returns:
        List of matching users with their registration details
    """
    from django.db.models import Q
    from django.contrib.auth.models import User
    
    logger.info(f"Searching for existing users with name: {first_name} {last_name}, license: {license_number or 'None'}")
    
    matching_users = []
    
    # Build query to find users with matching name
    query = Q(first_name__iexact=first_name) & Q(last_name__iexact=last_name)
    
    try:
        # Find users with matching name
        users = User.objects.filter(query).select_related('userprofile')
        logger.info(f"Found {users.count()} users with matching name")
        
        # If we have a license number, also find users with that license
        license_users = []
        if license_number and license_number.strip() and license_number.strip().lower() != 'n/a':
            clean_license = license_number.strip()
            logger.info(f"Searching for users with license number: {clean_license}")
            
            # Try an exact match first
            exact_license_users = User.objects.filter(userprofile__license_number__iexact=clean_license).select_related('userprofile')
            logger.info(f"Found {exact_license_users.count()} users with exact matching license")
            
            # Then try a partial match (contains) for license numbers that might be formatted differently
            partial_license_users = User.objects.filter(userprofile__license_number__icontains=clean_license).select_related('userprofile')
            logger.info(f"Found {partial_license_users.count()} users with partial matching license")
            
            # Combine them using distinct to avoid duplicates
            license_users = (exact_license_users | partial_license_users).distinct()
            logger.info(f"Found {license_users.count()} total users with matching license")
            
            # Combine with name matches
            users = (users | license_users).distinct()
        
        logger.info(f"Found total of {users.count()} distinct matching users")
        
        # Format the results
        for user in users:
            # Skip users without profiles
            if not hasattr(user, 'userprofile'):
                logger.warning(f"User {user.id} ({user.username}) has no userprofile")
                continue
                
            # Get registration method (try to determine if it was from QR code or manual)
            registration_method = "Manual Registration"
            if user.userprofile.enforcer_id:
                if user.userprofile.enforcer_id.startswith('QR'):
                    registration_method = "QR Code Registration"
                elif user.userprofile.enforcer_id.startswith('ENF'):
                    registration_method = "Enforcer Registration"
            
            # Add user to results
            try:
                matching_users.append({
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'enforcer_id': user.userprofile.enforcer_id or 'N/A',
                    'license_number': user.userprofile.license_number or 'Not provided',
                    'is_driver': getattr(user.userprofile, 'is_driver', False),
                    'is_operator': getattr(user.userprofile, 'is_operator', False),
                    'registration_date': user.date_joined.strftime('%Y-%m-%d'),
                    'registration_method': registration_method,
                    'profile_url': f"/users/{user.id}/profile/"
                })
                logger.info(f"Added user to results: {user.get_full_name()} ({user.username})")
            except Exception as e:
                logger.error(f"Error adding user {user.id} to results: {str(e)}")
            
        logger.info(f"Found {len(matching_users)} existing users matching the criteria")
        
    except Exception as e:
        logger.error(f"Error searching for existing users: {str(e)}")
    
    return matching_users

# QR Code scanning and profile view
@csrf_exempt
def qr_profile_view(request, enforcer_id):
    """
    View that displays user information from a QR code.
    This is the endpoint that QR codes will point to.
    """
    logger.info(f"QR profile view requested for enforcer_id: {enforcer_id}")
    profile = get_object_or_404(UserProfile, enforcer_id=enforcer_id)
    user = profile.user
    
    # Basic user information
    data = {
        'id': profile.enforcer_id,
        'name': user.get_full_name(),
        'role': profile.get_role_display(),
        'license_number': profile.license_number or 'N/A',
        'is_driver': profile.is_driver,
        'is_operator': profile.is_operator,
        'address': profile.address,
        'phone_number': profile.phone_number,
        'contact_number': profile.contact_number,
        'email': user.email,
    }
    
    # Get associated vehicles from all possible sources
    vehicles = []
    
    # Debug output
    logger.info(f"Searching for vehicles for user {user.username} (ID: {user.id})")
    
    # STEP 1: Try checking user_portal VehicleRegistration models for the user
    try:
        # Check if VehicleRegistration is available
        if VehicleRegistration is not None:
            logger.info(f"Using imported VehicleRegistration model")
            user_vehicles = VehicleRegistration.objects.filter(user=user)
            logger.info(f"SQL Query: {user_vehicles.query}")
            logger.info(f"Found {user_vehicles.count()} vehicles in VehicleRegistration for user {user.username}")
        else:
            # Fallback to dynamic import
            logger.info(f"Using dynamic import for VehicleRegistration")
            try:
                from django.apps import apps
                VehicleRegistrationModel = apps.get_model('user_portal', 'VehicleRegistration')
                user_vehicles = VehicleRegistrationModel.objects.filter(user=user)
                logger.info(f"Found {user_vehicles.count()} vehicles using apps.get_model")
            except Exception as e:
                logger.error(f"Failed to import using apps.get_model: {str(e)}")
                # Direct raw SQL as last resort
                logger.info(f"Attempting raw SQL query for vehicles")
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT plate_number, make, model, year_model, color, classification, 
                               registration_date, expiry_date
                        FROM user_portal_vehicleregistration
                        WHERE user_id = %s
                    """, [user.id])
                    user_vehicles = []
                    for row in cursor.fetchall():
                        user_vehicles.append({
                            'plate_number': row[0],
                            'make': row[1],
                            'model': row[2],
                            'year': row[3],
                            'color': row[4],
                            'classification': row[5],
                            'registration_date': row[6],
                            'expiry_date': row[7],
                        })
                    logger.info(f"Found {len(user_vehicles)} vehicles using raw SQL")
        
        # Process the vehicles found (either through ORM or raw SQL)
        if isinstance(user_vehicles, list):  # Raw SQL result
            for vehicle in user_vehicles:
                vehicle['operator'] = user.get_full_name()
                vehicle['source'] = 'VehicleRegistration'
                vehicles.append(vehicle)
                logger.info(f"Added vehicle from raw SQL: {vehicle['plate_number']}")
        else:  # ORM result
            for vehicle in user_vehicles:
                vehicle_data = {
                    'plate_number': vehicle.plate_number or 'N/A',
                    'make': vehicle.make or 'N/A',
                    'model': vehicle.model or 'N/A',
                    'year': vehicle.year_model or 'N/A',
                    'operator': user.get_full_name(),
                    'classification': vehicle.classification,
                    'registration_date': vehicle.registration_date.strftime('%Y-%m-%d') if vehicle.registration_date else 'N/A',
                    'expiry_date': vehicle.expiry_date.strftime('%Y-%m-%d') if vehicle.expiry_date else 'N/A',
                    'color': vehicle.color or 'N/A',
                    'source': 'VehicleRegistration'
                }
                vehicles.append(vehicle_data)
                logger.info(f"Added vehicle from VehicleRegistration: {vehicle.plate_number} - {vehicle.make} {vehicle.model}")
            
    except Exception as e:
        logger.error(f"Error checking VehicleRegistration: {str(e)}")
    
    # STEP 2: Check for Driver record and associated vehicles through assignments
    if profile.is_driver:
        try:
            # Get driver record
            driver = Driver.objects.filter(
                Q(first_name__iexact=user.first_name) & 
                Q(last_name__iexact=user.last_name)
            ).first()
            
            if driver:
                data['driver'] = {
                    'id': getattr(driver, 'new_pd_number', 'N/A'),
                    'status': 'Active' if driver.active else 'Inactive',
                    'type': 'Standard',   # Adding type field for frontend display
                    'license_number': driver.license_number or profile.license_number or 'N/A',
                    'expiration_date': driver.expiration_date.strftime('%Y-%m-%d') if driver.expiration_date else 'N/A',
                    'contact_number': driver.contact_number or profile.contact_number or profile.phone_number or 'N/A',
                    'emergency_contact': driver.emergency_contact or 'N/A',
                    'emergency_contact_number': driver.emergency_contact_number or 'N/A'
                }
                logger.info(f"Found driver record for {user.get_full_name()}")
                
                # Find vehicles through DriverVehicleAssignment
                driver_vehicles = DriverVehicleAssignment.objects.filter(
                    driver=driver,
                    is_active=True
                )
                
                logger.info(f"Found {driver_vehicles.count()} driver vehicle assignments for driver {driver.id}")
                
                for dv in driver_vehicles:
                    vehicle = dv.vehicle
                    if vehicle:
                        vehicle_data = {
                            'plate_number': vehicle.plate_number or 'N/A',
                            'make': getattr(vehicle, 'make', vehicle.vehicle_type) or 'N/A',
                            'model': getattr(vehicle, 'model', '') or 'N/A',
                            'year': getattr(vehicle, 'year_model', '') or 'N/A',
                            'operator': vehicle.operator.full_name() if vehicle.operator else 'N/A',
                            'engine_number': vehicle.engine_number or 'N/A',
                            'chassis_number': vehicle.chassis_number or 'N/A',
                            'color': vehicle.color or 'N/A',
                            'source': 'DriverVehicleAssignment'
                        }
                        # Avoid duplicates by checking plate number
                        if not any(v['plate_number'] == vehicle_data['plate_number'] for v in vehicles):
                            vehicles.append(vehicle_data)
                            logger.info(f"Added vehicle from DriverVehicleAssignment: {vehicle.plate_number} - {vehicle.vehicle_type}")
            else:
                logger.warning(f"User {user.get_full_name()} is marked as driver but no Driver record found")
                
        except Exception as e:
            logger.error(f"Error getting driver/vehicle information: {str(e)}")
    
    # STEP 3: Check if user is operator and find vehicles through operator relationship
    if profile.is_operator:
        try:
            # Find operator record
            operator = Operator.objects.filter(
                Q(first_name__iexact=user.first_name) & 
                Q(last_name__iexact=user.last_name)
            ).first()
            
            if operator:
                logger.info(f"Found operator record for {user.get_full_name()}")
                
                # Find vehicles through operator relationship
                operator_vehicles = Vehicle.objects.filter(operator=operator)
                
                logger.info(f"Found {operator_vehicles.count()} vehicles for operator {operator.id}")
                
                for vehicle in operator_vehicles:
                    vehicle_data = {
                        'plate_number': vehicle.plate_number or 'N/A',
                        'make': getattr(vehicle, 'make', vehicle.vehicle_type) or 'N/A',
                        'model': getattr(vehicle, 'model', '') or 'N/A',
                        'year': getattr(vehicle, 'year_model', '') or 'N/A',
                        'operator': operator.full_name(),
                        'engine_number': vehicle.engine_number or 'N/A',
                        'chassis_number': vehicle.chassis_number or 'N/A',
                        'color': vehicle.color or 'N/A',
                        'source': 'OperatorVehicle'
                    }
                    # Avoid duplicates by checking plate number
                    if not any(v['plate_number'] == vehicle_data['plate_number'] for v in vehicles):
                        vehicles.append(vehicle_data)
                        logger.info(f"Added vehicle from Operator: {vehicle.plate_number} - {vehicle.vehicle_type}")
            else:
                logger.warning(f"User {user.get_full_name()} is marked as operator but no Operator record found")
                
        except Exception as e:
            logger.error(f"Error getting operator/vehicle information: {str(e)}")
    
    # STEP 4: Look for violations with vehicles that might be associated with this user
    try:
        if profile.license_number:
            # Create a query for violations with plate numbers
            violation_query = Violation.objects.filter(
                Q(violator__license_number=profile.license_number) | Q(user_account=user),
                Q(plate_number__isnull=False) & ~Q(plate_number='')
            ).order_by('-violation_date')
            
            # Try to use distinct on plate_number if the database supports it (PostgreSQL)
            try:
                vehicle_violations = violation_query.distinct('plate_number')
                logger.info(f"Using PostgreSQL distinct query")
            except Exception:
                # Fallback for other databases - get all violations and filter in Python
                logger.info(f"Falling back to manual distinct filtering")
                vehicle_violations = violation_query
                processed_plates = set()
                filtered_violations = []
                
                for v in vehicle_violations:
                    if v.plate_number and v.plate_number not in processed_plates:
                        processed_plates.add(v.plate_number)
                        filtered_violations.append(v)
                
                vehicle_violations = filtered_violations
            
            logger.info(f"Found {len(vehicle_violations)} distinct vehicles from violations")
            
            for violation in vehicle_violations:
                if violation.plate_number and not any(v['plate_number'] == violation.plate_number for v in vehicles):
                    vehicle_data = {
                        'plate_number': violation.plate_number,
                        'make': violation.vehicle_type or 'Unknown',
                        'model': 'Unknown',
                        'year': 'Unknown',
                        'operator': violation.violator.get_full_name() if violation.violator else 'Unknown',
                        'color': violation.color or 'Unknown',
                        'source': 'ViolationRecord'
                    }
                    vehicles.append(vehicle_data)
                    logger.info(f"Added vehicle from Violation: {violation.plate_number}")
    except Exception as e:
        logger.error(f"Error getting vehicles from violations: {str(e)}")
    
    # Add vehicles to the data dictionary
    data['vehicles'] = vehicles
    logger.info(f"Total vehicles found: {len(vehicles)}")
    
    # Add violation information
    try:
        # Get violations linked to this user's account directly - avoid circular imports
        violations = None
        
        try:
            # First try the user_account direct relationship
            from django.db.models import Q
            from traffic_violation_system.models import Violation
            
            # Check if user has a license number and use it to filter
            if profile.license_number:
                logger.info(f"Querying violations for user {user.username} with license {profile.license_number}")
                violations = Violation.objects.filter(
                    Q(violator__license_number=profile.license_number) | Q(user_account=user)
                ).order_by('-violation_date')
            else:
                # Filter only by user account if no license number available
                logger.info(f"Querying violations for user {user.username} by account only (no license)")
                violations = Violation.objects.filter(user_account=user).order_by('-violation_date')
            
            logger.info(f"Retrieved violations using direct filter: found {violations.count() if violations else 0}")
        except Exception as import_error:
            logger.error(f"Error on direct filter method: {str(import_error)}")
            # Fallback to try the custom manager if available
            try:
                # Try using the custom manager as fallback
                logger.info(f"Attempting to use custom violation manager for user {user.username}")
                violations = Violation.user_violations.get_user_violations(user).order_by('-violation_date')
                logger.info(f"Retrieved violations using UserViolationManager: found {violations.count() if violations else 0}")
            except Exception as manager_error:
                logger.error(f"Error using UserViolationManager: {str(manager_error)}")
                violations = []
        
        if violations and violations.exists():
            # Filter to only include pending and adjudicated violations
            filtered_violations = [
                violation for violation in violations 
                if getattr(violation, 'status', '').lower() in ['pending', 'adjudicated']
            ]
            
            logger.info(f"Filtered to {len(filtered_violations)} pending/adjudicated violations")
            
            # Double-check all violations belong to this user
            validated_violations = []
            for violation in filtered_violations:
                # Check if this violation is actually for this user
                is_user_violation = False
                
                # Direct user account link
                if hasattr(violation, 'user_account') and violation.user_account == user:
                    is_user_violation = True
                
                # License number match
                elif (hasattr(violation, 'violator') and 
                      hasattr(violation.violator, 'license_number') and 
                      violation.violator.license_number and 
                      profile.license_number and
                      violation.violator.license_number.lower() == profile.license_number.lower()):
                    is_user_violation = True
                
                # QR hash link
                elif (hasattr(violation, 'qr_hash') and 
                      violation.qr_hash and 
                      hasattr(violation.qr_hash, 'user_account') and
                      violation.qr_hash.user_account == user):
                    is_user_violation = True
                    
                # Include only verified user violations
                if is_user_violation:
                    validated_violations.append(violation)
                else:
                    logger.warning(f"Violation ID {violation.id} was returned for user {user.username} but doesn't appear to belong to them. Skipping.")
            
            logger.info(f"After user validation: {len(validated_violations)} of {len(filtered_violations)} violations are for this user")
            
            # Convert violations to a list of dictionaries for the template
            violations_data = []
            
            for violation in validated_violations:
                # Convert to dictionary for template
                violation_data = {
                    'id': violation.id,
                    'violation_date': violation.violation_date,
                    'location': violation.location,
                    'violation_type': violation.violation_type,
                    'fine_amount': float(violation.fine_amount),
                    'amount': float(violation.fine_amount), # For template compatibility
                    'status': violation.status,
                    'plate_number': violation.plate_number or 'N/A',
                    'vehicle_type': violation.vehicle_type or 'N/A',
                }
                violations_data.append(violation_data)
            
            # Add violations to the data dictionary for the template
            data['violations'] = violations_data
            
            logger.info(f"Processed {len(violations_data)} violations for display")
        else:
            data['violations'] = []
            logger.info(f"No violations found for {user.get_full_name()}")
            
    except Exception as e:
        logger.error(f"Error getting violation information: {str(e)}")
        data['violations'] = []
    
    # Check if we're expecting a JSON response
    if request.headers.get('Accept') == 'application/json':
        logger.info(f"Returning JSON response with data: {data}")
        return JsonResponse(data)
    else:
        # UPDATED: Redirect to qr_user_data view for consistent template rendering
        logger.info(f"Redirecting to qr_user_data view for {user.get_full_name()}")
        return redirect('qr_user_data', enforcer_id=enforcer_id)

@login_required
def qr_scanner(request):
    """
    Renders the QR code scanner interface.
    This page allows authorized users to scan QR codes for verification.
    """
    return render(request, 'qr_scanner.html', {
        'page_title': 'QR Code Scanner',
        'debug': settings.DEBUG
    })

@csrf_exempt
def qr_user_data(request, enforcer_id):
    """
    View that displays user information in a separate template from a QR code.
    This provides a cleaner UI focused on user data presentation.
    """
    logger.info(f"QR user data view requested for enforcer_id: {enforcer_id}")
    
    try:
        # Log request information for debugging
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        
        # ENHANCED ERROR HANDLING: Try multiple approaches to find the user with any QR code format
        try:
            # First attempt exact match
            profile = UserProfile.objects.get(enforcer_id=enforcer_id)
            logger.info(f"Found exact match for enforcer_id: {enforcer_id}")
        except UserProfile.DoesNotExist:
            logger.warning(f"No exact match found for enforcer_id: {enforcer_id}")
            
            # Import Q in the local scope to avoid reference errors
            from django.db.models import Q
            
            # APPROACH 1: Try by username - many QR codes might encode just the username
            try:
                user = User.objects.get(username=enforcer_id)
                profile = UserProfile.objects.get(user=user)
                logger.info(f"Found user by exact username match: {enforcer_id}")
            except (User.DoesNotExist, UserProfile.DoesNotExist):
                logger.warning(f"No user with username: {enforcer_id}")
                
                # APPROACH 2: Try without dashes (common QR format issue)
                try:
                    no_dash_id = enforcer_id.replace('-', '')
                    profile = UserProfile.objects.get(enforcer_id=no_dash_id)
                    logger.info(f"Found match with dashes removed: {no_dash_id}")
                    return redirect('qr_user_data', enforcer_id=no_dash_id)
                except UserProfile.DoesNotExist:
                    logger.warning(f"No match found with dashes removed: {no_dash_id}")
                
                    # APPROACH 3: Try by license number (some QR codes might contain license numbers)
                    try:
                        license_profiles = UserProfile.objects.filter(license_number=enforcer_id)
                        if license_profiles.exists():
                            profile = license_profiles.first()
                            logger.info(f"Found user by license number: {enforcer_id}")
                        else:
                            raise UserProfile.DoesNotExist("No user with this license number")
                    except UserProfile.DoesNotExist:
                        logger.warning(f"No user with license number: {enforcer_id}")
                        
                        # APPROACH 4: Try legacy "2-Rossvan" format (digit-name format)
                        if '-' in enforcer_id:
                            parts = enforcer_id.split('-')
                            if len(parts) == 2 and parts[0].isdigit():
                                # This looks like "2-Rossvan" format, try to find by name
                                name = parts[1]
                                logger.info(f"Detected possible legacy format with name: {name}")
                                
                                # Try to find users with this name
                                name_matches = User.objects.filter(
                                    Q(first_name__icontains=name) | 
                                    Q(last_name__icontains=name) |
                                    Q(username__icontains=name)
                                )
                                
                                if name_matches.exists():
                                    logger.info(f"Found {name_matches.count()} users matching '{name}'")
                                    # Get their profiles
                                    name_profiles = UserProfile.objects.filter(user__in=name_matches)
                                    if name_profiles.exists():
                                        # Automatically use the first matching profile
                                        matching_profile = name_profiles.first()
                                        logger.info(f"Automatically redirecting to profile with enforcer_id: {matching_profile.enforcer_id}")
                                        return redirect('qr_user_data', enforcer_id=matching_profile.enforcer_id)
                        
                        # APPROACH 5: Try by driver's PD number
                        try:
                            driver = Driver.objects.filter(Q(new_pd_number=enforcer_id) | Q(pd_number=enforcer_id)).first()
                            if driver:
                                # Try to find a user with matching name
                                user = User.objects.filter(
                                    Q(first_name__iexact=driver.first_name) & 
                                    Q(last_name__iexact=driver.last_name)
                                ).first()
                                
                                if user and hasattr(user, 'userprofile'):
                                    profile = user.userprofile
                                    logger.info(f"Found user through driver PD number: {enforcer_id}")
                                else:
                                    raise UserProfile.DoesNotExist("No user profile for this driver")
                            else:
                                raise Driver.DoesNotExist("No driver with this PD number")
                        except (Driver.DoesNotExist, UserProfile.DoesNotExist):
                            logger.warning(f"No driver or matching user profile found for PD number: {enforcer_id}")
                            
                            # If we've reached here, we couldn't find an exact match
                            error_message = f"No user profile matches the ID/code: {enforcer_id}"
                            similar_profiles = []
                            
                            # Try case-insensitive search to find similar matches
                            similar_part = enforcer_id.split('-')[-1] if '-' in enforcer_id else enforcer_id
                            similar_profiles = UserProfile.objects.filter(
                                Q(enforcer_id__icontains=similar_part) |
                                Q(user__username__icontains=similar_part) |
                                Q(user__first_name__icontains=similar_part) |
                                Q(user__last_name__icontains=similar_part) |
                                Q(license_number__icontains=similar_part)
                            )
                            
                            # Show diagnostic info about available IDs in the system
                            sample_profiles = UserProfile.objects.all().order_by('?')[:5]  # Get 5 random profiles
                            if sample_profiles.exists():
                                logger.info(f"Sample enforcer IDs in system: {[p.enforcer_id for p in sample_profiles]}")
                                sample_id_format = f"Sample IDs in system: {', '.join([p.enforcer_id for p in sample_profiles])}"
                                
                                # Add information about proper format
                                if all(p.enforcer_id.startswith('ENF') for p in sample_profiles):
                                    error_message += f". The system uses enforcer IDs in the format 'ENF1234'. {sample_id_format}"
                                else:
                                    error_message += f". {sample_id_format}"
                            
                            # Add information if we found similar profiles
                            if similar_profiles.exists():
                                logger.info(f"Found {similar_profiles.count()} similar profiles: {[p.enforcer_id for p in similar_profiles]}")
                                
                                if "Did you mean" not in error_message and "We found user(s)" not in error_message:
                                    error_message += f". Did you mean one of these? {', '.join([p.enforcer_id for p in similar_profiles[:5]])}"
                                    
                            # Add improved instruction for QR code troubleshooting
                            error_message += "\n\nTo troubleshoot: Try scanning the QR code again, or try searching for the user by name, license number, or username in the system."
                            
                            return render(request, 'qr_user_data.html', {
                                'enforcer_id': enforcer_id,
                                'is_valid': False,
                                'error': error_message,
                                'similar_profiles': similar_profiles[:5] if similar_profiles else None,
                                'now': timezone.now(),
                                'debug': settings.DEBUG,
                                'legacy_format': '-' in enforcer_id and len(enforcer_id.split('-')) == 2 and enforcer_id.split('-')[0].isdigit()
                            })
        
        user = profile.user
        is_valid = True
        error = None
        
        logger.info(f"Found user profile: {profile.enforcer_id} for user {user.username}")
        
        # NEW: Search for other existing users with same name or license number
        existing_users = search_existing_users(
            user.first_name, 
            user.last_name, 
            profile.license_number
        )
        
        # Filter out the current user from the results
        existing_users = [u for u in existing_users if u['id'] != user.id]
        
        # Basic user information
        data = {
            'id': profile.enforcer_id,
            'name': user.get_full_name(),
            'role': profile.get_role_display(),
            'license_number': profile.license_number or 'N/A',
            'is_driver': profile.is_driver,
            'is_operator': profile.is_operator,
            'address': profile.address,
            'phone_number': profile.phone_number,
            'contact_number': profile.contact_number,
            'email': user.email,
            'avatar': profile.avatar.url if profile.avatar else None,
            # NEW: Add information about existing users with same name/license
            'existing_users': existing_users,
            'has_existing_users': len(existing_users) > 0,
        }
        
        logger.info(f"Basic user data prepared: {data}")
        
        # Get associated vehicles from all possible sources
        vehicles = []
        
        # Debug output
        logger.info(f"Searching for vehicles for user {user.username} (ID: {user.id})")
        
        # STEP 1: Try checking user_portal VehicleRegistration models for the user
        try:
            # Check if VehicleRegistration is available
            if VehicleRegistration is not None:
                logger.info(f"Using imported VehicleRegistration model")
                user_vehicles = VehicleRegistration.objects.filter(user=user)
                logger.info(f"Found {user_vehicles.count()} vehicles in VehicleRegistration for user {user.username}")
            
                for vehicle in user_vehicles:
                    vehicle_data = {
                        'plate_number': vehicle.plate_number or 'N/A',
                        'make': vehicle.make or 'N/A',
                        'model': vehicle.model or 'N/A',
                        'year': vehicle.year_model or 'N/A',
                        'operator': user.get_full_name(),
                        'classification': vehicle.classification,
                        'registration_date': vehicle.registration_date.strftime('%Y-%m-%d') if vehicle.registration_date else 'N/A',
                        'expiry_date': vehicle.expiry_date.strftime('%Y-%m-%d') if vehicle.expiry_date else 'N/A',
                        'color': vehicle.color or 'N/A',
                        'source': 'VehicleRegistration'
                    }
                    vehicles.append(vehicle_data)
                    logger.info(f"Added vehicle from VehicleRegistration: {vehicle.plate_number} - {vehicle.make} {vehicle.model}")
        except Exception as e:
            logger.error(f"Error checking VehicleRegistration: {str(e)}")
        
        # STEP 2: Check for Driver record and associated vehicles through assignments
        if profile.is_driver:
            try:
                # Get driver record
                driver = Driver.objects.filter(
                    Q(first_name__iexact=user.first_name) & 
                    Q(last_name__iexact=user.last_name)
                ).first()
                
                if driver:
                    data['driver'] = {
                        'id': getattr(driver, 'new_pd_number', 'N/A'),
                        'status': 'Active' if driver.active else 'Inactive',
                        'type': 'Standard',   # Adding type field for frontend display
                        'license_number': driver.license_number or profile.license_number or 'N/A',
                        'expiration_date': driver.expiration_date.strftime('%Y-%m-%d') if driver.expiration_date else 'N/A',
                        'contact_number': driver.contact_number or profile.contact_number or profile.phone_number or 'N/A',
                        'emergency_contact': driver.emergency_contact or 'N/A',
                        'emergency_contact_number': driver.emergency_contact_number or 'N/A'
                    }
                    logger.info(f"Found driver record for {user.get_full_name()}")
                    
                    # Find vehicles through DriverVehicleAssignment
                    driver_vehicles = DriverVehicleAssignment.objects.filter(
                        driver=driver,
                        is_active=True
                    )
                    
                    logger.info(f"Found {driver_vehicles.count()} driver vehicle assignments for driver {driver.id}")
                    
                    for dv in driver_vehicles:
                        vehicle = dv.vehicle
                        if vehicle:
                            vehicle_data = {
                                'plate_number': vehicle.plate_number or 'N/A',
                                'make': getattr(vehicle, 'make', vehicle.vehicle_type) or 'N/A',
                                'model': getattr(vehicle, 'model', '') or 'N/A',
                                'year': getattr(vehicle, 'year_model', '') or 'N/A',
                                'operator': vehicle.operator.full_name() if vehicle.operator else 'N/A',
                                'engine_number': vehicle.engine_number or 'N/A',
                                'chassis_number': vehicle.chassis_number or 'N/A',
                                'color': vehicle.color or 'N/A',
                                'source': 'DriverVehicleAssignment'
                            }
                            # Avoid duplicates by checking plate number
                            if not any(v['plate_number'] == vehicle_data['plate_number'] for v in vehicles):
                                vehicles.append(vehicle_data)
                                logger.info(f"Added vehicle from DriverVehicleAssignment: {vehicle.plate_number} - {vehicle.vehicle_type}")
            except Exception as e:
                logger.error(f"Error getting driver/vehicle information: {str(e)}")
        
        # STEP 3: Check if user is operator and find vehicles through operator relationship
        if profile.is_operator:
            try:
                # Find operator record
                operator = Operator.objects.filter(
                    Q(first_name__iexact=user.first_name) & 
                    Q(last_name__iexact=user.last_name)
                ).first()
                
                if operator:
                    logger.info(f"Found operator record for {user.get_full_name()}")
                    
                    # Find vehicles through operator relationship
                    operator_vehicles = Vehicle.objects.filter(operator=operator)
                    
                    logger.info(f"Found {operator_vehicles.count()} vehicles for operator {operator.id}")
                    
                    for vehicle in operator_vehicles:
                        vehicle_data = {
                            'plate_number': vehicle.plate_number or 'N/A',
                            'make': getattr(vehicle, 'make', vehicle.vehicle_type) or 'N/A',
                            'model': getattr(vehicle, 'model', '') or 'N/A',
                            'year': getattr(vehicle, 'year_model', '') or 'N/A',
                            'operator': operator.full_name(),
                            'engine_number': vehicle.engine_number or 'N/A',
                            'chassis_number': vehicle.chassis_number or 'N/A',
                            'color': vehicle.color or 'N/A',
                            'source': 'OperatorVehicle'
                        }
                        # Avoid duplicates by checking plate number
                        if not any(v['plate_number'] == vehicle_data['plate_number'] for v in vehicles):
                            vehicles.append(vehicle_data)
                            logger.info(f"Added vehicle from Operator: {vehicle.plate_number} - {vehicle.vehicle_type}")
            except Exception as e:
                logger.error(f"Error getting operator/vehicle information: {str(e)}")
        
        # Add vehicles to the data dictionary
        data['vehicles'] = vehicles
        logger.info(f"Total vehicles found: {len(vehicles)}")
        
        # Add violation information
        try:
            # Get violations linked to this user's account directly - avoid circular imports
            violations = None
            
            try:
                # First try the user_account direct relationship
                from django.db.models import Q
                from traffic_violation_system.models import Violation
                
                # Check if user has a license number and use it to filter
                if profile.license_number:
                    logger.info(f"Querying violations for user {user.username} with license {profile.license_number}")
                    violations = Violation.objects.filter(
                        Q(violator__license_number=profile.license_number) | Q(user_account=user)
                    ).order_by('-violation_date')
                else:
                    # Filter only by user account if no license number available
                    logger.info(f"Querying violations for user {user.username} by account only (no license)")
                    violations = Violation.objects.filter(user_account=user).order_by('-violation_date')
                
                logger.info(f"Retrieved violations using direct filter: found {violations.count() if violations else 0}")
            except Exception as import_error:
                logger.error(f"Error on direct filter method: {str(import_error)}")
                # Fallback to try the custom manager if available
                try:
                    # Try using the custom manager as fallback
                    logger.info(f"Attempting to use custom violation manager for user {user.username}")
                    violations = Violation.user_violations.get_user_violations(user).order_by('-violation_date')
                    logger.info(f"Retrieved violations using UserViolationManager: found {violations.count() if violations else 0}")
                except Exception as manager_error:
                    logger.error(f"Error using UserViolationManager: {str(manager_error)}")
                    violations = []
            
            if violations and violations.exists():
                # Filter to only include pending and adjudicated violations
                filtered_violations = [
                    violation for violation in violations 
                    if getattr(violation, 'status', '').lower() in ['pending', 'adjudicated']
                ]
                
                logger.info(f"Filtered to {len(filtered_violations)} pending/adjudicated violations")
                
                # Double-check all violations belong to this user
                validated_violations = []
                for violation in filtered_violations:
                    # Check if this violation is actually for this user
                    is_user_violation = False
                    
                    # Direct user account link
                    if hasattr(violation, 'user_account') and violation.user_account == user:
                        is_user_violation = True
                    
                    # License number match
                    elif (hasattr(violation, 'violator') and 
                          hasattr(violation.violator, 'license_number') and 
                          violation.violator.license_number and 
                          profile.license_number and
                          violation.violator.license_number.lower() == profile.license_number.lower()):
                        is_user_violation = True
                    
                    # QR hash link
                    elif (hasattr(violation, 'qr_hash') and 
                          violation.qr_hash and 
                          hasattr(violation.qr_hash, 'user_account') and
                          violation.qr_hash.user_account == user):
                        is_user_violation = True
                        
                    # Include only verified user violations
                    if is_user_violation:
                        validated_violations.append(violation)
                    else:
                        logger.warning(f"Violation ID {violation.id} was returned for user {user.username} but doesn't appear to belong to them. Skipping.")
                
                logger.info(f"After user validation: {len(validated_violations)} of {len(filtered_violations)} violations are for this user")
                
                # Convert violations to a list of dictionaries for the template
                violations_data = []
                
                for violation in validated_violations:
                    # Convert to dictionary for template
                    violation_data = {
                        'id': violation.id,
                        'violation_date': violation.violation_date,
                        'location': violation.location,
                        'violation_type': violation.violation_type,
                        'fine_amount': float(violation.fine_amount),
                        'amount': float(violation.fine_amount), # For template compatibility
                        'status': violation.status,
                        'plate_number': violation.plate_number or 'N/A',
                        'vehicle_type': violation.vehicle_type or 'N/A',
                    }
                    violations_data.append(violation_data)
                
                # Add violations to the data dictionary for the template
                data['violations'] = violations_data
                
                logger.info(f"Processed {len(violations_data)} violations for display")
            else:
                data['violations'] = []
                logger.info(f"No violations found for {user.get_full_name()}")
                
        except Exception as e:
            logger.error(f"Error getting violation information: {str(e)}")
            data['violations'] = []
            
        # Check if we're expecting a JSON response
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse(data)
        else:
            return render(request, 'qr_user_data.html', {
                'enforcer_id': enforcer_id,
                'data': data,
                'is_valid': is_valid,
                'error': error,
                'has_violations': data['violations'] != [],
                'recent_violations': data['violations'][:5] if data['violations'] else None,
                'violation_count': len(data['violations']) if data['violations'] else 0,
                'now': timezone.now(),
                'debug': settings.DEBUG,
                'existing_users': data.get('existing_users', []),
                'has_existing_users': data.get('has_existing_users', False),
            })
            
    except Exception as e:
        logger.error(f"Error in qr_user_data: {str(e)}", exc_info=True)
        return render(request, 'qr_user_data.html', {
            'enforcer_id': enforcer_id,
            'is_valid': False,
            'error': f"An error occurred: {str(e)}",
            'now': timezone.now(),
            'debug': settings.DEBUG
        })

def get_or_create_violator_qr_hash(first_name, last_name, license_number=None, phone_number=None):
    """
    Get or create a ViolatorQRHash for a violator.
    This ensures that multiple violations for the same violator use the same QR code.
    """
    # First, try to find an existing hash based on identifying information
    existing_hash = None
    
    # Check by license number if available (most reliable identifier)
    if license_number:
        existing_hash = ViolatorQRHash.objects.filter(
            license_number=license_number,
            registered=False  # Only use unregistered hashes
        ).first()
    
    # If no existing hash found by license, try by name and phone if available
    if not existing_hash and phone_number:
        existing_hash = ViolatorQRHash.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            phone_number=phone_number,
            registered=False
        ).first()
    
    # If still no match, check by name only as last resort
    if not existing_hash:
        existing_hash = ViolatorQRHash.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            registered=False
        ).first()
    
    # If we found an existing hash, return it
    if existing_hash:
        return existing_hash
    
    # Otherwise, create a new hash
    hash_id = ViolatorQRHash.generate_hash(first_name, last_name, license_number)
    
    # Create 90-day expiration
    expires_at = timezone.now() + timezone.timedelta(days=90)
    
    # Create new ViolatorQRHash
    new_hash = ViolatorQRHash.objects.create(
        hash_id=hash_id,
        first_name=first_name,
        last_name=last_name,
        license_number=license_number,
        phone_number=phone_number,
        expires_at=expires_at
    )
    
    return new_hash

def generate_violation_qr_code(violation_id):
    """
    Generate a QR code for a violation.
    Links the violation to an existing or new ViolatorQRHash.
    """
    # Get the violation
    violation = get_object_or_404(Violation, id=violation_id)
    
    # If violation already has a QR hash, use it
    if violation.qr_hash:
        qr_hash = violation.qr_hash
    else:
        # Create or get a QR hash for this violator
        qr_hash = get_or_create_violator_qr_hash(
            first_name=violation.first_name,
            last_name=violation.last_name,
            license_number=violation.license_number,
            phone_number=violation.phone_number
        )
        
        # Link the violation to the QR hash
        violation.qr_hash = qr_hash
        violation.save()
    
    # Generate the registration URL with the hash
    registration_url = reverse('register_with_violations', kwargs={'hash_id': qr_hash.hash_id})
    absolute_url = f"{settings.SITE_URL}{registration_url}"
    
    # Create the QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(absolute_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes for response
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    return buffer.getvalue(), absolute_url

def violation_qr_code_view(request, violation_id):
    """View to display QR code for a violation"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    qr_image, registration_url = generate_violation_qr_code(violation_id)
    
    # Return the QR code image
    response = HttpResponse(qr_image, content_type="image/png")
    response['Content-Disposition'] = f'inline; filename="violation_qr_{violation_id}.png"'
    return response

def violation_qr_code_print_view(request, violation_id):
    """View to display a printable page with the QR code"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    violation = get_object_or_404(Violation, id=violation_id)
    qr_image, registration_url = generate_violation_qr_code(violation_id)
    
    # Convert QR code image to base64 for embedding in HTML
    import base64
    qr_image_base64 = base64.b64encode(qr_image).decode('utf-8')
    
    context = {
        'violation': violation,
        'qr_image_base64': qr_image_base64,
        'registration_url': registration_url,
    }
    
    return render(request, 'violations/print_qr_code.html', context) 