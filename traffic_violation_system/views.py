from django.contrib.auth import logout, authenticate, login
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import Violation, Payment, UserProfile, ActivityLog, Violator, Announcement
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
import cv2
import numpy as np
from datetime import datetime, timedelta, date
import base64
from django.core.files.base import ContentFile
from django.utils import timezone
from django.contrib.auth.models import User
import random
import string
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from .utils import log_activity
import requests
import json
from django.urls import reverse
import qrcode
from io import BytesIO
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from idanalyzer import CoreAPI
import os




@login_required
def admin_dashboard(request):
    today = timezone.now()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Get violations statistics
    violations = Violation.objects.all()
    total_violations = violations.count()
    weekly_violations = violations.filter(violation_date__gte=week_ago).count()
    monthly_violations = violations.filter(violation_date__gte=month_ago).count()

    # Get status-based counts
    pending_violations = violations.filter(status='PENDING').count()
    paid_violations_count = violations.filter(status='PAID').count()
    settled_violations = violations.filter(status='SETTLED').count()
    overdue_violations = violations.filter(status='OVERDUE').count()

    # Calculate revenue statistics
    paid_violations = violations.filter(status='PAID')
    total_revenue = paid_violations.aggregate(total=Sum('fine_amount'))['total'] or 0
    monthly_revenue = paid_violations.filter(
        receipt_date__gte=month_ago
    ).aggregate(total=Sum('fine_amount'))['total'] or 0
    weekly_revenue = paid_violations.filter(
        receipt_date__gte=week_ago
    ).aggregate(total=Sum('fine_amount'))['total'] or 0

    # Get violations trend data (last 30 days)
    dates = []
    violations_data = []
    
    for i in range(30, -1, -1):
        date = today - timedelta(days=i)
        # Format date as ISO string for proper JavaScript parsing
        dates.append(date.strftime('%Y-%m-%d'))
        count = violations.filter(
            violation_date__date=date.date()
        ).count()
        violations_data.append(count)

    # Convert dates to JSON-safe format
    from django.core.serializers.json import DjangoJSONEncoder
    import json
    
    context = {
        'total_violations': total_violations,
        'total_revenue': total_revenue,
        'pending_violations': pending_violations,
        'overdue_violations': overdue_violations,
        'weekly_violations': weekly_violations,
        'monthly_violations': monthly_violations,
        'weekly_revenue': weekly_revenue,
        'monthly_revenue': monthly_revenue,
        'paid_violations': paid_violations_count,
        'settled_violations': settled_violations,
        'dates': json.dumps(dates, cls=DjangoJSONEncoder),
        'violations_data': json.dumps(violations_data),
        'recent_violations': violations.order_by('-violation_date')[:10]
    }

    return render(request, 'violations/admin_dashboard.html', context)


@login_required
def violation_detail(request, violation_id):
    violation = get_object_or_404(Violation, id=violation_id)
    payment = Payment.objects.filter(violation=violation).first()
    
    context = {
        'violation': violation,
        'payment': payment,
        'paymongo_public_key': settings.PAYMONGO_PUBLIC_KEY,
    }
    
    # If it's an HTMX request, return just the content without the base template
    if request.headers.get('HX-Request'):
        return render(request, 'violations/violation_detail.html', context)
    
    return render(request, 'violations/violation_detail.html', context)


@login_required
def process_payment(request, violation_id):
    violation = get_object_or_404(Violation, id=violation_id)

    try:
        # Create Paymongo checkout session
        url = "https://api.paymongo.com/v1/checkout_sessions"
        
        # Convert amount to centavos (cents)
        amount = int(float(violation.fine_amount) * 100)
        
        payload = {
            "data": {
                "attributes": {
                    "send_email_receipt": True,
                    "show_description": True,
                    "show_line_items": True,
                    "line_items": [
                        {
                            "currency": "PHP",
                            "amount": amount,
                            "name": f"Violation #{violation.id}",
                            "quantity": 1,
                            "description": f"Payment for {violation.violation_type}"
                        }
                    ],
                    "payment_method_types": ["gcash", "card"],
                    "description": f"Payment for Violation #{violation.id}",
                    "reference_number": f"VIO-{violation.id}",
                    "success_url": request.build_absolute_uri(reverse('violation_detail', args=[violation.id])) + "?status=success",
                    "cancel_url": request.build_absolute_uri(reverse('violation_detail', args=[violation.id])) + "?status=cancelled"
                }
            }
        }

        # Create Basic Auth header
        auth_string = base64.b64encode(f"{settings.PAYMONGO_SECRET_KEY}:".encode()).decode()
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "authorization": f"Basic {auth_string}"
        }

        # Print request details for debugging
        print("Request Headers:", headers)
        print("Request Payload:", json.dumps(payload, indent=2))

        # Create checkout session
        response = requests.post(url, json=payload, headers=headers)
        
        # Print response for debugging
        print("Response Status:", response.status_code)
        print("Response Body:", response.text)
        
        if response.status_code == 200:
            checkout_data = response.json()
            checkout_url = checkout_data["data"]["attributes"]["checkout_url"]
            
            # Update violation status to DISPUTED immediately
            violation.status = 'DISPUTED'
            violation.save()
            
            # Create payment record
            Payment.objects.create(
                violation=violation,
                amount_paid=violation.fine_amount,
                payment_method='online',
                transaction_id=checkout_data["data"]["id"]
            )
            
            # Log the activity
            log_activity(
                user=request.user,
                action='Payment Initiated - Status Updated to Disputed',
                details=f'Payment initiated for Violation #{violation.id}. Status updated to DISPUTED.',
                category='payment'
            )
            
            # Return the checkout URL
            return JsonResponse({
                'checkout_url': checkout_url
            })
        else:
            error_message = response.json() if response.text else 'Unknown error'
            print("Paymongo Error:", error_message)
            return JsonResponse({
                'error': f'Failed to create checkout session: {error_message}'
            }, status=400)

    except Exception as e:
        import traceback
        print("Exception:", str(e))
        print("Traceback:", traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
def payment_webhook(request):
    if request.method == 'POST':
        try:
            # Parse the webhook data
            payload = json.loads(request.body)
            print("Webhook payload:", json.dumps(payload, indent=2))  # Debug log

            # Check if this is a successful checkout session
            event_type = payload.get('data', {}).get('attributes', {}).get('type')
            
            if event_type == 'checkout_session.completed':
                # Get the checkout session data
                checkout_data = payload['data']['attributes']
                
                # Get the reference number which contains our violation ID
                reference_number = checkout_data.get('reference_number')
                if not reference_number:
                    print("No reference number found in webhook data")
                    return HttpResponse(status=400)
                
                violation_id = reference_number.replace('VIO-', '')
                
                try:
                    # Get the violation
                    violation = Violation.objects.get(id=violation_id)
                    
                    # Create payment record
                    Payment.objects.create(
                        violation=violation,
                        amount_paid=float(checkout_data['line_items'][0]['amount']) / 100,  # Convert from cents
                        payment_method=checkout_data.get('payment_method_used', 'online'),
                        transaction_id=checkout_data['id']
                    )
                    
                    # Update violation status to PAID
                    violation.status = 'PAID'  # Changed from 'DISPUTED' to 'PAID'
                    violation.save()
                    
                    # Log the activity
                    try:
                        user = User.objects.get(username='system')
                    except User.DoesNotExist:
                        user = User.objects.create_user(username='system', password='systemuser123')
                    
                    log_activity(
                        user=user,
                        action='Payment Received - Status Updated to Paid',
                        details=f'Payment received for Violation #{violation.id} via {checkout_data.get("payment_method_used", "online")}. Status updated to PAID.',
                        category='payment'
                    )
                    
                    print(f"Successfully processed payment for violation {violation_id}")
                    return HttpResponse(status=200)
                    
                except Violation.DoesNotExist:
                    print(f"Error: Violation {violation_id} not found")
                    return HttpResponse(status=404)
                except Exception as e:
                    print(f"Error processing payment: {str(e)}")
                    return HttpResponse(status=400)
            
            return HttpResponse(status=200)

        except json.JSONDecodeError as e:
            print(f"Error decoding webhook payload: {str(e)}")
            return HttpResponse(status=400)
        except Exception as e:
            print(f"Webhook processing error: {str(e)}")
            return HttpResponse(status=400)

    return HttpResponse(status=405)  # Method not allowed for non-POST requests


@login_required
def upload_violation(request):
    if request.method == 'POST':
        try:
            # Create or get violator
            violator, created = Violator.objects.get_or_create(
                license_number=request.POST.get('license_number'),
                defaults={
                    'first_name': 'Unknown',
                    'last_name': 'Driver',
                }
            )

            # Create violation
            violation = Violation.objects.create(
                violator=violator,
                location=request.POST.get('location'),
                violation_type=request.POST.get('violation_type'),
                fine_amount=request.POST.get('fine_amount'),
                image=request.FILES.get('violation_image')
            )
            
            log_activity(
                user=request.user,
                action='Uploaded NCAP Violation',
                details=f'NCAP Violation uploaded for {violation.violator.license_number}',
                category='violation'
            )
            
            # Store current page in session
            request.session['current_page'] = 'ncap_violations_list'
            messages.success(request, 'NCAP Violation uploaded successfully.')
            return redirect('ncap_violations_list')
            
        except Exception as e:
            messages.error(request, f'Error uploading NCAP violation: {str(e)}')
            return redirect('upload_violation')
            
    context = {
        'violation_choices': Violation.VIOLATION_CHOICES
    }
    return render(request, 'violations/upload_violation.html', context)


def process_violation_image(image_path):
    """Process the violation image using OpenCV"""
    try:
        # Read image
        img = cv2.imread(image_path)

        # Basic image processing (example)
        img = cv2.resize(img, (800, 600))
        img = cv2.addWeighted(img, 1.2, img, 0, 0)  # Enhance contrast

        # Save processed image
        processed_path = image_path.replace('temp/', 'processed/')
        cv2.imwrite(processed_path, img)

        return processed_path
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return image_path


@login_required
def issue_ticket(request):
    if request.method == 'POST':
        try:
            print("POST data:", request.POST)
            
            # First check if a violator with this license number exists
            license_number = request.POST.get('license_number')
            print("License number:", license_number)
            
            try:
                violator = Violator.objects.get(license_number=license_number)
                # Update violator information
                violator.first_name = request.POST.get('first_name')
                violator.last_name = request.POST.get('last_name')
                violator.phone_number = request.POST.get('phone_number')
                violator.address = request.POST.get('address')
                violator.save()
            except Violator.DoesNotExist:
                # Create new violator if not found
                violator = Violator.objects.create(
                    first_name=request.POST.get('first_name'),
                    last_name=request.POST.get('last_name'),
                    license_number=license_number,
                    phone_number=request.POST.get('phone_number'),
                    address=request.POST.get('address')
                )

            # Get list of selected violations
            violation_types = request.POST.getlist('violation_type[]')
            print("Selected violations:", violation_types)
            
            if not violation_types:
                raise ValueError("Please select at least one violation type")

            # Create violation with new vehicle information and multiple violations
            violation = Violation.objects.create(
                violator=violator,
                location=request.POST.get('location'),
                violation_type=violation_types[0],  # Store first violation as primary type
                fine_amount=request.POST.get('fine_amount'),
                enforcer=request.user,  # This will store the user object
                enforcer_signature_date=timezone.now(),
                vehicle_type=request.POST.get('vehicle_type'),
                classification=request.POST.get('classification'),
                plate_number=request.POST.get('plate_number'),
                color=request.POST.get('color'),
                registration_number=request.POST.get('registration_number'),
                registration_date=request.POST.get('registration_date'),
                vehicle_owner=request.POST.get('vehicle_owner'),
                vehicle_owner_address=request.POST.get('vehicle_owner_address')
            )
            
            # Set violation types
            violation.set_violation_types(violation_types)
            
            # Handle signature or refusal note
            if request.POST.get('no_signature') == 'on':
                violation.description = f"Violator refused to sign. Note: {request.POST.get('refusal_note')}"
            else:
                signature_data = request.POST.get('signature_data')
                if signature_data:
                    format, imgstr = signature_data.split(';base64,')
                    ext = format.split('/')[-1]
                    filename = f'signature_{violation.id}.{ext}'
                    data = ContentFile(base64.b64decode(imgstr))
                    violation.violator_signature.save(filename, data, save=False)
                    violation.violator_signature_date = timezone.now()

            violation.save()

            # Log the activity
            log_activity(
                user=request.user,
                action='Issued Ticket',
                details=f'Ticket issued to {violator.license_number}',
                category='violation'
            )

            print("Ticket created successfully, rendering template")
            
            return render(request, 'violations/ticket_template.html', {
                'violation': violation,
            })

        except Exception as e:
            print("Error:", str(e))
            messages.error(request, f'Error issuing ticket: {str(e)}')
            return redirect('issue_ticket')

    context = {
        'violation_choices': Violation.VIOLATION_CHOICES,
        'vehicle_classifications': Violation.VEHICLE_CLASSIFICATIONS,
    }
    return render(request, 'violations/issue_direct_ticket.html', context)


def custom_logout(request):
    logout(request)
    response = redirect('login')
    # Add cache control headers to prevent back button from showing authenticated pages
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Get the next URL from session or use default
            next_url = request.session.get('next', None)
            if next_url:
                del request.session['next']  # Clear the stored URL
                return redirect(next_url)
                
            # Default redirects based on user role
            if user.userprofile.role == 'USER':
                return redirect('user_portal:user_dashboard')
            else:
                return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    # Add no-cache headers for the login page
    response = render(request, 'registration/login.html')
    response['Cache-Control'] = 'no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


def generate_enforcer_id():
    """Generate a unique enforcer ID"""
    prefix = 'ENF'
    while True:
        # Generate random 4 digits
        numbers = ''.join(random.choices(string.digits, k=4))
        enforcer_id = f"{prefix}{numbers}"
        if not UserProfile.objects.filter(enforcer_id=enforcer_id).exists():
            return enforcer_id


def register(request):
    if request.method == 'POST':
        try:
            # Create user
            user = User.objects.create_user(
                username=request.POST['username'],
                password=request.POST['password'],
                email=request.POST['email'],
                first_name=request.POST['first_name'],
                last_name=request.POST['last_name']
            )

            # Create user profile
            profile = UserProfile.objects.create(
                user=user,
                enforcer_id=generate_enforcer_id(),  # Still needed for system compatibility
                phone_number=request.POST['phone_number'],
                address=request.POST['address'],
                role='USER',  # Set role as USER
                license_number=request.POST['license_number']  # Add license number
            )

            # Handle avatar upload
            if 'avatar' in request.FILES:
                profile.avatar = request.FILES['avatar']
                profile.save()

            messages.success(request, 'Registration successful! Please login.')
            return redirect('login')
        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
            return redirect('register')

    return render(request, 'registration/register.html')


@login_required
def profile(request):
    # Add context for showing messages
    context = {
        'show_messages': request.session.get('current_page') == 'profile'
    }
    return render(request, 'profile.html', context)


@login_required
def edit_profile(request):
    # Get or create UserProfile
    profile, created = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'enforcer_id': generate_enforcer_id(),
            'phone_number': '',
            'address': ''
        }
    )

    if request.method == 'POST':
        try:
            user = request.user

            # Update user information
            user.first_name = request.POST.get('first_name')
            user.last_name = request.POST.get('last_name')
            user.email = request.POST.get('email')
            user.save()

            # Update profile information
            profile.phone_number = request.POST.get('phone_number')
            profile.address = request.POST.get('address')

            if 'avatar' in request.FILES:
                profile.avatar = request.FILES['avatar']

            profile.save()

            # Store current page in session
            request.session['current_page'] = 'profile'
            
            # Add success message
            messages.success(request, 'Profile updated successfully!')
            
            # Log the activity
            log_activity(
                user=request.user,
                action='Updated Profile',
                details='Profile information was updated',
                category='user'
            )

            return redirect('profile')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
            return redirect('edit_profile')

    return render(request, 'edit_profile.html', {'user': request.user})


@login_required
def users_list(request):
    user_profiles = UserProfile.objects.all().select_related('user').order_by('user__date_joined')
    
    # Enhanced search functionality
    search_query = request.GET.get('search', '').strip()
    role_filter = request.GET.get('role', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if search_query:
        user_profiles = user_profiles.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(enforcer_id__icontains=search_query)
        )

    if role_filter:
        user_profiles = user_profiles.filter(role=role_filter)

    if status_filter:
        is_active = status_filter == 'active'
        user_profiles = user_profiles.filter(user__is_active=is_active)

    # Pagination - 10 users per page
    paginator = Paginator(user_profiles, 10)
    page = request.GET.get('page', 1)
    try:
        user_profiles = paginator.page(page)
    except PageNotAnInteger:
        user_profiles = paginator.page(1)
    except EmptyPage:
        user_profiles = paginator.page(paginator.num_pages)

    context = {
        'user_profiles': user_profiles,
        'page_obj': user_profiles,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'total_count': paginator.count
    }
    return render(request, 'users/users_list.html', context)


@login_required
def create_user(request):
    if request.method == 'POST':
        try:
            # Create user
            user = User.objects.create_user(
                username=request.POST['username'],
                password=request.POST['password'],
                email=request.POST['email'],
                first_name=request.POST['first_name'],
                last_name=request.POST['last_name']
            )

            # Instead of creating a new profile, update the one created by the signal
            profile = user.userprofile  # This exists because of the signal
            profile.phone_number = request.POST['phone_number']
            profile.address = request.POST['address']
            profile.role = request.POST['role']

            if 'avatar' in request.FILES:
                profile.avatar = request.FILES['avatar']
            
            profile.save()

            # Log the activity
            log_activity(
                user=request.user,
                action='Created User',
                details=f'Created user account for {user.get_full_name()}',
                category='user'
            )

            # Store current page in session
            request.session['current_page'] = 'users_list'
            messages.success(request, 'User created successfully!')
            return redirect('users_list')
        except Exception as e:
            # If there's an error, delete the user to maintain consistency
            if 'user' in locals():
                user.delete()
            messages.error(request, f'Error creating user: {str(e)}')
    
    roles = UserProfile.ROLE_CHOICES
    return render(request, 'users/create_user.html', {'roles': roles})


@login_required
def user_detail(request, user_id):
    profile = get_object_or_404(UserProfile, id=user_id)
    return render(request, 'users/user_detail.html', {'profile': profile})


@login_required
def edit_user(request, user_id):
    profile = get_object_or_404(UserProfile, id=user_id)
    
    if request.method == 'POST':
        try:
            user = profile.user
            user.first_name = request.POST['first_name']
            user.last_name = request.POST['last_name']
            user.email = request.POST['email']
            user.save()

            profile.phone_number = request.POST['phone_number']
            profile.address = request.POST['address']
            profile.role = request.POST['role']

            if 'avatar' in request.FILES:
                profile.avatar = request.FILES['avatar']
            
            profile.save()

            # Log the activity
            log_activity(
                user=request.user,
                action='Updated User',
                details=f'Updated user profile for {user.get_full_name()}',
                category='user'
            )

            # Store current page in session
            request.session['current_page'] = 'users_list'
            messages.success(request, 'User profile updated successfully!')
            return redirect('users_list')
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')

    roles = UserProfile.ROLE_CHOICES
    return render(request, 'users/edit_user.html', {
        'profile': profile,
        'roles': roles
    })


@login_required
def toggle_user_status(request, user_id):
    if request.method == 'POST':
        try:
            profile = get_object_or_404(UserProfile, id=user_id)
            user = profile.user
            
            # Toggle the user's active status
            user.is_active = not user.is_active
            user.save()
            
            # Add success message
            messages.success(request, f'User {user.username} has been {"activated" if user.is_active else "deactivated"} successfully.')
            
            return JsonResponse({
                'success': True,
                'is_active': user.is_active,
                'message': f'User {user.username} has been {"activated" if user.is_active else "deactivated"}'
            })
        except Exception as e:
            messages.error(request, f'Error changing user status: {str(e)}')
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
            
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=405)


@login_required
def activity_history(request):
    activities = ActivityLog.objects.select_related('user', 'user__userprofile').all()

    # Enhanced search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        activities = activities.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(action__icontains=search_query) |
            Q(details__icontains=search_query) |
            Q(category__icontains=search_query) |
            Q(user__userprofile__enforcer_id__icontains=search_query)
        ).distinct()

    # Get filter parameters
    category = request.GET.get('category', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    user_id = request.GET.get('user_id', '')

    # Apply filters
    if category:
        activities = activities.filter(category=category)
    
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            activities = activities.filter(timestamp__gte=date_from)
        except ValueError:
            pass

    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            # Add one day to include the entire end date
            date_to = date_to + timedelta(days=1)
            activities = activities.filter(timestamp__lt=date_to)
        except ValueError:
            pass

    if user_id:
        activities = activities.filter(user_id=user_id)

    # Order by timestamp descending (most recent first)
    activities = activities.order_by('-timestamp')

    # Pagination - 25 activities per page
    paginator = Paginator(activities, 25)
    page = request.GET.get('page', 1)
    try:
        activities = paginator.page(page)
    except PageNotAnInteger:
        activities = paginator.page(1)
    except EmptyPage:
        activities = paginator.page(paginator.num_pages)

    # Get all categories and users for filters
    categories = ActivityLog.CATEGORY_CHOICES
    users = User.objects.filter(
        id__in=activities.paginator.object_list.values_list('user_id', flat=True).distinct()
    ).select_related('userprofile')

    context = {
        'activities': activities,
        'categories': categories,
        'users': users,
        'current_category': category,
        'current_user': user_id,
        'date_from': date_from,
        'date_to': date_to,
        'page_obj': activities,
        'search_query': search_query,
        'total_count': paginator.count
    }

    return render(request, 'activity_history.html', context)


@login_required
def get_statistics(request, time_range):
    """API endpoint for chart data"""
    today = timezone.now()
    
    if time_range == 'week':
        start_date = today - timedelta(days=7)
        date_format = '%Y-%m-%d'
    elif time_range == 'month':
        start_date = today - timedelta(days=30)
        date_format = '%Y-%m-%d'
    else:  # year
        start_date = today - timedelta(days=365)
        date_format = '%Y-%m'

    # Get violations data
    violations = Violation.objects.filter(
        violation_date__gte=start_date
    ).annotate(
        date=TruncDate('violation_date')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')

    # Format data for charts
    labels = []
    data = []
    
    # Create a date range for all dates in the period
    date_range = []
    delta = today - start_date
    for i in range(delta.days + 1):
        date_range.append(start_date + timedelta(days=i))
    
    # Create a lookup of existing data
    data_lookup = {item['date']: item['count'] for item in violations}
    
    # Fill in data for all dates
    for date in date_range:
        labels.append(date.strftime(date_format))
        data.append(data_lookup.get(date.date(), 0))

    violations_chart = {
        'labels': labels,
        'datasets': [{
            'label': 'Total Violations',
            'data': data,
            'borderColor': '#2563eb',
            'backgroundColor': 'rgba(37, 99, 235, 0.1)',
            'tension': 0.4,
            'fill': True
        }]
    }

    return JsonResponse({
        'violations': violations_chart
    })


@login_required
def violation_detail_modal(request, violation_id):
    try:
        violation = get_object_or_404(Violation, id=violation_id)
        
        # Check if it's an NCAP violation by checking for image
        is_ncap = bool(violation.image)
        
        # Use the appropriate template
        template_name = 'violations/ncap_violation_detail_modal.html' if is_ncap else 'violations/violation_detail_modal.html'
        
        context = {
            'violation': violation,
            'is_modal': True
        }
        
        return render(request, template_name, context)
    except Exception as e:
        return HttpResponse(
            '<div class="alert alert-danger">Error loading violation details. Please try again.</div>', 
            status=500
        )

@login_required
def violations_list(request):
    # Get all violations excluding NCAP violations (those with images)
    violations = Violation.objects.filter(image='').select_related('violator', 'enforcer').order_by('-violation_date')
    
    # Enhanced search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        violations = violations.filter(
            Q(violator__first_name__icontains=search_query) |
            Q(violator__last_name__icontains=search_query) |
            Q(violator__license_number__icontains=search_query) |
            Q(violation_type__icontains=search_query) |
            Q(vehicle_type__icontains=search_query) |
            Q(plate_number__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(status__icontains=search_query)
        ).distinct()

    # Pagination - 15 items per page
    paginator = Paginator(violations, 15)
    page = request.GET.get('page', 1)
    try:
        violations = paginator.page(page)
    except PageNotAnInteger:
        violations = paginator.page(1)
    except EmptyPage:
        violations = paginator.page(paginator.num_pages)

    context = {
        'violations': violations,
        'page_obj': violations,
        'search_query': search_query,
        'total_count': paginator.count
    }
    return render(request, 'violations/violations_list.html', context)

@login_required
def update_violation_status(request, violation_id):
    if request.method == 'POST':
        try:
            violation = get_object_or_404(Violation, id=violation_id)
            new_status = request.POST.get('status')
            
            if new_status in dict(Violation.STATUS_CHOICES):
                old_status = violation.status
                violation.status = new_status
                violation.save()
                
                # Log the activity
                log_activity(
                    user=request.user,
                    action='Updated Violation Status',
                    details=f'Changed status of Violation #{violation.id} from {old_status} to {new_status}',
                    category='violation'
                )
                
                messages.success(request, f'Violation status updated successfully to {new_status}')
                return JsonResponse({
                    'status': 'success',
                    'message': f'Violation status updated to {new_status}',
                    'new_status': new_status
                })
            else:
                messages.error(request, 'Invalid status provided')
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid status provided'
                }, status=400)
                
        except Exception as e:
            messages.error(request, f'Error updating violation status: {str(e)}')
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
            
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

@login_required
def user_detail_modal(request, user_id):
    try:
        profile = get_object_or_404(UserProfile, id=user_id)
        context = {
            'profile': profile,
            'is_modal': True
        }
        return render(request, 'users/user_detail.html', context)
    except Exception as e:
        return HttpResponse(
            '<div class="alert alert-danger">Error loading user details. Please try again.</div>', 
            status=500
        )

@login_required
def ncap_violations_list(request):
    # Get violations with images (NCAP violations)
    violations = Violation.objects.exclude(
        Q(image='') | Q(image__isnull=True)
    ).select_related('violator', 'enforcer').order_by('-violation_date')
    
    # Enhanced search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        violations = violations.filter(
            Q(violator__first_name__icontains=search_query) |
            Q(violator__last_name__icontains=search_query) |
            Q(violator__license_number__icontains=search_query) |
            Q(violation_type__icontains=search_query) |
            Q(vehicle_type__icontains=search_query) |
            Q(plate_number__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(status__icontains=search_query)
        ).distinct()

    # Pagination - 12 items per page
    paginator = Paginator(violations, 12)
    page = request.GET.get('page', 1)
    try:
        violations = paginator.page(page)
    except PageNotAnInteger:
        violations = paginator.page(1)
    except EmptyPage:
        violations = paginator.page(paginator.num_pages)

    context = {
        'violations': violations,
        'page_obj': violations,
        'search_query': search_query,
        'total_count': paginator.count
    }
    return render(request, 'violations/ncap_violations_list.html', context)

@login_required
def adjudication_list(request):
    # Get all violations without status filtering
    violations = Violation.objects.select_related('violator', 'enforcer').order_by('-violation_date')
    
    # Enhanced search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        violations = violations.filter(
            Q(violator__first_name__icontains=search_query) |
            Q(violator__last_name__icontains=search_query) |
            Q(violator__license_number__icontains=search_query) |
            Q(violation_type__icontains=search_query) |
            Q(vehicle_type__icontains=search_query) |
            Q(plate_number__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(status__icontains=search_query)
        ).distinct()

    # Pagination - 15 items per page
    paginator = Paginator(violations, 15)
    page = request.GET.get('page', 1)
    try:
        violations = paginator.page(page)
    except PageNotAnInteger:
        violations = paginator.page(1)
    except EmptyPage:
        violations = paginator.page(paginator.num_pages)

    context = {
        'violations': violations,
        'page_obj': violations,
        'search_query': search_query,
        'total_count': paginator.count
    }
    return render(request, 'violations/adjudication_list.html', context)

@login_required
def adjudication_form(request, violation_id):
    violation = get_object_or_404(Violation, id=violation_id)
    context = {
        'violation': violation,
    }
    return render(request, 'violations/adjudication_form.html', context)

@login_required
def submit_adjudication(request, violation_id):
    if request.method == 'POST':
        violation = get_object_or_404(Violation, id=violation_id)
        try:
            # Process the adjudication form
            violation.status = 'ADJUDICATED'
            violation.adjudicated_by = request.user
            violation.adjudication_date = timezone.now()
            violation.adjudication_remarks = request.POST.get('remarks')
            violation.save()
            
            # Log the activity
            log_activity(
                user=request.user,
                action='Adjudicated Case',
                details=f'Adjudicated Violation #{violation.id}',
                category='violation'
            )
            
            messages.success(request, 'Case adjudicated successfully.')
            return redirect('adjudication_list')
            
        except Exception as e:
            messages.error(request, f'Error processing adjudication: {str(e)}')
            return redirect('adjudication_form', violation_id=violation_id)
            
    return redirect('adjudication_list')

@login_required
def announcements_list(request):
    announcements = Announcement.objects.filter(is_active=True).select_related('created_by').order_by('-created_at')
    
    # Enhanced search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        announcements = announcements.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(priority__icontains=search_query) |
            Q(created_by__first_name__icontains=search_query) |
            Q(created_by__last_name__icontains=search_query) |
            Q(created_by__userprofile__enforcer_id__icontains=search_query)
        ).distinct()

    # Pagination - 8 announcements per page
    paginator = Paginator(announcements, 8)
    page = request.GET.get('page', 1)
    try:
        announcements = paginator.page(page)
    except PageNotAnInteger:
        announcements = paginator.page(1)
    except EmptyPage:
        announcements = paginator.page(paginator.num_pages)

    context = {
        'announcements': announcements,
        'page_obj': announcements,
        'search_query': search_query,
        'total_count': paginator.count
    }
    return render(request, 'announcements/announcements_list.html', context)

@login_required
def create_announcement(request):
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, 'You do not have permission to create announcements.')
        return redirect('announcements_list')

    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        priority = request.POST.get('priority', 'MEDIUM')

        if title and content:
            announcement = Announcement.objects.create(
                title=title,
                content=content,
                priority=priority,
                created_by=request.user
            )
            # Store current page in session
            request.session['current_page'] = 'announcements_list'
            messages.success(request, 'Announcement created successfully.')
            return redirect('announcements_list')
        else:
            messages.error(request, 'Please fill in all required fields.')

    return render(request, 'announcements/create_announcement.html')

@login_required
def edit_announcement(request, announcement_id):
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, 'You do not have permission to edit announcements.')
        return redirect('announcements_list')

    announcement = get_object_or_404(Announcement, id=announcement_id)

    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        priority = request.POST.get('priority')
        is_active = request.POST.get('is_active') == 'on'

        if title and content:
            announcement.title = title
            announcement.content = content
            announcement.priority = priority
            announcement.is_active = is_active
            announcement.save()
            # Store current page in session
            request.session['current_page'] = 'announcements_list'
            messages.success(request, 'Announcement updated successfully.')
            return redirect('announcements_list')
        else:
            messages.error(request, 'Please fill in all required fields.')

    context = {
        'announcement': announcement
    }
    return render(request, 'announcements/edit_announcement.html', context)

@login_required
def delete_announcement(request, announcement_id):
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, 'You do not have permission to delete announcements.')
        return redirect('announcements_list')

    announcement = get_object_or_404(Announcement, id=announcement_id)
    announcement.delete()
    # Store current page in session
    request.session['current_page'] = 'announcements_list'
    messages.success(request, 'Announcement deleted successfully.')
    return redirect('announcements_list')

@login_required
def enforcer_map(request):
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR', 'ENFORCER']:
        messages.error(request, 'You do not have permission to view the enforcer map.')
        return redirect('admin_dashboard')
    
    return render(request, 'enforcer_map.html')

@login_required
@csrf_exempt
def update_location(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    
    if not request.user.userprofile.role == 'ENFORCER':
        return JsonResponse({'status': 'error', 'message': 'Only enforcers can update location'}, status=403)

    try:
        data = json.loads(request.body)
        profile = request.user.userprofile
        
        # Update location efficiently
        profile.latitude = data['latitude']
        profile.longitude = data['longitude']
        profile.last_location_update = timezone.now()
        profile.is_active_duty = data.get('is_active', True)
        
        # Use update_fields to optimize the query
        profile.save(update_fields=['latitude', 'longitude', 'last_location_update', 'is_active_duty'])
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
def get_enforcer_locations(request):
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR', 'ENFORCER']:
        return JsonResponse({
            'status': 'error',
            'message': 'Permission denied'
        }, status=403)

    # Get all enforcers with their locations, optimized query
    current_time = timezone.now()
    inactive_threshold = current_time - timezone.timedelta(minutes=5)

    locations_query = UserProfile.objects.filter(
        role='ENFORCER',
        latitude__isnull=False,
        longitude__isnull=False,
        is_active_duty=True,
        last_location_update__gt=inactive_threshold
    ).select_related('user').only(
        'id', 'user__first_name', 'user__last_name',
        'enforcer_id', 'role', 'latitude', 'longitude',
        'last_location_update', 'avatar', 'is_active_duty'
    )

    locations = [{
        'id': profile.id,
        'name': f"{profile.user.first_name} {profile.user.last_name}",
        'enforcer_id': profile.enforcer_id,
        'role': profile.role,
        'latitude': float(profile.latitude),
        'longitude': float(profile.longitude),
        'last_update': profile.last_location_update.isoformat() if profile.last_location_update else None,
        'avatar_url': profile.avatar.url if profile.avatar else None,
        'is_active': True  # All returned enforcers are active
    } for profile in locations_query]

    return JsonResponse({
        'status': 'success',
        'locations': locations
    })

# Add this function to check if user is authorized
def is_payment_recorder(user):
    return user.is_authenticated and user.userprofile.role in ['ADMIN', 'SUPERVISOR', 'ADJUDICATOR']

# Add this view for recording payments
@user_passes_test(is_payment_recorder)
def record_payment(request, violation_id):
    violation = get_object_or_404(Violation, id=violation_id)
    
    if request.method == 'POST':
        try:
            receipt_number = request.POST.get('receipt_number')
            receipt_date = request.POST.get('receipt_date')
            remarks = request.POST.get('remarks')
            
            violation.status = 'PAID'
            violation.receipt_number = receipt_number
            violation.receipt_date = receipt_date
            violation.payment_date = timezone.now()
            violation.payment_remarks = remarks
            violation.processed_by = request.user
            violation.payment_amount = violation.fine_amount
            violation.save()
            
            # Log the activity
            log_activity(
                user=request.user,
                action='Recorded Payment',
                details=f'Recorded payment for Violation #{violation.id}',
                category='violation'
            )
            
            messages.success(request, 'Payment recorded successfully.')
            return redirect('payment_processing')
        except Exception as e:
            messages.error(request, f'Error recording payment: {str(e)}')
    
    context = {
        'violation': violation,
        'today': timezone.now()
    }
    return render(request, 'violations/payment_receipt.html', context)

# Add this view for payment records
@login_required
def payment_records(request):
    # Get all paid violations
    paid_violations = Violation.objects.filter(
        status='PAID'
    ).select_related('violator', 'enforcer').order_by('-receipt_date')
    
    # Enhanced search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        paid_violations = paid_violations.filter(
            Q(violator__first_name__icontains=search_query) |
            Q(violator__last_name__icontains=search_query) |
            Q(violator__license_number__icontains=search_query) |
            Q(violation_type__icontains=search_query) |
            Q(vehicle_type__icontains=search_query) |
            Q(plate_number__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(receipt_number__icontains=search_query)
        ).distinct()
    
    # Pagination
    paginator = Paginator(paid_violations, 10)
    page = request.GET.get('page')
    
    try:
        paid_violations = paginator.page(page)
    except PageNotAnInteger:
        paid_violations = paginator.page(1)
    except EmptyPage:
        paid_violations = paginator.page(paginator.num_pages)
    
    context = {
        'paid_violations': paid_violations,
        'page_obj': paid_violations,
        'search_query': search_query,
        'total_count': paginator.count
    }
    
    return render(request, 'payments/payment_records.html', context)

# Add this view for printing receipts
@login_required
def print_receipt(request, violation_id):
    violation = get_object_or_404(Violation, id=violation_id)
    
    if violation.status != 'PAID':
        messages.error(request, 'Cannot print receipt for unpaid violation.')
        return redirect('payment_records')
    
    context = {
        'violation': violation,
    }
    
    return render(request, 'payments/print_receipt.html', context)

def is_supervisor(user):
    return user.userprofile.role == 'SUPERVISOR' or user.userprofile.role == 'ADMIN'

def is_treasurer(user):
    return user.userprofile.role == 'TREASURER' or user.userprofile.role == 'ADMIN'

@login_required
@user_passes_test(is_supervisor)
def pending_approvals(request):
    # Get violations that are adjudicated but not yet approved/rejected
    violations = Violation.objects.filter(
        status='ADJUDICATED'
    ).select_related('violator', 'enforcer', 'adjudicated_by').order_by('-violation_date')
    
    # Enhanced search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        violations = violations.filter(
            Q(violator__first_name__icontains=search_query) |
            Q(violator__last_name__icontains=search_query) |
            Q(violator__license_number__icontains=search_query) |
            Q(violation_type__icontains=search_query)
        ).distinct()

    # Pagination
    paginator = Paginator(violations, 15)
    page = request.GET.get('page', 1)
    try:
        violations = paginator.page(page)
    except PageNotAnInteger:
        violations = paginator.page(1)
    except EmptyPage:
        violations = paginator.page(paginator.num_pages)

    context = {
        'violations': violations,
        'page_obj': violations,
        'search_query': search_query,
        'total_count': paginator.count
    }
    return render(request, 'violations/pending_approvals.html', context)

@login_required
@user_passes_test(is_supervisor)
def approve_adjudication(request, violation_id):
    if request.method == 'POST':
        violation = get_object_or_404(Violation, id=violation_id)
        try:
            violation.status = 'APPROVED'
            violation.approved_by = request.user
            violation.approval_date = timezone.now()
            violation.save()
            
            # Log the activity
            log_activity(
                user=request.user,
                action='Approved Adjudication',
                details=f'Approved adjudication for Violation #{violation.id}',
                category='violation'
            )
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
@user_passes_test(is_supervisor)
def reject_adjudication(request, violation_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            reason = data.get('reason', '')
            
            violation = get_object_or_404(Violation, id=violation_id)
            violation.status = 'REJECTED'
            violation.rejection_reason = reason
            violation.save()
            
            # Log the activity
            log_activity(
                user=request.user,
                action='Rejected Adjudication',
                details=f'Rejected adjudication for Violation #{violation.id}',
                category='violation'
            )
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
@user_passes_test(is_treasurer)
def payment_processing(request):
    # Get violations that are approved but not yet paid
    violations = Violation.objects.filter(
        status='APPROVED'
    ).select_related('violator', 'enforcer', 'adjudicated_by').order_by('-violation_date')
    
    # Enhanced search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        violations = violations.filter(
            Q(violator__first_name__icontains=search_query) |
            Q(violator__last_name__icontains=search_query) |
            Q(violator__license_number__icontains=search_query) |
            Q(violation_type__icontains=search_query)
        ).distinct()

    # Pagination
    paginator = Paginator(violations, 15)
    page = request.GET.get('page', 1)
    try:
        violations = paginator.page(page)
    except PageNotAnInteger:
        violations = paginator.page(1)
    except EmptyPage:
        violations = paginator.page(paginator.num_pages)

    context = {
        'violations': violations,
        'page_obj': violations,
        'search_query': search_query,
        'total_count': paginator.count
    }
    return render(request, 'violations/payment_processing.html', context)

@login_required
@user_passes_test(is_treasurer)
def record_payment(request, violation_id):
    violation = get_object_or_404(Violation, id=violation_id)
    
    if request.method == 'POST':
        try:
            receipt_number = request.POST.get('receipt_number')
            receipt_date = request.POST.get('receipt_date')
            remarks = request.POST.get('remarks')
            
            violation.status = 'PAID'
            violation.receipt_number = receipt_number
            violation.receipt_date = receipt_date
            violation.payment_date = timezone.now()
            violation.payment_remarks = remarks
            violation.processed_by = request.user
            violation.payment_amount = violation.fine_amount
            violation.save()
            
            # Log the activity
            log_activity(
                user=request.user,
                action='Recorded Payment',
                details=f'Recorded payment for Violation #{violation.id}',
                category='violation'
            )
            
            messages.success(request, 'Payment recorded successfully.')
            return redirect('payment_processing')
        except Exception as e:
            messages.error(request, f'Error recording payment: {str(e)}')
    
    context = {
        'violation': violation,
        'today': timezone.now()
    }
    return render(request, 'violations/payment_receipt.html', context)

# Landing Page Views
def landing_home(request):
    return render(request, 'landing/home.html')

def about(request):
    return render(request, 'landing/about.html')

def services(request):
    return render(request, 'landing/services.html')

def contact(request):
    if request.method == 'POST':
        # Handle contact form submission
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        # Add your contact form processing logic here
        messages.success(request, 'Your message has been sent successfully!')
        return redirect('contact')
    return render(request, 'landing/contact.html')

@csrf_exempt
def scan_document(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    try:
        # Get the image file from request
        image_file = request.FILES.get('image')
        scan_type = request.POST.get('scan_type')
        
        print(f"Received scan request - Type: {scan_type}")
        
        if not image_file:
            return JsonResponse({'success': False, 'message': 'No image provided'})
            
        # Initialize ID Analyzer API
        api_key = os.getenv('ID_ANALYZER_API_KEY')
        if not api_key:
            print("Error: ID Analyzer API key not configured")
            return JsonResponse({'success': False, 'message': 'ID Analyzer API key not configured'})
            
        # Save temporary file
        temp_path = os.path.join('temp', f'doc_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg')
        os.makedirs('temp', exist_ok=True)
        
        print(f"Saving temporary file to: {temp_path}")
        
        with open(temp_path, 'wb+') as destination:
            for chunk in image_file.chunks():
                destination.write(chunk)

        try:
            print("Initializing ID Analyzer API...")
            # Initialize Core API with your api key and region
            coreapi = CoreAPI(api_key, "US")

            # Enable document authentication using quick module
            coreapi.enable_authentication(True, 'quick')
            
            # Enable face detection
            coreapi.face_detection = True
            
            print("Scanning document...")
            # Perform scan
            result = coreapi.scan(document_primary=temp_path)
            print("Scan result:", result)
            
            # Process results based on scan type
            if scan_type == 'license':
                # Extract license information
                if result.get('result'):
                    data_result = result['result']
                    # Properly format the address from address1 field
                    address = data_result.get('address1', '')
                    # Format the full name if individual parts are not available
                    first_name = data_result.get('firstName', '')
                    last_name = data_result.get('lastName', '')
                    if not first_name and not last_name and data_result.get('fullName'):
                        names = data_result['fullName'].split(' ', 1)
                        first_name = names[0]
                        last_name = names[1] if len(names) > 1 else ''

                    response_data = {
                        'success': True,
                        'license_number': data_result.get('documentNumber', ''),
                        'first_name': first_name,
                        'last_name': last_name,
                        'address': address,
                        'phone_number': data_result.get('phone', '')
                    }
                    print("License data extracted:", response_data)
                else:
                    print("No data extracted from license")
                    raise Exception('No data extracted from license')
                    
            else:  # vehicle registration
                # Extract vehicle information
                if result.get('result'):
                    data_result = result['result']
                    # Properly format the address
                    address = data_result.get('address1', data_result.get('address', ''))
                    response_data = {
                        'success': True,
                        'plate_number': data_result.get('vehicle', {}).get('plateNumber', ''),
                        'vehicle_type': data_result.get('vehicle', {}).get('type', ''),
                        'color': data_result.get('vehicle', {}).get('color', ''),
                        'registration_number': data_result.get('documentNumber', ''),
                        'owner_name': data_result.get('fullName', ''),
                        'owner_address': address
                    }
                    print("Vehicle data extracted:", response_data)
                else:
                    print("No data extracted from vehicle registration")
                    raise Exception('No data extracted from vehicle registration')

            # Add authentication results if available
            if result.get('authentication'):
                auth_result = result['authentication']
                response_data['authentication_score'] = auth_result.get('score', 0)
                print("Authentication score:", response_data['authentication_score'])
                
            return JsonResponse(response_data)
            
        except Exception as e:
            print(f"ID Analyzer API error: {str(e)}")
            # Handle API-specific errors
            return JsonResponse({
                'success': False,
                'message': f'ID Analyzer API error: {str(e)}'
            })
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                print("Temporary file removed")
                
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error processing document: {str(e)}'
        })
