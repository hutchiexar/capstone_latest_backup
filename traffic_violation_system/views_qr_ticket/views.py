from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from traffic_violation_system.models import Driver, DriverVehicleAssignment, UserProfile
from django.contrib.auth.models import User
import logging

# Set up logger
logger = logging.getLogger(__name__)

@login_required
def prepare_driver_ticket(request, driver_id):
    """
    Prepares session data for issuing a ticket to a driver identified via QR code
    and redirects to the issue ticket page.
    """
    try:
        # Fetch the driver data
        driver = get_object_or_404(Driver, new_pd_number=driver_id)
        
        # Store all needed data in session
        request.session['ticket_data'] = {
            'driver_id': driver_id,
            'first_name': driver.first_name,
            'last_name': driver.last_name,
            'license_number': driver.license_number,
            'phone_number': driver.contact_number,
            'address': driver.address,
            'data_source': 'driver_qr',
        }
        
        # Fetch vehicle data if available
        vehicles = DriverVehicleAssignment.objects.filter(driver=driver, is_active=True)
        if vehicles.exists():
            vehicle = vehicles.first().vehicle
            request.session['ticket_data'].update({
                'vehicle_type': getattr(vehicle, 'make', getattr(vehicle, 'vehicle_type', '')),
                'plate_number': vehicle.plate_number,
                'color': vehicle.color,
                'classification': getattr(vehicle, 'classification', 'Public'),
                'registration_number': getattr(vehicle, 'registration_number', ''),
                'registration_date': getattr(vehicle, 'registration_date', '').strftime('%Y-%m-%d') 
                    if hasattr(vehicle, 'registration_date') and vehicle.registration_date else '',
                'vehicle_owner': getattr(vehicle.operator, 'full_name', lambda: 'N/A')() 
                    if hasattr(vehicle, 'operator') and vehicle.operator else '',
                'vehicle_owner_address': getattr(vehicle.operator, 'address', '') 
                    if hasattr(vehicle, 'operator') and vehicle.operator else '',
            })
        
        # Save the session explicitly
        request.session.modified = True
        
        # Redirect to the issue direct ticket page
        return redirect('issue_direct_ticket')
        
    except Exception as e:
        messages.error(request, f"Error preparing ticket data: {str(e)}")
        return redirect('driver_verify', driver_id=driver_id)

@login_required
def prepare_user_ticket(request, enforcer_id):
    """
    Prepares session data for issuing a ticket to a user identified via QR code
    and redirects to the issue ticket page.
    """
    try:
        # Fetch the user profile data
        profile = get_object_or_404(UserProfile, enforcer_id=enforcer_id)
        user = profile.user
        
        # Store basic user information in session
        request.session['ticket_data'] = {
            'user_account_id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'license_number': profile.license_number or '',
            'phone_number': profile.phone_number or profile.contact_number or '',
            'address': profile.address or '',
            'data_source': 'user_qr',
        }
        
        # If the user is associated with a driver, get more information
        if profile.is_driver:
            try:
                driver = Driver.objects.filter(
                    Q(first_name__iexact=user.first_name) & 
                    Q(last_name__iexact=user.last_name)
                ).first()
                
                if driver:
                    # Update with driver information
                    request.session['ticket_data'].update({
                        'license_number': driver.license_number or profile.license_number or '',
                        'phone_number': driver.contact_number or profile.contact_number or profile.phone_number or '',
                    })
            except Exception as e:
                # Just log the error but continue
                logger.error(f"Error getting driver info for user {user.username}: {str(e)}")
        
        # Get vehicle information if available
        vehicles = []
        try:
            if hasattr(user, 'registered_vehicles'):
                vehicles = user.registered_vehicles.filter(is_active=True)
            elif profile.is_driver and 'driver' in locals() and driver:
                driver_vehicles = DriverVehicleAssignment.objects.filter(driver=driver, is_active=True)
                if driver_vehicles.exists():
                    vehicles = [dv.vehicle for dv in driver_vehicles]
        except Exception as e:
            logger.error(f"Error getting vehicles for user {user.username}: {str(e)}")
        
        # If we found vehicles, use the first one
        if vehicles:
            vehicle = vehicles[0]
            request.session['ticket_data'].update({
                'vehicle_type': getattr(vehicle, 'make', getattr(vehicle, 'vehicle_type', '')),
                'plate_number': vehicle.plate_number,
                'color': vehicle.color,
                'classification': getattr(vehicle, 'classification', 'Public'),
                'registration_number': getattr(vehicle, 'registration_number', ''),
                'registration_date': getattr(vehicle, 'registration_date', '').strftime('%Y-%m-%d') 
                    if hasattr(vehicle, 'registration_date') and vehicle.registration_date else '',
                'vehicle_owner': getattr(vehicle, 'operator', None) and vehicle.operator.full_name() 
                    if hasattr(vehicle, 'operator') and vehicle.operator else user.get_full_name(),
                'vehicle_owner_address': getattr(vehicle, 'operator', None) and vehicle.operator.address 
                    if hasattr(vehicle, 'operator') and vehicle.operator else profile.address or '',
            })
        
        # Save the session explicitly
        request.session.modified = True
        
        # Redirect to the issue direct ticket page
        return redirect('issue_direct_ticket')
        
    except Exception as e:
        messages.error(request, f"Error preparing ticket data: {str(e)}")
        return redirect('qr_user_data', enforcer_id=enforcer_id) 