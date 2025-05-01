from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import UserProfile, Driver, Vehicle, DriverVehicleAssignment, Violation, Operator
from django.contrib.auth.models import User
from django.db.models import Q
from django.conf import settings
import logging
from django.contrib.auth.decorators import login_required
from django.db import connection

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
        # Get violations linked to this user's license number and user account
        violations = None
        
        if profile.license_number:
            violations = Violation.objects.filter(
                Q(violator__license_number=profile.license_number) | Q(user_account=user)
            ).order_by('-violation_date')[:5]  # Limit to 5 most recent
        
        if violations and violations.exists():
            violations_data = []
            for violation in violations:
                violations_data.append({
                    'id': violation.id,
                    'date': violation.violation_date.strftime('%Y-%m-%d %H:%M'),
                    'location': violation.location,
                    'violation_type': violation.violation_type,
                    'fine_amount': float(violation.fine_amount),
                    'status': violation.status,
                    'plate_number': violation.plate_number or 'N/A',
                    'vehicle_type': violation.vehicle_type or 'N/A'
                })
            data['violations'] = violations_data
            logger.info(f"Found {len(violations_data)} violations for {user.get_full_name()}")
        else:
            data['violations'] = []
            logger.info(f"No violations found for {user.get_full_name()}")
            
    except Exception as e:
        logger.error(f"Error getting violation information: {str(e)}")
        data['violations'] = []
    
    # Check if this is an API request or a regular browser request
    if request.headers.get('Accept', '').find('application/json') != -1:
        logger.info(f"Returning JSON response with data: {data}")
        return JsonResponse(data)
    else:
        # Render a template showing the profile information
        logger.info(f"Rendering HTML template for {user.get_full_name()}")
        return render(request, 'user_portal/qr_profile_details.html', {
            'profile': profile,
            'user': user,
            'data': data,
            'debug': settings.DEBUG
        })

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
        profile = get_object_or_404(UserProfile, enforcer_id=enforcer_id)
        user = profile.user
        is_valid = True
        error = None
        
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
        }
        
        # Get associated vehicles from all possible sources
        # Reuse the existing logic from qr_profile_view to fetch vehicles
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
            # Get violations linked to this user's license number and user account
            violations = None
            
            if profile.license_number:
                violations = Violation.objects.filter(
                    Q(violator__license_number=profile.license_number) | Q(user_account=user)
                ).order_by('-violation_date')[:5]  # Limit to 5 most recent
            
            if violations and violations.exists():
                violations_data = []
                for violation in violations:
                    violations_data.append({
                        'id': violation.id,
                        'date': violation.violation_date.strftime('%Y-%m-%d %H:%M'),
                        'location': violation.location,
                        'violation_type': violation.violation_type,
                        'fine_amount': float(violation.fine_amount),
                        'status': violation.status,
                        'plate_number': violation.plate_number or 'N/A',
                        'vehicle_type': violation.vehicle_type or 'N/A'
                    })
                data['violations'] = violations_data
                logger.info(f"Found {len(violations_data)} violations for {user.get_full_name()}")
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
    from django.utils import timezone
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