from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from .models import UserNotification, UserReport, VehicleRegistration, OperatorViolationLookup
from traffic_violation_system.models import Violation, Violator, Operator
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.http import HttpResponseNotAllowed, JsonResponse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth.models import User

@login_required
def user_dashboard(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
        
    # Get violations linked to this user's license number
    license_violations = Violation.objects.filter(
        violator__license_number=request.user.userprofile.license_number
    )
    
    # Get violations linked directly to the user account
    account_violations = Violation.objects.filter(
        user_account=request.user
    )
    
    # Combine the querysets - but we'll evaluate them first to avoid filtering issues
    license_violations_list = list(license_violations)
    account_violations_list = list(account_violations)
    
    # Use set operations to get distinct violations from both sources
    all_violations_ids = set(v.id for v in license_violations_list + account_violations_list)
    
    # Calculate statistics directly without using .filter() on a union
    # Count active violations
    active_violations = sum(1 for v in license_violations_list + account_violations_list 
                          if v.id in all_violations_ids and v.status in ['PENDING', 'ADJUDICATED', 'APPROVED'])
    
    # Calculate total paid
    total_paid = sum(v.fine_amount or 0 for v in license_violations_list + account_violations_list 
                   if v.id in all_violations_ids and v.status == 'PAID')
    
    # Calculate violations due soon
    seven_days_from_now = (timezone.now() + timezone.timedelta(days=7)).date()
    due_soon = sum(1 for v in license_violations_list + account_violations_list 
                 if v.id in all_violations_ids and 
                    v.status in ['PENDING', 'ADJUDICATED', 'APPROVED'] and
                    v.payment_due_date and v.payment_due_date <= seven_days_from_now)
    
    # For recent violations, we'll get all violations and sort them in Python
    all_violations = []
    for violation in license_violations_list + account_violations_list:
        if violation.id in all_violations_ids and violation not in all_violations:
            all_violations.append(violation)
    
    # Sort by violation date (descending) and take the first 5
    recent_violations = sorted(all_violations, key=lambda v: v.violation_date, reverse=True)[:5]
    
    # Get recent notifications
    recent_notifications = UserNotification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:5]

    context = {
        'active_violations_count': active_violations,
        'total_paid': total_paid,
        'due_soon_count': due_soon,
        'recent_violations': recent_violations,
        'recent_notifications': recent_notifications,
    }
    
    return render(request, 'user_portal/dashboard.html', context)

@login_required
def user_violations(request):
    # Get violations linked to this user's license number
    license_violations = Violation.objects.filter(
        violator__license_number=request.user.userprofile.license_number
    )
    
    # Get violations linked directly to the user account
    account_violations = Violation.objects.filter(
        user_account=request.user
    )
    
    # Evaluate the querysets to lists to avoid filtering issues
    license_violations_list = list(license_violations)
    account_violations_list = list(account_violations)
    
    # Combine and remove duplicates
    all_violations_ids = set()
    all_violations = []
    
    for violation in license_violations_list + account_violations_list:
        if violation.id not in all_violations_ids:
            all_violations_ids.add(violation.id)
            all_violations.append(violation)
    
    # Sort by violation date (descending)
    all_violations = sorted(all_violations, key=lambda v: v.violation_date or timezone.now().date(), reverse=True)
    
    # Filter by status if provided - we'll do this in Python
    status = request.GET.get('status')
    if status:
        all_violations = [v for v in all_violations if v.status == status]
    
    context = {
        'violations': all_violations,
        'status_choices': Violation.STATUS_CHOICES,
        'current_status': status,
    }
    
    return render(request, 'user_portal/violations.html', context)

@login_required
def violation_detail(request, violation_id):
    # Try to find the violation either by license number or user account
    try:
        # First check if it's linked to the user's license
        violation = Violation.objects.get(
            id=violation_id,
            violator__license_number=request.user.userprofile.license_number
        )
    except Violation.DoesNotExist:
        # If not found, check if it's linked to the user account
        violation = get_object_or_404(
            Violation,
            id=violation_id,
            user_account=request.user
        )
    
    context = {
        'violation': violation,
    }
    
    return render(request, 'user_portal/violation_detail.html', context)

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
        return redirect('user_settings')
    
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
        
        messages.success(request, 'Your report has been submitted successfully.')
        return redirect('user_dashboard')
    
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
    
    return redirect(request.META.get('HTTP_REFERER', 'user_dashboard'))

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
                registration_date=request.POST['registration_date'],
                expiry_date=request.POST['expiry_date']
            )
            
            # Handle OR/CR image upload
            if request.FILES.get('or_cr_image'):
                vehicle.or_cr_image = request.FILES['or_cr_image']
            
            vehicle.save()
            messages.success(request, 'Vehicle registered successfully!')
            return redirect('vehicle_list')
            
        except Exception as e:
            messages.error(request, f'Error registering vehicle: {str(e)}')
            
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
    return JsonResponse({
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
    })

@user_passes_test(lambda u: u.is_staff)
def user_management(request):
    """Custom user management view that shows users and their registered vehicles"""
    # Get query parameters
    search_query = request.GET.get('search', '')
    filter_has_vehicles = request.GET.get('has_vehicles', '')
    
    # Start with all non-superuser users
    users = User.objects.filter(is_superuser=False).order_by('-date_joined')
    
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
        )
    
    # Filter by vehicle ownership if requested
    if filter_has_vehicles == 'yes':
        users = users.annotate(
            vehicle_count=Count('vehicleregistration')
        ).filter(vehicle_count__gt=0)
    elif filter_has_vehicles == 'no':
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
        'filter_has_vehicles': filter_has_vehicles,
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
def operator_lookup(request):
    """View for operator owners to lookup operators and check their violation history"""
    # Check if the user is a vehicle owner
    vehicles = VehicleRegistration.objects.filter(user=request.user)
    
    if not vehicles.exists():
        messages.warning(request, "You need to register a vehicle before you can lookup operators.")
        return redirect('user_portal:vehicle_list')
    
    # For demonstration, get the 5 most recent lookups
    recent_lookups = OperatorViolationLookup.objects.filter(
        vehicle_owner=request.user
    ).order_by('-lookup_date')[:5]
    
    # Check if a search query was passed (from lookup history)
    search_query = request.GET.get('search', '')
    
    context = {
        'recent_lookups': recent_lookups,
        'search_query': search_query,
    }
    
    return render(request, 'user_portal/operator_lookup.html', context)

@login_required
def operator_lookup_search(request):
    """API endpoint to search for operators and return their violation history"""
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    
    # Check if the user is a vehicle owner
    vehicles = VehicleRegistration.objects.filter(user=request.user)
    if not vehicles.exists():
        return JsonResponse({'status': 'error', 'message': 'You must register a vehicle to use this feature'}, status=403)
    
    search_term = request.GET.get('q', '').strip()
    if not search_term:
        return JsonResponse({'status': 'error', 'message': 'Search term is required'}, status=400)
    
    # Search for operators by license number, name, or other identifiers
    operators = []
    
    # If this is a license number search, check User objects with UserProfile
    if len(search_term) > 3:  # Assuming license numbers are at least 4 characters
        # Search for users with matching license numbers in their profiles
        users_with_license = User.objects.filter(
            userprofile__license_number__icontains=search_term
        ).select_related('userprofile')
        
        for user in users_with_license:
            if hasattr(user, 'userprofile') and user.userprofile.license_number:
                # Get violations for this license number
                violations = Violation.objects.filter(
                    violator__license_number=user.userprofile.license_number
                )
                
                # For checking recent violations, convert to date for comparison
                ninety_days_ago = (timezone.now() - timezone.timedelta(days=90)).date()
                
                operator_data = {
                    'id': user.id,
                    'name': user.get_full_name(),
                    'license_number': user.userprofile.license_number,
                    'violation_count': violations.count(),
                    'has_recent_violations': violations.filter(
                        violation_date__gte=ninety_days_ago
                    ).exists(),
                    'violation_types': list(violations.values_list('violation_type', flat=True).distinct()),
                    'status': 'good' if not violations.exists() else 'warning' if violations.count() < 3 else 'danger'
                }
                operators.append(operator_data)
    
    # Also search the Violator model for matching license numbers or names
    violators = Violator.objects.filter(
        Q(license_number__icontains=search_term) |
        Q(first_name__icontains=search_term) |
        Q(last_name__icontains=search_term)
    )
    
    for violator in violators:
        # Skip if this license number was already found in users
        if any(op['license_number'] == violator.license_number for op in operators):
            continue
            
        # Get violations for this violator
        violations = Violation.objects.filter(violator=violator)
        
        operator_data = {
            'id': f"v{violator.id}",  # Prefix with 'v' to distinguish from user IDs
            'name': f"{violator.first_name} {violator.last_name}",
            'license_number': violator.license_number,
            'violation_count': violations.count(),
            'has_recent_violations': violations.filter(
                violation_date__gte=ninety_days_ago
            ).exists(),
            'violation_types': list(violations.values_list('violation_type', flat=True).distinct()),
            'status': 'good' if not violations.exists() else 'warning' if violations.count() < 3 else 'danger'
        }
        operators.append(operator_data)
    
    # Search the Operator model too if it's available
    try:
        traffic_operators = Operator.objects.filter(
            Q(new_pd_number__icontains=search_term) |
            Q(old_pd_number__icontains=search_term) |
            Q(first_name__icontains=search_term) |
            Q(last_name__icontains=search_term)
        ).distinct()
        
        # Track operators we've already added to avoid duplicates
        added_operators = set()
        
        for op in traffic_operators:
            # Skip if we've already added this operator
            operator_key = f"operator-{op.id}"
            if operator_key in added_operators:
                continue
                
            # Add to tracking set
            added_operators.add(operator_key)
            
            # Try to find violations for this operator by matching name
            violations = Violation.objects.filter(
                Q(violator__first_name__iexact=op.first_name) & 
                Q(violator__last_name__iexact=op.last_name)
            )
            
            operator_data = {
                'id': f"o{op.id}",  # Prefix with 'o' to distinguish from user and violator IDs
                'name': op.full_name(),
                'pd_number': op.new_pd_number,
                'old_pd_number': op.old_pd_number,
                'violation_count': violations.count(),
                'has_recent_violations': violations.filter(
                    violation_date__gte=ninety_days_ago
                ).exists(),
                'violation_types': list(violations.values_list('violation_type', flat=True).distinct()),
                'status': 'good' if not violations.exists() else 'warning' if violations.count() < 3 else 'danger'
            }
            operators.append(operator_data)
    except:
        # If Operator model doesn't exist or if there's an error, just continue
        pass
    
    # Record this lookup for the first result if there are any
    if operators and len(operators) > 0:
        first_result = operators[0]
        
        # Check if we've recently looked up this same operator to avoid duplicates
        recent_lookup_time = timezone.now() - timezone.timedelta(minutes=5)
        recent_identical_lookup = OperatorViolationLookup.objects.filter(
            vehicle_owner=request.user,
            operator_name=first_result['name'],
            lookup_date__gte=recent_lookup_time
        ).exists()
        
        # Only create a new lookup record if we haven't recently looked up this operator
        if not recent_identical_lookup:
            OperatorViolationLookup.objects.create(
                vehicle_owner=request.user,
                operator_license=first_result.get('license_number', first_result.get('pd_number', 'Unknown')),
                operator_name=first_result['name']
            )
    
    return JsonResponse({
        'status': 'success',
        'operators': operators
    })

@login_required
def operator_lookup_history(request):
    """View for showing the history of operator lookups by this user"""
    # Check if the user is a vehicle owner
    vehicles = VehicleRegistration.objects.filter(user=request.user)
    
    if not vehicles.exists():
        messages.warning(request, "You need to register a vehicle before you can lookup operators.")
        return redirect('user_portal:vehicle_list')
    
    lookups = OperatorViolationLookup.objects.filter(
        vehicle_owner=request.user
    ).order_by('-lookup_date')
    
    # Pagination - 20 lookups per page
    paginator = Paginator(lookups, 20)
    page = request.GET.get('page', 1)
    
    try:
        paginated_lookups = paginator.page(page)
    except PageNotAnInteger:
        paginated_lookups = paginator.page(1)
    except EmptyPage:
        paginated_lookups = paginator.page(paginator.num_pages)
    
    context = {
        'lookups': paginated_lookups,
        'page_obj': paginated_lookups,
    }
    
    return render(request, 'user_portal/operator_lookup_history.html', context) 