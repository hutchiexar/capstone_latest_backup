from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import UserProfile, Driver, Vehicle, DriverVehicleAssignment, Violation, Operator
from django.contrib.auth.models import User
from django.db.models import Q
from django.conf import settings
import logging
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.utils import timezone

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
                violations = Violation.objects.filter(
                    Q(violator__license_number=profile.license_number) | Q(user_account=user)
                ).order_by('-violation_date')
            else:
                # Filter only by user account if no license number available
                violations = Violation.objects.filter(user_account=user).order_by('-violation_date')
            
            logger.info(f"Retrieved violations using direct filter: found {violations.count() if violations else 0}")
        except Exception as import_error:
            logger.error(f"Error on direct filter method: {str(import_error)}")
            # Fallback to try the custom manager if available
            try:
                # Try using the custom manager as fallback
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
            
            # Convert violations to a list of dictionaries for the template
            violations_data = []
            
            for violation in filtered_violations:
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
        
        # Basic user information - reuse the existing logic from qr_profile_view
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
                    violations = Violation.objects.filter(
                        Q(violator__license_number=profile.license_number) | Q(user_account=user)
                    ).order_by('-violation_date')
                else:
                    # Filter only by user account if no license number available
                    violations = Violation.objects.filter(user_account=user).order_by('-violation_date')
                
                logger.info(f"Retrieved violations using direct filter: found {violations.count() if violations else 0}")
            except Exception as import_error:
                logger.error(f"Error on direct filter method: {str(import_error)}")
                # Fallback to try the custom manager if available
                try:
                    # Try using the custom manager as fallback
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
                
                # Convert violations to a list of dictionaries for the template
                violations_data = []
                
                for violation in filtered_violations:
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
            
    except Exception as e:
        logger.error(f"Error fetching user data: {str(e)}")
        is_valid = False
        error = str(e)
        data = {}
    
    # Get current datetime for verification timestamp
    now = timezone.now()
    
    # Render the dedicated template
    return render(request, 'qr_user_data.html', {
        'enforcer_id': enforcer_id,
        'is_valid': is_valid,
        'error': error,
        'data': data,
        'now': now,
        'debug': settings.DEBUG
    }) 