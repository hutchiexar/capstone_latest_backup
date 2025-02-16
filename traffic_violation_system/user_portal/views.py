from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from .models import UserNotification, UserReport
from traffic_violation_system.models import Violation, Violator
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.http import HttpResponseNotAllowed

@login_required
def user_dashboard(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
        
    # Get user's violations
    violations = Violation.objects.filter(
        violator__license_number=request.user.userprofile.license_number
    )
    
    # Calculate statistics
    active_violations = violations.filter(
        status__in=['PENDING', 'ADJUDICATED', 'APPROVED']
    ).count()
    
    total_paid = violations.filter(
        status='PAID'
    ).aggregate(
        total=Sum('fine_amount')
    )['total'] or 0
    
    seven_days_from_now = timezone.now() + timezone.timedelta(days=7)
    due_soon = violations.filter(
        status__in=['PENDING', 'ADJUDICATED', 'APPROVED'],
        payment_due_date__lte=seven_days_from_now
    ).count()
    
    # Get recent violations
    recent_violations = violations.order_by('-violation_date')[:5]
    
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
    violations = Violation.objects.filter(
        violator__license_number=request.user.userprofile.license_number
    ).order_by('-violation_date')
    
    # Filter by status if provided
    status = request.GET.get('status')
    if status:
        violations = violations.filter(status=status)
    
    context = {
        'violations': violations,
        'status_choices': Violation.STATUS_CHOICES,
        'current_status': status,
    }
    
    return render(request, 'user_portal/violations.html', context)

@login_required
def violation_detail(request, violation_id):
    violation = get_object_or_404(
        Violation,
        id=violation_id,
        violator__license_number=request.user.userprofile.license_number
    )
    
    context = {
        'violation': violation,
    }
    
    return render(request, 'user_portal/violation_detail.html', context)

@login_required
def user_profile(request):
    user_profile = request.user.userprofile
    violations_count = Violation.objects.filter(
        violator__license_number=user_profile.license_number
    ).count()
    
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

            # Update profile information
            user_profile.contact_number = request.POST.get('contact_number')
            user_profile.address = request.POST.get('address')

            if 'avatar' in request.FILES:
                user_profile.avatar = request.FILES['avatar']

            user_profile.save()

            messages.success(request, 'Profile updated successfully!')
            return redirect('user_portal:user_profile')
        except Exception as e:
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