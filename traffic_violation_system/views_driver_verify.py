from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from .models import Driver, Vehicle, DriverVehicleAssignment, Violation
from django.db.models import Q
from django.contrib.auth.models import User
from django.db import connection

def search_drivers(request):
    """
    View to search for drivers by name or license number.
    This is used when a driver ID lookup fails.
    """
    query = {}
    results = []
    
    # Get search parameters
    driver_name = request.GET.get('driver_name', '').strip()
    license_number = request.GET.get('license_number', '').strip()
    
    # Only search if at least one parameter is provided
    if driver_name or license_number:
        query_filter = Q()
        
        # Build query based on provided parameters
        if driver_name:
            # Split name into parts to search first and last name
            name_parts = driver_name.split()
            if len(name_parts) == 1:
                # Single word - search both first and last name
                name_part = name_parts[0]
                query_filter |= Q(first_name__icontains=name_part)
                query_filter |= Q(last_name__icontains=name_part)
            else:
                # Multiple words - assume first and last name
                query_filter |= Q(first_name__icontains=name_parts[0])
                query_filter |= Q(last_name__icontains=name_parts[-1])
        
        if license_number:
            query_filter |= Q(license_number__icontains=license_number)
        
        # Execute the query
        drivers = Driver.objects.filter(query_filter).order_by('first_name', 'last_name')
        
        # If no direct hits, try more creative searches
        if not drivers.exists() and driver_name:
            # Try searching with LIKE SQL query for more flexibility
            try:
                with connection.cursor() as cursor:
                    name_search = f"%{driver_name}%"
                    cursor.execute("""
                        SELECT id FROM traffic_violation_system_driver
                        WHERE 
                            LOWER(first_name || ' ' || last_name) LIKE LOWER(%s)
                        LIMIT 20
                    """, [name_search])
                    
                    results = cursor.fetchall()
                    if results:
                        id_list = [r[0] for r in results]
                        drivers = Driver.objects.filter(id__in=id_list)
            except Exception as e:
                print(f"Error in SQL name search: {str(e)}")
        
        results = drivers[:20]  # Limit to 20 results
        
        # If we found exactly one driver, redirect directly to their verification page
        if len(results) == 1:
            driver = results[0]
            return redirect('driver_verify', driver_id=driver.new_pd_number or driver.id)
    
    # If we didn't redirect, render the search results page
    context = {
        'results': results,
        'query': {
            'driver_name': driver_name,
            'license_number': license_number
        },
        'count': len(results)
    }
    
    return render(request, 'drivers/driver_search_results.html', context)

def driver_verify(request, driver_id):
    """
    Public endpoint to verify a driver's identity using their ID number.
    This is the endpoint used by the QR scanner and does not require login.
    """
    legacy_format = False
    similar_drivers = []
    
    try:
        # Try to find by Driver.new_pd_number first
        driver = Driver.objects.get(new_pd_number=driver_id)
        
        # Try to find associated user profile
        user_profile = None
        try:
            # Find a user with the same name as the driver
            matching_user = User.objects.filter(
                Q(first_name=driver.first_name) & Q(last_name=driver.last_name)
            ).first()
            
            if matching_user and hasattr(matching_user, 'userprofile'):
                user_profile = matching_user.userprofile
        except Exception as e:
            # Just log the error and continue without user profile
            print(f"Error finding user profile for driver: {str(e)}")
            pass
        
        # Initialize vehicles as an empty list
        vehicles = []
        
        # Get assigned vehicles
        vehicle_assignments = DriverVehicleAssignment.objects.filter(
            driver=driver,
            is_active=True
        )
        
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
        
        # Get all violations associated with this driver 
        driver_violations = Violation.objects.filter(
            Q(pd_number=driver.new_pd_number) | 
            Q(pd_number=driver.old_pd_number) | 
            Q(violator__license_number=driver.license_number)
        ).order_by('-violation_date')
        
        # Filter to only include pending and adjudicated violations
        driver_violations = [
            violation for violation in driver_violations 
            if getattr(violation, 'status', '').lower() in ['pending', 'adjudicated']
        ]
        
        # Separate violations into regular and NCAP
        ncap_violations = []
        regular_violations = []
        
        # NCAP detection keywords
        ncap_keywords = [
            'helmet', 'no helmet', 'camera', 'ncap', 'photo', 'evidence', 'cctv',
            'speed', 'red light', 'traffic signal', 'stoplight'
        ]
        
        for violation in driver_violations:
            # Check if violation has any image fields (a common indicator of NCAP)
            has_images = False
            if hasattr(violation, 'image') and violation.image:
                has_images = True
            if hasattr(violation, 'driver_photo') and violation.driver_photo:
                has_images = True
            if hasattr(violation, 'vehicle_photo') and violation.vehicle_photo:
                has_images = True
            
            # Check for NCAP based on violation type keywords
            is_ncap_type = False
            violation_type = getattr(violation, 'violation_type', '') or getattr(violation, 'violations', '')
            if violation_type:
                for keyword in ncap_keywords:
                    if keyword.lower() in violation_type.lower():
                        is_ncap_type = True
                        break
            
            # Check for explicit is_ncap field
            has_ncap_field = hasattr(violation, 'is_ncap') and getattr(violation, 'is_ncap', False)
            
            # If any criteria match, consider it NCAP
            if has_images or is_ncap_type or has_ncap_field:
                ncap_violations.append(violation)
            else:
                regular_violations.append(violation)
        
        context = {
            'driver': driver,
            'driver_id': driver_id,
            'is_valid': True,
            'now': timezone.now(),
            'vehicles': vehicles,
            'violations': driver_violations,
            'regular_violations': regular_violations,
            'ncap_violations': ncap_violations,
            'user_profile': user_profile,
            'data': {  # Add a data object for backward compatibility
                'violations': driver_violations,
                'regular_violations': regular_violations,
                'ncap_violations': ncap_violations,
            }
        }
    except Driver.DoesNotExist:
        # Try legacy format or handle the error
        try:
            import re
            
            # Check for legacy PD number format (PD-XXX)
            pd_match = re.match(r'PD-(\d+)', driver_id)
            if pd_match:
                legacy_format = True
                extracted_id = int(pd_match.group(1))
                pd_number_raw = str(extracted_id)
                
                # Create a list of possible formats for the ID
                possible_formats = [
                    pd_number_raw,              # Just the number
                    f"PD-{pd_number_raw}",      # PD-XXX
                    f"PD{pd_number_raw}",       # PDXXX
                    f"PD_{pd_number_raw}",      # PD_XXX
                    f"PD-{pd_number_raw.zfill(6)}", # PD-000XXX (with leading zeros)
                    f"PD{pd_number_raw.zfill(6)}",  # PD000XXX
                    f"PD-{pd_number_raw.zfill(4)}", # PD-00XX
                    f"PD{pd_number_raw.zfill(4)}",  # PD00XX
                ]
                
                # Try multiple lookup strategies
                # 1. Try by ID
                try:
                    driver = Driver.objects.get(id=extracted_id)
                    # If found, return to the beginning to process normally
                    return driver_verify(request, driver.new_pd_number or driver_id)
                except Driver.DoesNotExist:
                    pass
                
                # 2. Try by old_pd_number with various formats
                for format_variant in possible_formats:
                    try:
                        # Exact match first
                        driver = Driver.objects.filter(old_pd_number=format_variant).first()
                        if driver:
                            # If found, return to the beginning to process normally
                            return driver_verify(request, driver.new_pd_number or driver_id)
                        
                        # Then contains match
                        driver = Driver.objects.filter(old_pd_number__contains=format_variant).first()
                        if driver:
                            # If found, return to the beginning to process normally
                            return driver_verify(request, driver.new_pd_number or driver_id)
                    except Exception:
                        pass
                
                # 3. Try finding the driver through violation records
                # Sometimes drivers are recorded in violations but not properly linked
                try:
                    # Check violations for this PD number
                    violations_with_pd = Violation.objects.filter(
                        Q(pd_number__contains=pd_number_raw) |
                        Q(pd_number__contains=f"PD-{pd_number_raw}") |
                        Q(pd_number__contains=f"PD{pd_number_raw}")
                    ).order_by('-violation_date')[:5]
                    
                    # If we found violations, try to get driver info from them
                    if violations_with_pd.exists():
                        # Get the license numbers from these violations
                        license_numbers = set()
                        for violation in violations_with_pd:
                            if hasattr(violation, 'violator') and violation.violator and violation.violator.license_number:
                                license_numbers.add(violation.violator.license_number)
                            
                            # Also get driver names from violations
                            if hasattr(violation, 'violator'):
                                first_name = getattr(violation.violator, 'first_name', '')
                                last_name = getattr(violation.violator, 'last_name', '')
                                if first_name and last_name:
                                    # Try to find driver by name
                                    driver_by_name = Driver.objects.filter(
                                        first_name__iexact=first_name,
                                        last_name__iexact=last_name
                                    ).first()
                                    if driver_by_name:
                                        return driver_verify(request, driver_by_name.new_pd_number or driver_id)
                        
                        # Try to find driver by license numbers from violations
                        for license_number in license_numbers:
                            if license_number:
                                driver_by_license = Driver.objects.filter(
                                    license_number=license_number
                                ).first()
                                if driver_by_license:
                                    return driver_verify(request, driver_by_license.new_pd_number or driver_id)
                    
                except Exception as e:
                    print(f"Error searching violations: {str(e)}")
                    
                # 4. Try direct SQL search for maximum flexibility
                try:
                    with connection.cursor() as cursor:
                        # Find drivers with any field containing the PD number
                        cursor.execute("""
                            SELECT id, first_name, last_name, new_pd_number 
                            FROM traffic_violation_system_driver
                            WHERE 
                                CAST(id AS text) = %s OR
                                old_pd_number LIKE %s OR
                                new_pd_number LIKE %s OR
                                license_number LIKE %s
                        """, [
                            pd_number_raw, 
                            f'%{pd_number_raw}%',
                            f'%{pd_number_raw}%',
                            f'%{pd_number_raw}%'
                        ])
                        results = cursor.fetchall()
                        
                        if results:
                            # Found a match via SQL, use the first one
                            driver_id_found = results[0][0]  # Get ID from first match
                            driver = Driver.objects.get(id=driver_id_found)
                            return driver_verify(request, driver.new_pd_number or driver_id)
                        
                        # Try other variations of the PD number format
                        cursor.execute("""
                            SELECT id, first_name, last_name, new_pd_number 
                            FROM traffic_violation_system_driver
                            WHERE 
                                old_pd_number LIKE %s OR
                                old_pd_number LIKE %s OR
                                new_pd_number LIKE %s OR
                                new_pd_number LIKE %s
                        """, [
                            f'%PD-{pd_number_raw}%',
                            f'%PD{pd_number_raw}%',
                            f'%PD-{pd_number_raw}%',
                            f'%PD{pd_number_raw}%'
                        ])
                        results = cursor.fetchall()
                        
                        if results:
                            # Found a match via SQL, use the first one
                            driver_id_found = results[0][0]  # Get ID from first match
                            driver = Driver.objects.get(id=driver_id_found)
                            return driver_verify(request, driver.new_pd_number or driver_id)
                except Exception as e:
                    print(f"Error in SQL search: {str(e)}")
                
                # 5. Find similar drivers to suggest by ID proximity
                try:
                    similar_drivers = list(Driver.objects.filter(
                        Q(id__gte=extracted_id-10) & Q(id__lte=extracted_id+10)
                    ).exclude(id=extracted_id)[:5])
                    
                    # If no similar drivers by ID, try finding by legacy ID formats
                    if not similar_drivers:
                        # Find drivers with IDs close to the target numerically
                        with connection.cursor() as cursor:
                            cursor.execute("""
                                SELECT id FROM traffic_violation_system_driver
                                WHERE 
                                    CASE 
                                        WHEN old_pd_number ~ '^[0-9]+$' THEN
                                            CAST(old_pd_number AS integer) >= %s AND
                                            CAST(old_pd_number AS integer) <= %s
                                        ELSE FALSE
                                    END
                                ORDER BY CAST(old_pd_number AS integer)
                                LIMIT 5
                            """, [extracted_id-50, extracted_id+50])
                            
                            results = cursor.fetchall()
                            if results:
                                id_list = [r[0] for r in results]
                                similar_drivers = list(Driver.objects.filter(id__in=id_list))
                    
                    # If still no results, try finding by new_pd_number patterns
                    if not similar_drivers:
                        similar_drivers = list(Driver.objects.filter(
                            new_pd_number__contains=pd_number_raw
                        )[:5])
                        
                except Exception as e:
                    print(f"Error finding similar drivers: {str(e)}")
                    
                # If still nothing found, check if any drivers exist in the system at all
                if not similar_drivers:
                    try:
                        # Get a few random drivers to suggest
                        total_drivers = Driver.objects.count()
                        if total_drivers > 0:
                            # Get a few drivers to suggest
                            sample_drivers = Driver.objects.all().order_by('?')[:5]
                            if sample_drivers:
                                similar_drivers = list(sample_drivers)
                    except Exception as e:
                        print(f"Error getting sample drivers: {str(e)}")
                
                raise Driver.DoesNotExist(f"No driver found with ID: {extracted_id}")
            else:
                # Maybe it's just a number without the PD- prefix
                if driver_id.isdigit():
                    try:
                        num_id = int(driver_id)
                        driver = Driver.objects.get(id=num_id)
                        # If found, redirect to proper format
                        return driver_verify(request, driver.new_pd_number or driver_id)
                    except (Driver.DoesNotExist, ValueError):
                        pass
                
                # Try other formats - maybe it's a license number or old PD number
                driver = Driver.objects.filter(
                    Q(license_number=driver_id) | 
                    Q(old_pd_number=driver_id) |
                    Q(old_pd_number__contains=driver_id) |
                    Q(new_pd_number__contains=driver_id)
                ).first()
                
                if driver:
                    # If found with alternate lookup, process with the correct ID
                    return driver_verify(request, driver.new_pd_number or driver_id)
                
                # Try using contains search on both old and new PD numbers
                driver = Driver.objects.filter(
                    Q(old_pd_number__icontains=driver_id) | 
                    Q(new_pd_number__icontains=driver_id)
                ).first()
                
                if driver:
                    return driver_verify(request, driver.new_pd_number or driver_id)
                
                raise Driver.DoesNotExist("Driver ID not recognized in any format")
        except Exception as e:
            error_message = str(e)
            if "matching query does not exist" in error_message.lower():
                error_message = f"No driver found with ID: {driver_id}"
            
            context = {
                'is_valid': False,
                'driver_id': driver_id,
                'legacy_format': legacy_format,
                'similar_drivers': similar_drivers,
                'now': timezone.now(),
                'error': error_message
            }
    except Exception as e:
        context = {
            'is_valid': False,
            'driver_id': driver_id,
            'now': timezone.now(),
            'error': str(e)
        }
    
    return render(request, 'drivers/driver_verify.html', context) 