from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from .models import Driver, Vehicle, DriverVehicleAssignment, Violation

def driver_verify(request, driver_id):
    """
    Public endpoint to verify a driver's identity using their ID number.
    This is the endpoint used by the QR scanner and does not require login.
    """
    try:
        # Try to find by Driver.new_pd_number first
        driver = Driver.objects.get(new_pd_number=driver_id)
        
        # Get assigned vehicles
        vehicle_assignments = DriverVehicleAssignment.objects.filter(
            driver=driver,
            is_active=True
        )
        
        vehicles = []
        for assignment in vehicle_assignments:
            if assignment.vehicle:
                vehicle = assignment.vehicle
                vehicles.append({
                    'plate_number': vehicle.plate_number or 'N/A',
                    'make': getattr(vehicle, 'make', vehicle.vehicle_type) or 'N/A',
                    'model': getattr(vehicle, 'model', '') or 'N/A',
                    'year': getattr(vehicle, 'year_model', '') or 'N/A',
                    'color': vehicle.color or 'N/A',
                    'operator': vehicle.operator.full_name() if vehicle.operator else 'N/A'
                })
        
        # Get violations associated with this driver based on PD number
        driver_violations = Violation.objects.filter(pd_number=driver.new_pd_number).order_by('-violation_date')
        
        context = {
            'driver': driver,
            'driver_id': driver_id,
            'is_valid': True,
            'now': timezone.now(),
            'vehicles': vehicles,
            'violations': driver_violations
        }
    except Driver.DoesNotExist:
        # Try legacy format or handle the error
        try:
            import re
            
            # For older driver ID formats
            match = re.match(r'PD-(\d+)', driver_id)
            if match:
                # Try to find by ID, but this is a fallback
                # Typically this won't work as we need the new_pd_number
                id = int(match.group(1))
                driver = Driver.objects.get(id=id)
                
                # Get violations for legacy format
                driver_violations = Violation.objects.filter(pd_number=driver.new_pd_number).order_by('-violation_date')
                
                context = {
                    'driver': driver,
                    'driver_id': driver_id,
                    'is_valid': True,
                    'now': timezone.now(),
                    'vehicles': [],
                    'violations': driver_violations
                }
            else:
                raise Driver.DoesNotExist("Invalid driver ID format")
        except Exception as e:
            context = {
                'is_valid': False,
                'driver_id': driver_id,
                'now': timezone.now(),
                'error': str(e)
            }
    except Exception as e:
        context = {
            'is_valid': False,
            'driver_id': driver_id,
            'now': timezone.now(),
            'error': str(e)
        }
    
    return render(request, 'drivers/driver_verify.html', context) 