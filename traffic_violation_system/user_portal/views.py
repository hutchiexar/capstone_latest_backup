import logging
from decimal import Decimal
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.http import HttpResponseNotAllowed, JsonResponse, HttpResponseRedirect, HttpResponse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth.models import User
from django.urls import reverse
from django.db.utils import IntegrityError
from django.utils.timesince import timesince
from traffic_violation_system.educational.models import (
    EducationalCategory, 
    EducationalTopic, 
    TopicAttachment, 
    UserBookmark, 
    UserProgress
)
from django.template.loader import render_to_string
import json
import re
from django.db import connection

from traffic_violation_system.models import (
    Violation, 
    Payment,
    Vehicle,
    ViolatorQRHash,
    Driver
)
from ..forms import PaymentForm
from .models import VehicleRegistration, UserReport, DriverApplication, UserNotification

@login_required
def user_dashboard(request):
    """View for the user dashboard, showing a summary of violations, vehicles, and other user info."""
    
    # Get the current user and their profile
    user = request.user
    profile = user.userprofile
    
    # Check for direct violations
    direct_violations = Violation.objects.filter(user_account=user)
    
    # Raw SQL query for more direct debugging
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM traffic_violation_system_violation WHERE user_account_id = %s",
            [user.id]
        )
        raw_count = cursor.fetchone()[0]
    
    # Get violations linked to this user's license number and user account
    # Use the UserViolationManager to ensure we only get violations for this user
    all_violations = Violation.user_violations.get_user_violations(user).order_by('-violation_date')
    
    # Get the 5 most recent violations for the dashboard
    recent_violations = all_violations[:5]
    
    # Count total and active violations
    total_violations_count = all_violations.count()
    active_violations_count = all_violations.filter(
        Q(status='PENDING') | Q(status='APPROVED') | Q(status='ADJUDICATED')
    ).count()
    
    # Sum of amounts for paid violations
    total_paid = all_violations.filter(status='PAID').aggregate(
        total=Sum('fine_amount')
    )['total'] or Decimal('0.00')
    
    # Calculate violations due soon (within 7 days)
    seven_days_from_now = timezone.now().date() + timedelta(days=7)
    due_soon_count = all_violations.filter(
        Q(status='PENDING') | Q(status='APPROVED') | Q(status='ADJUDICATED'),
        payment_due_date__lte=seven_days_from_now,
        payment_due_date__gte=timezone.now().date()
    ).count()
    
    # Get the user's vehicles
    vehicles = VehicleRegistration.objects.filter(user=user)
    
    # Get recent notifications
    recent_notifications = UserNotification.objects.filter(
        user=user
    ).order_by('-created_at')[:3]
    
    # Check for registered QR hashes
    qr_hashes = ViolatorQRHash.objects.filter(user_account=user)
    
    context = {
        'profile': profile,
        'total_violations_count': total_violations_count,
        'active_violations_count': active_violations_count,
        'total_paid': total_paid,
        'due_soon_count': due_soon_count,
        'recent_violations': recent_violations,
        'vehicles': vehicles,
        'recent_notifications': recent_notifications,
        # Handle unread notification count for the notification badge
        'unread_notification_count': UserNotification.objects.filter(
            user=user, is_read=False
        ).count(),
    }
    
    return render(request, 'user_portal/dashboard.html', context)

@login_required
def user_violations(request):
    """
    Display a list of all user violations (includes both regular and NCAP violations).
    """
    user = request.user
    
    # Get direct violations count
    direct_violations_count = Violation.objects.filter(user_account=user).count()
    
    # Check database for any violation with user_account field set
    with connection.cursor() as cursor:
        # This will work for both MySQL and SQLite
        cursor.execute("SELECT COUNT(*) FROM traffic_violation_system_violation WHERE user_account_id = %s", [user.id])
        raw_count = cursor.fetchone()[0]
    
    # Get violations linked to this user's license number and user account
    # Use the UserViolationManager to ensure we only get violations for this user
    violations = Violation.user_violations.get_user_violations(user).order_by('-violation_date')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        violations = violations.filter(
            Q(violation_type__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(novr_number__icontains=search_query) |
            Q(pin_number__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        violations = violations.filter(status=status_filter)
        
    # Separate NCAP and regular violations
    # NCAP violations have images, regular ones don't
    ncap_violations = violations.filter(
        Q(image__isnull=False, image__gt='') | 
        Q(driver_photo__isnull=False, driver_photo__gt='') | 
        Q(vehicle_photo__isnull=False, vehicle_photo__gt='') | 
        Q(secondary_photo__isnull=False, secondary_photo__gt='')
    )
    
    # For regular violations, ensure all image fields are either NULL or empty
    regular_violations = violations.exclude(
        Q(image__isnull=False, image__gt='') | 
        Q(driver_photo__isnull=False, driver_photo__gt='') | 
        Q(vehicle_photo__isnull=False, vehicle_photo__gt='') | 
        Q(secondary_photo__isnull=False, secondary_photo__gt='')
    )
    
    # Get the active tab from the request, default to 'all'
    active_tab = request.GET.get('tab', 'all')
    
    # Determine which violations to paginate based on the active tab
    if active_tab == 'regular':
        violations_to_paginate = regular_violations
    elif active_tab == 'ncap':
        violations_to_paginate = ncap_violations
    else:
        violations_to_paginate = violations
    
    # Pagination
    paginator = Paginator(violations_to_paginate, 10)  # 10 items per page
    page = request.GET.get('page')
    
    try:
        violations_page = paginator.page(page)
    except PageNotAnInteger:
        violations_page = paginator.page(1)
    except EmptyPage:
        violations_page = paginator.page(paginator.num_pages)
    
    # Prepare status choices for filter dropdown
    status_choices = dict(Violation.STATUS_CHOICES)
    
    # Check if coming from print form
    if request.GET.get('printed', False):
        # messages.success(request, "The violation ticket was successfully printed.")
        pass  # No action needed
    
    context = {
        'title': 'My Violations',
        'violations': violations_page,
        'total_count': violations.count(),
        'regular_count': regular_violations.count(),
        'ncap_count': ncap_violations.count(),
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': status_choices,
        'active_tab': active_tab,
    }
    
    return render(request, 'user_portal/violations.html', context)

@login_required
def user_ncap_violations(request):
    """
    Display a list of the user's NCAP violations (with camera evidence).
    """
    user = request.user
    
    # Get violations linked to this user's license number and user account
    # Use the UserViolationManager to ensure we only get violations for this user
    violations = Violation.user_violations.get_user_violations(user).order_by('-violation_date')
    
    # Initialize the query for NCAP violations 
    from django.db.models import Q
    ncap_query = (
        Q(image__isnull=False, image__gt='') | 
        Q(driver_photo__isnull=False, driver_photo__gt='') | 
        Q(vehicle_photo__isnull=False, vehicle_photo__gt='') | 
        Q(secondary_photo__isnull=False, secondary_photo__gt='')
    )
    
    # If user is a driver, also include violations assigned to their PD number as NCAP violations
    if hasattr(user, 'userprofile') and user.userprofile.is_driver:
        try:
            from traffic_violation_system.models import Driver
            drivers = Driver.objects.filter(
                first_name=user.first_name,
                last_name=user.last_name
            )
            if drivers.exists():
                driver = drivers.first()
                if driver.new_pd_number:
                    ncap_query |= Q(pd_number=driver.new_pd_number)
        except Exception:
            # If there's an error, just continue without this part of the filter
            pass
            
    # Filter to only include NCAP violations using the built query
    violations = violations.filter(ncap_query)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        violations = violations.filter(
            Q(violation_type__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(novr_number__icontains=search_query) |
            Q(pin_number__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        violations = violations.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(violations, 10)  # 10 items per page
    page = request.GET.get('page')
    
    try:
        violations_page = paginator.page(page)
    except PageNotAnInteger:
        violations_page = paginator.page(1)
    except EmptyPage:
        violations_page = paginator.page(paginator.num_pages)
    
    # Prepare status choices for filter dropdown
    status_choices = dict(Violation.STATUS_CHOICES)
    
    # Check if coming from successful violation save or print operation
    if request.session.pop('ncap_violation_saved', False):
        messages.success(request, "NCAP violation has been successfully recorded.")
    
    # Check if redirected from print form
    if request.GET.get('printed', False):
        # messages.success(request, "The NCAP violation was successfully printed.")
        pass  # No action needed
    
    context = {
        'title': 'My NCAP Violations',
        'violations': violations_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': status_choices,
    }
    
    return render(request, 'user_portal/ncap_violations.html', context)

@login_required
def violation_detail(request, violation_id):
    """
    Display details of a specific violation.
    Ensures that users can only view their own violations.
    """
    user = request.user
    
    try:
        # Use the custom manager to enforce user-specific access
        user_violations = Violation.user_violations.get_user_violations(user)
        violation = get_object_or_404(user_violations, id=violation_id)
        
        # Check if it's an NCAP violation by checking if any image fields exist AND aren't empty
        is_ncap = (bool(violation.image and violation.image.name) or 
                   bool(violation.driver_photo and violation.driver_photo.name) or 
                   bool(violation.vehicle_photo and violation.vehicle_photo.name) or 
                   bool(violation.secondary_photo and violation.secondary_photo.name))
        
        # Choose the appropriate template
        template_name = 'user_portal/ncap_violation_detail.html' if is_ncap else 'user_portal/violation_detail.html'
        
        context = {
            'violation': violation,
            'is_ncap': is_ncap,
            'title': f'Violation #{violation.id} Details'
        }
        
        return render(request, template_name, context)
    except Exception as e:
        messages.error(request, f"Error loading violation: {str(e)}")
        return redirect('user_portal:user_dashboard')

@login_required
def user_profile(request):
    user_profile = request.user.userprofile
    
    # Get violations linked to this user's license number
    license_violations = Violation.objects.filter(
        violator__license_number=user_profile.license_number
    )
    
    # Get violations linked directly to the user account
    account_violations = Violation.objects.filter(
        user_account=request.user
    )
    
    # Convert QuerySets to lists to handle the intersection in Python
    license_violations_list = list(license_violations)
    account_violations_list = list(account_violations)
    
    # Find unique violation IDs
    all_violation_ids = set(v.id for v in license_violations_list + account_violations_list)
    
    # Count unique violations
    violations_count = len(all_violation_ids)
    
    context = {
        'user_profile': user_profile,
        'violations_count': violations_count,
    }
    
    return render(request, 'user_portal/profile.html', context)

@login_required
def user_settings(request):
    if request.method == 'POST':
        # Handle notification preferences update
        notification_preferences = request.POST.getlist('notifications')
        request.user.userprofile.notification_preferences = notification_preferences
        request.user.userprofile.save()
        messages.success(request, 'Settings updated successfully.')
        return redirect('user_portal:user_settings')
    
    context = {
        'user_profile': request.user.userprofile,
    }
    
    return render(request, 'user_portal/settings.html', context)

@login_required
def user_notifications(request):
    """View for showing all user notifications with pagination"""
    notifications = UserNotification.objects.filter(user=request.user).order_by('-created_at')
    
    # Pagination - 20 notifications per page
    paginator = Paginator(notifications, 20)
    page = request.GET.get('page', 1)
    
    try:
        notifications = paginator.page(page)
    except PageNotAnInteger:
        notifications = paginator.page(1)
    except EmptyPage:
        notifications = paginator.page(paginator.num_pages)
    
    context = {
        'notifications': notifications,
        'page_obj': notifications,
    }
    
    return render(request, 'user_portal/notifications.html', context)

@login_required
def file_report(request):
    if request.method == 'POST':
        report_type = request.POST.get('type')
        subject = request.POST.get('subject')
        description = request.POST.get('description')
        location = request.POST.get('location')
        incident_date = request.POST.get('incident_date')
        attachment = request.FILES.get('attachment')
        
        report = UserReport.objects.create(
            user=request.user,
            type=report_type,
            subject=subject,
            description=description,
            location=location,
            incident_date=incident_date,
            attachment=attachment
        )
        
        # Don't use Django messages, instead add a URL parameter for SweetAlert
        return redirect(f"{reverse('user_portal:user_dashboard')}?report=success")
    
    context = {
        'report_types': UserReport.REPORT_TYPES,
    }
    
    return render(request, 'user_portal/file_report.html', context)

@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(
        UserNotification,
        id=notification_id,
        user=request.user
    )
    notification.is_read = True
    notification.save()
    
    return redirect(request.META.get('HTTP_REFERER', 'user_portal:user_dashboard'))

@login_required
def mark_all_notifications_read(request):
    """API endpoint to mark all user notifications as read"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    
    try:
        # Mark all unread notifications as read
        UserNotification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)
        
        return JsonResponse({
            'status': 'success',
            'message': 'All notifications marked as read'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        }, status=500)

@login_required
def edit_profile(request):
    if request.method == 'POST':
        try:
            user = request.user
            user_profile = user.userprofile

            # Update user information
            user.first_name = request.POST.get('first_name')
            user.last_name = request.POST.get('last_name')
            user.email = request.POST.get('email')
            user.save()

            # Update profile information - fix the field name to match the form
            user_profile.contact_number = request.POST.get('contact_number')
            user_profile.license_number = request.POST.get('license_number')
            user_profile.address = request.POST.get('address')
            
            # Save the new fields
            user_profile.birthdate = request.POST.get('birthdate') or None
            user_profile.emergency_contact_name = request.POST.get('emergency_contact_name')
            user_profile.emergency_contact = request.POST.get('emergency_contact')
            user_profile.emergency_contact_number = request.POST.get('emergency_contact_number')

            if 'avatar' in request.FILES:
                user_profile.avatar = request.FILES['avatar']

            user_profile.save()

            # Check if this is an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'Profile updated successfully!'})
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('user_portal:user_profile')
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': f'Error updating profile: {str(e)}'}, status=400)
            
            messages.error(request, f'Error updating profile: {str(e)}')
            return redirect('user_portal:edit_profile')

    return redirect('user_portal:user_profile')

@login_required
def change_password(request):
    if request.method == 'POST':
        try:
            current_password = request.POST.get('current_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')

            # Check if current password is correct
            if not request.user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
                return redirect('user_portal:user_settings')

            # Check if new passwords match
            if new_password1 != new_password2:
                messages.error(request, 'New passwords do not match.')
                return redirect('user_portal:user_settings')

            # Change password
            request.user.set_password(new_password1)
            request.user.save()

            # Update session to prevent logout
            update_session_auth_hash(request, request.user)

            messages.success(request, 'Password changed successfully.')
        except Exception as e:
            messages.error(request, f'Error changing password: {str(e)}')

    return redirect('user_portal:user_settings')

@login_required
def delete_account(request):
    if request.method == 'POST':
        try:
            confirmation = request.POST.get('confirmation')
            if confirmation != 'DELETE':
                messages.error(request, 'Please type DELETE to confirm account deletion.')
                return redirect('user_portal:user_settings')

            # Delete the user account
            request.user.delete()
            messages.success(request, 'Your account has been deleted successfully.')
            return redirect('landing_home')
        except Exception as e:
            messages.error(request, f'Error deleting account: {str(e)}')

    return redirect('user_portal:user_settings')

@login_required
def vehicle_list(request):
    vehicles = VehicleRegistration.objects.filter(user=request.user)
    return render(request, 'user_portal/vehicles.html', {'vehicles': vehicles})

@login_required
def register_vehicle(request):
    if request.method == 'POST':
        try:
            # Log registration attempt for debugging
            print(f"Vehicle registration attempt by user: {request.user.username} ({request.user.id})")
            
            # Validate required fields first 
            required_fields = ['or_number', 'cr_number', 'plate_number', 'vehicle_type', 
                              'make', 'model', 'year_model', 'color', 'classification',
                              'registration_date', 'expiry_date']
            
            for field in required_fields:
                if not request.POST.get(field):
                    field_name = field.replace('_', ' ').title()
                    print(f"Missing required field: {field_name}")
                    raise KeyError(f"The {field_name} is required")
            
            # Validate date formats
            try:
                registration_date = datetime.strptime(request.POST['registration_date'], '%Y-%m-%d').date()
                expiry_date = datetime.strptime(request.POST['expiry_date'], '%Y-%m-%d').date()
                
                # Validate expiry date is after registration date
                if expiry_date <= registration_date:
                    print(f"Date validation error: Expiry date ({expiry_date}) is not after registration date ({registration_date})")
                    raise ValueError("The expiry date must be after the registration date")
                
                # Validate year model is a valid year
                year_model = int(request.POST['year_model'])
                current_year = datetime.now().year
                if year_model < 1900 or year_model > current_year + 1:
                    print(f"Year model validation error: {year_model} is not between 1900 and {current_year + 1}")
                    raise ValueError(f"The year model must be between 1900 and {current_year + 1}")
                
                # Validate capacity if provided
                capacity = 4  # Default capacity
                if request.POST.get('capacity'):
                    capacity = int(request.POST.get('capacity'))
                    if capacity <= 0:
                        print(f"Capacity validation error: {capacity} is less than or equal to 0")
                        raise ValueError("Capacity must be at least 1")
                
            except ValueError as e:
                if "expiry date must be after" in str(e):
                    raise ValueError(str(e))
                elif "year model" in str(e):
                    raise ValueError(str(e))
                elif "Capacity must be" in str(e):
                    raise ValueError(str(e))
                else:
                    print(f"Date format error: {str(e)}")
                    raise ValueError("Please check the date format. It should be YYYY-MM-DD.")
            
            # Check for file upload
            if 'or_cr_image' not in request.FILES:
                print("Missing OR/CR image file")
                raise KeyError("OR/CR Image file is missing")
                
            # Validate file
            file = request.FILES['or_cr_image']
            # Validate file size (5MB max)
            if file.size > 5 * 1024 * 1024:
                print(f"File size too large: {file.size / (1024 * 1024):.2f}MB exceeds 5MB limit")
                raise ValueError(f"The image file is too large ({file.size / (1024 * 1024):.2f}MB). Maximum size is 5MB.")
            
            # Validate file type
            valid_types = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf']
            if file.content_type not in valid_types:
                print(f"Invalid file type: {file.content_type}")
                raise ValueError(f"Please upload a valid file type (JPG, PNG, or PDF). You uploaded: {file.content_type}")
            
            # Check for duplicate records before creating
            plate_check = VehicleRegistration.objects.filter(plate_number=request.POST['plate_number']).exists()
            if plate_check:
                print(f"Duplicate plate number: {request.POST['plate_number']}")
                raise IntegrityError("Plate number already exists", None, None)
                
            or_check = VehicleRegistration.objects.filter(or_number=request.POST['or_number']).exists()
            if or_check:
                print(f"Duplicate OR number: {request.POST['or_number']}")
                raise IntegrityError("OR number already exists", None, None)
                
            cr_check = VehicleRegistration.objects.filter(cr_number=request.POST['cr_number']).exists()
            if cr_check:
                print(f"Duplicate CR number: {request.POST['cr_number']}")
                raise IntegrityError("CR number already exists", None, None)
            
            # Create new vehicle registration
            vehicle = VehicleRegistration(
                user=request.user,
                or_number=request.POST['or_number'],
                cr_number=request.POST['cr_number'],
                plate_number=request.POST['plate_number'],
                vehicle_type=request.POST['vehicle_type'],
                make=request.POST['make'],
                model=request.POST['model'],
                year_model=request.POST['year_model'],
                color=request.POST['color'],
                classification=request.POST['classification'],
                registration_date=registration_date,
                expiry_date=expiry_date,
                is_active='is_active' in request.POST
            )
            
            # Set capacity if the field exists in the model
            try:
                vehicle.capacity = capacity
            except:
                pass  # Field might not exist yet
            
            # Set the OR/CR image
            vehicle.or_cr_image = file
            
            vehicle.save()
            print(f"Vehicle registered successfully: {vehicle.plate_number} (ID: {vehicle.id})")
            
            # Use URL parameter for success message instead of Django messages
            return redirect(f"{reverse('user_portal:vehicle_list')}?register=success")
            
        except KeyError as e:
            # Missing required field
            missing_field = str(e).strip("'")
            if "The " in missing_field:
                error_message = missing_field
            else:
                field_name = missing_field.replace('_', ' ').title()
                error_message = f"Please provide the {field_name} field."
            
        except ValueError as e:
            # Friendly messages for common value errors
            error_message = str(e)
            if "time data" in error_message or "format" in error_message:
                error_message = "Please provide a valid date in the correct format (YYYY-MM-DD)."
            elif "invalid literal for int()" in error_message:
                error_message = "Please provide a valid number for the Year Model."
            
        except IntegrityError as e:
            # More specific duplicate entry messages
            error_str = str(e).lower()
            if 'unique constraint' in error_str or 'duplicate key' in error_str or 'plate number already exists' in error_str:
                if 'plate_number' in error_str or 'plate number already exists' in error_str:
                    error_message = "This plate number is already registered in our system. If this is your vehicle, it may have been registered previously."
                elif 'or_number' in error_str or 'or number already exists' in error_str:
                    error_message = "This OR number is already registered in our system. Please check if you entered the correct number from your OR/CR."
                elif 'cr_number' in error_str or 'cr number already exists' in error_str:
                    error_message = "This CR number is already registered in our system. Please check if you entered the correct number from your OR/CR."
                else:
                    error_message = "This vehicle information is already in our system. Please check your OR/CR details."
            else:
                error_message = "There was a problem with your vehicle information. Please double-check all fields."
        
        except Exception as e:
            # File upload errors and other issues
            error_str = str(e).lower()
            if "image" in error_str or "file" in error_str or hasattr(e, '__module__') and 'multipart' in e.__module__.lower():
                error_message = "There was a problem with your OR/CR image. Please make sure it's a valid file (JPG, PNG, PDF) and not too large (max 5MB)."
            elif "database" in error_str or hasattr(e, '__module__') and e.__module__ == 'django.db.utils':
                error_message = "Our system is experiencing technical difficulties. Please try again in a few minutes."
                # Log the database error for administrators
                print(f"DATABASE ERROR during vehicle registration: {str(e)}")
            else:
                # Log the actual error for debugging but show a friendly message to the user
                print(f"Vehicle registration error: {type(e).__name__}: {str(e)}")
                error_message = f"Something went wrong with your vehicle registration: {str(e)}"
            
        # Render the form again with the error message and previous data
        return render(request, 'user_portal/register_vehicle.html', {
            'vehicle_classifications': [
                ('Private', 'Private'),
                ('Public', 'Public'),
                ('Government', 'Government'),
                ('Commercial', 'Commercial')
            ],
            'error_message': error_message,
            'form_data': request.POST  # Include the form data to repopulate fields
        })
            
    return render(request, 'user_portal/register_vehicle.html', {
        'vehicle_classifications': [
            ('Private', 'Private'),
            ('Public', 'Public'),
            ('Government', 'Government'),
            ('Commercial', 'Commercial')
        ]
    })

@login_required
def vehicle_detail(request, vehicle_id):
    vehicle = get_object_or_404(VehicleRegistration, id=vehicle_id, user=request.user)
    response_data = {
        'id': vehicle.id,
        'or_number': vehicle.or_number,
        'cr_number': vehicle.cr_number,
        'plate_number': vehicle.plate_number,
        'vehicle_type': vehicle.vehicle_type,
        'make': vehicle.make,
        'model': vehicle.model,
        'year_model': vehicle.year_model,
        'color': vehicle.color,
        'classification': vehicle.classification,
        'registration_date': vehicle.registration_date.strftime('%Y-%m-%d'),
        'expiry_date': vehicle.expiry_date.strftime('%Y-%m-%d'),
        'or_cr_image_url': vehicle.or_cr_image.url if vehicle.or_cr_image else None
    }
    
    # Add capacity if available
    try:
        response_data['capacity'] = vehicle.capacity
    except:
        response_data['capacity'] = 4  # Default capacity
        
    return JsonResponse(response_data)

@user_passes_test(lambda u: u.is_staff)
def user_management(request):
    """Custom user management view that shows regular users and their registered vehicles"""
    # Get query parameters
    search_query = request.GET.get('search', '')
    has_vehicles = request.GET.get('has_vehicles', '')
    
    # Start with regular users only (with role 'USER')
    users = User.objects.filter(
        userprofile__role='USER',
        is_superuser=False
    ).order_by('-date_joined')
    
    # Apply search if provided
    if search_query:
        users = users.filter(
            username__icontains=search_query
        ) | users.filter(
            email__icontains=search_query
        ) | users.filter(
            first_name__icontains=search_query
        ) | users.filter(
            last_name__icontains=search_query
        ).filter(userprofile__role='USER')  # Make sure search results are also regular users
    
    # Filter by vehicle ownership if requested
    if has_vehicles == 'yes':
        users = users.annotate(
            vehicle_count=Count('vehicleregistration')
        ).filter(vehicle_count__gt=0)
    elif has_vehicles == 'no':
        users = users.annotate(
            vehicle_count=Count('vehicleregistration')
        ).filter(vehicle_count=0)
    
    # Collect detailed user data
    user_data = []
    for user in users:
        vehicles = VehicleRegistration.objects.filter(user=user)
        violations_count = 0
        
        # If user has a profile with a license number, count violations
        try:
            if hasattr(user, 'userprofile') and user.userprofile.license_number:
                violations_count = Violation.objects.filter(
                    violator__license_number=user.userprofile.license_number
                ).count()
        except:
            pass
        
        user_data.append({
            'user': user,
            'vehicles': vehicles,
            'vehicle_count': vehicles.count(),
            'active_vehicles': vehicles.filter(is_active=True).count(),
            'violations_count': violations_count,
            'joined_days_ago': (timezone.now().date() - user.date_joined.date()).days
        })
    
    # Handle pagination
    paginator = Paginator(user_data, 10)  # 10 users per page
    page = request.GET.get('page', 1)
    
    try:
        paginated_user_data = paginator.page(page)
    except PageNotAnInteger:
        paginated_user_data = paginator.page(1)
    except EmptyPage:
        paginated_user_data = paginator.page(paginator.num_pages)
    
    context = {
        'user_data': paginated_user_data,
        'search_query': search_query,
        'has_vehicles': has_vehicles,
        'total_users': users.count(),
        'page_obj': paginated_user_data,
    }
    
    return render(request, 'user_portal/admin/user_management.html', context)

@login_required
def regular_users_list(request):
    """View for displaying only regular users. Access restricted to admin, supervisor, and enforcer roles."""
    # Check if user has permission to access this page
    if not hasattr(request.user, 'userprofile') or request.user.userprofile.role not in ['ADMIN', 'SUPERVISOR', 'ENFORCER']:
        return redirect('admin_dashboard')
    
    # Get regular users only
    regular_users = User.objects.filter(
        userprofile__role='USER',
        is_superuser=False
    ).order_by('-date_joined')
    
    # Calculate stats for the dashboard
    active_users = regular_users.filter(is_active=True).count()
    current_month = timezone.now().month
    current_year = timezone.now().year
    new_this_month = regular_users.filter(
        date_joined__month=current_month,
        date_joined__year=current_year
    ).count()
    with_license = regular_users.filter(
        userprofile__license_number__isnull=False
    ).exclude(
        userprofile__license_number=''
    ).count()
    
    # Prepare detailed user data
    user_data = []
    for user in regular_users:
        user_data.append({
            'user': user,
            'joined_days_ago': (timezone.now().date() - user.date_joined.date()).days
        })
    
    context = {
        'users': user_data,
        'active_users': active_users,
        'new_this_month': new_this_month,
        'with_license': with_license,
    }
    
    return render(request, 'user_portal/admin/user_list.html', context)

@login_required
def notification_detail(request, notification_id):
    """API endpoint to get notification details"""
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return redirect('user_portal:user_notifications')
    
    try:
        notification = get_object_or_404(
            UserNotification,
            id=notification_id,
            user=request.user
        )
        
        # Format the created_at date for display
        created_at_formatted = notification.created_at.strftime('%b %d, %Y %I:%M %p')
        
        # Check if this notification is related to an announcement (has reference_id and type SYSTEM)
        announcement_content = None
        announcement_title = None
        if notification.type == 'SYSTEM' and notification.reference_id:
            try:
                from traffic_violation_system.models import Announcement
                announcement = Announcement.objects.filter(id=notification.reference_id).first()
                if announcement:
                    announcement_content = announcement.content
                    announcement_title = announcement.title
            except Exception as e:
                print(f"Error fetching announcement: {str(e)}")
        
        # Return notification details as JSON
        response_data = {
            'id': notification.id,
            'type': notification.type,
            'message': notification.message,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
            'created_at_formatted': created_at_formatted,
            'reference_id': notification.reference_id,
            'type_display': notification.get_type_display(),
            'icon': notification.get_icon(),
        }
        
        # Add announcement content and title if available
        if announcement_content:
            response_data['announcement_content'] = announcement_content
        if announcement_title:
            response_data['announcement_title'] = announcement_title
        
        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
def load_more_notifications(request):
    """API endpoint to load more notifications"""
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return redirect('user_portal:user_notifications')
    
    try:
        offset = int(request.GET.get('offset', 0))
        limit = int(request.GET.get('limit', 10))  # Increased default limit to 10
        
        # Get notifications with pagination
        notifications = UserNotification.objects.filter(
            user=request.user
        ).order_by('-created_at')[offset:offset+limit+1]  # Get one extra to check if there are more
        
        # Check if there are more notifications
        has_more = len(notifications) > limit
        if has_more:
            notifications = notifications[:limit]  # Remove the extra item
        
        # Format notifications for the response
        formatted_notifications = []
        for notification in notifications:
            # Calculate time ago (similar to Django's timesince template filter)
            time_ago = timesince(notification.created_at)
            
            formatted_notifications.append({
                'id': notification.id,
                'type': notification.type,
                'message': notification.message,
                'is_read': notification.is_read,
                'reference_id': notification.reference_id,
                'icon': notification.get_icon(),
                'time_ago': time_ago
            })
        
        return JsonResponse({
            'notifications': formatted_notifications,
            'has_more': has_more,
            'total_count': UserNotification.objects.filter(user=request.user).count(),
            'offset': offset,
            'next_offset': offset + limit if has_more else None
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in load_more_notifications: {error_details}")
        return JsonResponse({
            'success': False,
            'message': str(e),
            'error_details': str(error_details) if request.user.is_staff else None
        }, status=500)

@login_required
def create_test_notification(request):
    """Debug endpoint to create test notifications for the current user"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'User not authenticated'}, status=401)
    
    try:
        # Create a test notification
        notification_types = ['SYSTEM', 'VIOLATION', 'PAYMENT', 'STATUS']
        import random
        notification_type = random.choice(notification_types)
        
        # Create messages based on notification type
        messages = {
            'SYSTEM': 'This is a test system notification. Your account settings have been updated.',
            'VIOLATION': 'You have received a new traffic violation ticket. <b>Please check your violations page</b>.',
            'PAYMENT': 'Your payment of ₱1,500.00 for Violation #12345 has been <b>successfully processed</b>.',
            'STATUS': 'The status of your report #54321 has been updated to <span class="text-success">Resolved</span>.'
        }
        
        # Create the notification
        notification = UserNotification.objects.create(
            user=request.user,
            type=notification_type,
            message=messages[notification_type],
            is_read=False,
            reference_id=random.randint(1000, 9999)
        )
        
        print(f"Debug: Created test notification ID {notification.id} of type {notification_type} for user {request.user.username}")
        
        # Log the current notification count for this user
        notification_count = UserNotification.objects.filter(
            user=request.user
        ).count()
        
        unread_count = UserNotification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        print(f"Debug: User {request.user.username} now has {notification_count} notifications ({unread_count} unread)")
        
        return JsonResponse({
            'status': 'success',
            'message': f'Test notification created ({notification_type})',
            'notification_id': notification.id,
            'total_count': notification_count,
            'unread_count': unread_count
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error creating test notification: {error_details}")
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'error_details': str(error_details)
        }, status=500)

# Fix the user_notifications context processor by checking if user is properly authenticated
def debug_notifications(request):
    """Debug view to check notification system status"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'User not authenticated'}, status=401)
    
    try:
        # Get the context data similar to the context processor
        all_notifications = UserNotification.objects.filter(user=request.user).order_by('-created_at')
        recent_notifications = all_notifications[:10]
        
        unread_count = UserNotification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        # Format notifications for readability
        formatted_notifications = []
        for notif in recent_notifications:
            formatted_notifications.append({
                'id': notif.id,
                'type': notif.type,
                'message': notif.message,
                'is_read': notif.is_read,
                'created_at': notif.created_at.isoformat(),
                'age': timesince(notif.created_at)
            })
        
        return JsonResponse({
            'status': 'success',
            'user_authenticated': request.user.is_authenticated,
            'username': request.user.username,
            'total_notifications': all_notifications.count(),
            'unread_notifications': unread_count,
            'recent_notifications': formatted_notifications,
            'showing_count': len(formatted_notifications)
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in debug_notifications: {error_details}")
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'error_details': str(error_details)
        }, status=500)

# Educational Materials Views
@login_required
def education_topics(request):
    """Display a list of all educational topics available to the user."""
    categories = EducationalCategory.objects.annotate(
        topics_count=Count('topics', filter=Q(topics__is_published=True))
    ).filter(topics_count__gt=0)
    
    search_query = request.GET.get('q', '')
    category_filter = request.GET.get('category', '')
    
    topics = EducationalTopic.objects.filter(is_published=True)
    
    if search_query:
        topics = topics.filter(
            Q(title__icontains=search_query) | 
            Q(content__icontains=search_query)
        )
    
    if category_filter:
        topics = topics.filter(category_id=category_filter)
    
    # Get user progress for the topics
    user_progress = {}
    progress_objects = UserProgress.objects.filter(
        user=request.user,
        topic__in=topics
    )
    user_progress = {p.topic_id: p.is_completed for p in progress_objects}
    
    # Get user bookmarks
    user_bookmarks = {}
    bookmark_objects = UserBookmark.objects.filter(
        user=request.user,
        topic__in=topics
    )
    user_bookmarks = {b.topic_id: True for b in bookmark_objects}
    
    # Add bookmark and progress info to topics
    topics_with_meta = []
    for topic in topics:
        topic_dict = {
            'topic': topic,
            'is_bookmarked': user_bookmarks.get(topic.id, False),
            'is_completed': user_progress.get(topic.id, False)
        }
        topics_with_meta.append(topic_dict)
    
    recently_added = EducationalTopic.objects.filter(is_published=True).order_by('-created_at')[:5]
    
    context = {
        'categories': categories,
        'topics': topics_with_meta,
        'recently_added': recently_added,
        'search_query': search_query,
        'category_filter': category_filter,
    }
    return render(request, 'user_portal/educational/topic_list.html', context)


@login_required
def education_topic_detail(request, topic_id):
    """Display a single educational topic in detail."""
    topic = get_object_or_404(EducationalTopic, id=topic_id, is_published=True)
    attachments = TopicAttachment.objects.filter(topic=topic)
    
    # Get or create user progress
    progress, created = UserProgress.objects.get_or_create(
        user=request.user,
        topic=topic,
        defaults={'last_accessed': timezone.now()}
    )
    
    # Update last_accessed time if not created
    if not created:
        progress.last_accessed = timezone.now()
        progress.save()
    
    # Check if user has bookmarked this topic
    is_bookmarked = UserBookmark.objects.filter(user=request.user, topic=topic).exists()
    
    # Get related topics from the same category
    related_topics = EducationalTopic.objects.filter(
        category=topic.category,
        is_published=True
    ).exclude(id=topic.id)[:5]
    
    # Check for PDF attachment to show in viewer
    is_pdf_content = False
    pdf_url = None
    pdf_attachments = attachments.filter(file_type='PDF')
    if pdf_attachments.exists():
        # If a PDF is attached, set flag to use PDF viewer instead of regular content display
        is_pdf_content = True
        pdf_url = pdf_attachments.first().file.url
    
    context = {
        'topic': topic,
        'attachments': attachments,
        'is_completed': progress.is_completed,
        'is_bookmarked': is_bookmarked,
        'related_topics': related_topics,
        'is_pdf_content': is_pdf_content,
        'pdf_url': pdf_url,
    }
    return render(request, 'user_portal/educational/topic_detail.html', context)


@login_required
def education_bookmarks(request):
    """Display all bookmarked educational topics for the user."""
    bookmarked_topics = UserBookmark.objects.filter(
        user=request.user
    ).select_related('topic', 'topic__category').order_by('-created_at')
    
    context = {
        'bookmarked_topics': bookmarked_topics,
    }
    return render(request, 'user_portal/educational/bookmarks.html', context)


@login_required
def education_progress(request):
    """Display the user's learning progress for educational topics."""
    # Get all user progress records
    completed_topics = UserProgress.objects.filter(
        user=request.user,
        is_completed=True
    ).select_related('topic', 'topic__category').order_by('-completed_at')
    
    in_progress_topics = UserProgress.objects.filter(
        user=request.user,
        is_completed=False
    ).select_related('topic', 'topic__category').order_by('-last_accessed')
    
    # Calculate statistics
    total_count = EducationalTopic.objects.filter(is_published=True).count()
    completed_count = completed_topics.count()
    in_progress_count = in_progress_topics.count()
    
    completion_percentage = 0
    if total_count > 0:
        completion_percentage = int((completed_count / total_count) * 100)
    
    stats = {
        'total_count': total_count,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'completion_percentage': completion_percentage
    }
    
    context = {
        'completed_topics': completed_topics,
        'in_progress_topics': in_progress_topics,
        'stats': stats
    }
    return render(request, 'user_portal/educational/my_progress.html', context)

@login_required
def print_ncap_violation_form(request, violation_id):
    """
    Generate a printable PDF version of an NCAP violation form for the user.
    """
    try:
        # Try to find the violation either by license number or user account
        user = request.user
        license_number = user.userprofile.license_number
        
        try:
            violation = Violation.objects.get(
                id=violation_id,
                violator__license_number=license_number
            )
        except Violation.DoesNotExist:
            violation = get_object_or_404(
                Violation,
                id=violation_id,
                user_account=user
            )
        
        # Check if it's really an NCAP violation (has photos)
        has_photos = bool(violation.image or violation.driver_photo or 
                         violation.vehicle_photo or violation.secondary_photo)
        
        if not has_photos:
            messages.error(request, "This is not an NCAP violation and cannot be printed with this form.")
            return redirect('user_portal:user_violations')
        
        # Pass the violation to the template for printing
        context = {
            'violation': violation,
            'user': user,
            'print_mode': True,
        }
        
        return render(request, 'violations/ncap_print_form.html', context)
        
    except Exception as e:
        messages.error(request, f"Error generating printable form: {str(e)}")
        return redirect('user_portal:user_violations')

@login_required
def driver_apply(request):
    """
    View for users to apply as a driver by submitting required documents.
    This view handles both GET requests (display application form) and POST requests (submit application).
    """
    user = request.user
    
    # Check if user has already submitted an application that's pending or approved
    
    # Check if user already has an active application
    existing_applications = DriverApplication.objects.filter(
        user=user
    ).exclude(status='REJECTED')
    
    if existing_applications.exists():
        # Redirect to application status page if already applied
        return redirect('user_portal:driver_application_status')
    
    if request.method == 'POST':
        # Process the form submission
        try:
            # Get form data
            cttmo_seminar_certificate = request.FILES.get('cttmo_seminar_certificate')
            xray_results = request.FILES.get('xray_results')
            medical_certificate = request.FILES.get('medical_certificate')
            police_clearance = request.FILES.get('police_clearance')
            mayors_permit = request.FILES.get('mayors_permit')
            other_documents = request.FILES.get('other_documents')
            
            # Validate required fields
            if not all([cttmo_seminar_certificate, xray_results, medical_certificate, police_clearance, mayors_permit]):
                messages.error(request, "Please provide all required documents.")
                return render(request, 'user_portal/driver_application_form.html')
            
            # Create the application
            application = DriverApplication(
                user=user,
                cttmo_seminar_certificate=cttmo_seminar_certificate,
                xray_results=xray_results,
                medical_certificate=medical_certificate,
                police_clearance=police_clearance,
                mayors_permit=mayors_permit,
                other_documents=other_documents
            )
            application.save()
            
            # Create a notification for admins
            admin_users = User.objects.filter(is_staff=True)
            for admin_user in admin_users:
                UserNotification.objects.create(
                    user=admin_user,
                    type='SYSTEM',
                    message=f"New driver application submitted by {user.get_full_name()} (ID: {application.id})",
                    reference_id=application.id
                )
            
            # Create a confirmation notification for the user
            UserNotification.objects.create(
                user=user,
                type='SYSTEM',
                message="Your driver application has been submitted and is pending review.",
                reference_id=application.id
            )
            
            messages.success(request, "Your application has been submitted successfully and is pending review.")
            return redirect('user_portal:driver_application_status')
            
        except Exception as e:
            messages.error(request, f"An error occurred while submitting your application: {str(e)}")
            return render(request, 'user_portal/driver_application_form.html')
    
    # Display the application form for GET requests
    return render(request, 'user_portal/driver_application_form.html')

@login_required
def driver_application_status(request):
    """
    View for users to check the status of their driver applications.
    """
    user = request.user
    
    # Retrieve all applications for this user, ordered by submission date (newest first)
    applications = DriverApplication.objects.filter(user=user).order_by('-submitted_at')
    
    context = {
        'applications': applications,
    }
    
    return render(request, 'user_portal/driver_application_status.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def driver_applications_manage(request):
    """
    Admin view to manage driver applications.
    This view displays both pending and processed applications.
    """
    # Get all pending applications
    pending_applications = DriverApplication.objects.filter(status='PENDING').order_by('-submitted_at')
    
    # Get processed applications (approved or rejected)
    processed_applications = DriverApplication.objects.exclude(status='PENDING').order_by('-processed_at')
    
    context = {
        'pending_applications': pending_applications,
        'processed_applications': processed_applications,
    }
    
    return render(request, 'user_portal/admin/driver_applications_manage.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def driver_application_review(request, application_id):
    """
    Admin view to review a specific driver application.
    Handles both GET requests (view application details) and POST requests (approve/reject application).
    """
    application = get_object_or_404(DriverApplication, id=application_id)
    
    # For AJAX requests to get application details
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if request.method == 'GET':
            # Return application details as JSON
            user_data = {
                'full_name': application.user.get_full_name(),
                'username': application.user.username,
                'email': application.user.email,
                'phone_number': getattr(application.user.userprofile, 'phone_number', ''),
                'address': getattr(application.user.userprofile, 'address', ''),
            }
            
            application_data = {
                'id': application.id,
                'status': application.status,
                'submitted_at': application.submitted_at.isoformat(),
                'processed_at': application.processed_at.isoformat() if application.processed_at else None,
                'notes': application.notes,
                'processed_by': application.processed_by.get_full_name() if application.processed_by else None,
            }
            
            documents_data = {
                'cttmo_seminar_certificate': application.cttmo_seminar_certificate.url if application.cttmo_seminar_certificate else None,
                'xray_results': application.xray_results.url if application.xray_results else None,
                'medical_certificate': application.medical_certificate.url if application.medical_certificate else None,
                'police_clearance': application.police_clearance.url if application.police_clearance else None,
                'mayors_permit': application.mayors_permit.url if application.mayors_permit else None,
                'other_documents': application.other_documents.url if application.other_documents else None,
            }
            
            return JsonResponse({
                'success': True,
                'user': user_data,
                'application': application_data,
                'documents': documents_data,
            })
        
        elif request.method == 'POST':
            # Process application approval/rejection
            status = request.POST.get('status')
            notes = request.POST.get('notes', '')
            
            if status not in ['APPROVED', 'REJECTED']:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid status. Must be either APPROVED or REJECTED.'
                })
            
            if status == 'REJECTED' and not notes:
                return JsonResponse({
                    'success': False,
                    'message': 'Please provide a reason for rejection.'
                })
            
            # Update the application
            application.mark_as_processed(request.user, status, notes)
            
            return JsonResponse({
                'success': True,
                'message': f'Application has been {status.lower()}.',
                'redirect': reverse('user_portal:driver_applications_manage')
            })
    
    # For regular page requests to view the application
    context = {
        'application': application,
    }
    
    return render(request, 'user_portal/admin/driver_application_review.html', context)

@login_required
def driver_id_card(request):
    """
    Generate a driver ID card for approved drivers.
    Shows both front and back views with a QR code on the back.
    """
    user = request.user
    profile = user.userprofile
    
    # Check if user is an approved driver
    if not profile.is_driver:
        messages.error(request, "You are not an approved driver. Please apply to become a driver first.")
        return redirect('user_portal:driver_apply')
    
    # Get the latest approved application
    try:
        application = DriverApplication.objects.filter(
            user=user,
            status='APPROVED'
        ).latest('processed_at')
    except DriverApplication.DoesNotExist:
        messages.error(request, "No approved driver application found.")
        return redirect('user_portal:user_dashboard')
    
    # Try to get the Driver record to get the PD number
    try:
        driver = Driver.objects.filter(
            first_name=user.first_name,
            last_name=user.last_name
        ).first()
        
        pd_number = driver.new_pd_number if driver else f"PD-{application.id:03d}"
    except Exception as e:
        # Fallback if we can't get the driver record
        pd_number = f"PD-{application.id:03d}"
    
    # QR code data - URL to the driver's public profile
    qr_data = f"{request.build_absolute_uri('/')[:-1]}/driver/{pd_number}/verify"
    
    context = {
        'user': user,
        'profile': profile,
        'application': application,
        'driver_id': pd_number,
        'qr_data': qr_data,
        'issue_date': application.processed_at.date(),
        'expiry_date': application.processed_at.date().replace(year=application.processed_at.date().year + 1)
    }
    
    return render(request, 'user_portal/driver_id_card.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def driver_id_verify(request, driver_id):
    """
    Verify a driver's identity using their ID number.
    This is the endpoint that the QR code points to.
    """
    try:
        # Try to find by Driver.new_pd_number first
        try:
            from traffic_violation_system.models import Driver
            driver_record = Driver.objects.get(new_pd_number=driver_id)
            
            # Now try to find the user associated with this driver
            from django.contrib.auth.models import User
            driver = User.objects.filter(
                first_name=driver_record.first_name,
                last_name=driver_record.last_name
            ).first()
            
            if not driver:
                raise User.DoesNotExist("No matching user found for driver")
                
        except (Driver.DoesNotExist, User.DoesNotExist):
            # Try to find by application ID from the legacy format (PD-{application.id:03d})
            try:
                # Extract the application ID from the driver_id if it follows the legacy format
                match = re.match(r'PD-(\d+)', driver_id)
                
                if match:
                    app_id = int(match.group(1))
                    application = DriverApplication.objects.get(id=app_id, status='APPROVED')
                    driver = application.user
                else:
                    raise DriverApplication.DoesNotExist("Invalid driver ID format")
            except (ValueError, DriverApplication.DoesNotExist):
                raise Exception("Driver not found")
        
        context = {
            'driver': driver,
            'driver_id': driver_id,
            'is_valid': True,
            'profile': driver.userprofile,
            'application': DriverApplication.objects.filter(user=driver, status='APPROVED').latest('processed_at'),
            'now': timezone.now(),
            'driver_record': driver_record if 'driver_record' in locals() else None
        }
    except Exception as e:
        context = {
            'is_valid': False,
            'driver_id': driver_id,
            'now': timezone.now(),
            'error': str(e)
        }
    
    return render(request, 'user_portal/driver_id_verify.html', context) 

@login_required
def view_qr_code(request):
    """
    Display the user's QR code for viewing and printing.
    The QR code can be attached to vehicles for easy scanning by enforcers.
    """
    user = request.user
    profile = user.userprofile
    
    # Check if QR code exists
    if not profile.qr_code:
        # QR code doesn't exist, generate one
        try:
            import qrcode
            from io import BytesIO
            from django.core.files import File
            
            # Generate vehicle/user data to include in QR code
            qr_data = {
                "user_id": user.id,
                "name": user.get_full_name(),
                "license": profile.license_number or "",
                "enforcer_id": profile.enforcer_id or "",
            }
            
            # Add vehicle data if the user has registered vehicles
            vehicles = user.registered_vehicles.filter(is_active=True)
            if vehicles.exists():
                vehicle = vehicles.first()
                qr_data.update({
                    "plate_number": vehicle.plate_number,
                    "vehicle_type": vehicle.vehicle_type,
                    "make": vehicle.make,
                    "model": vehicle.model
                })
            
            # Convert data to string
            qr_content = "\n".join([f"{k}: {v}" for k, v in qr_data.items()])
            
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_content)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, 'PNG')
            
            # Save QR code to profile
            filename = f'qr_code_{user.username}.png'
            profile.qr_code.save(filename, File(buffer), save=True)
            
            messages.success(request, "QR Code generated successfully.")
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating QR code: {str(e)}")
            messages.error(request, "There was a problem generating your QR code. Please try again later.")
            return redirect('user_portal:user_profile')
    
    context = {
        'user': user,
        'profile': profile,
        'page_title': 'Vehicle QR Code'
    }
    
    return render(request, 'user_portal/view_qr_code.html', context) 