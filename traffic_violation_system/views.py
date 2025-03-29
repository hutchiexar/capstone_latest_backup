from django.contrib.auth import logout, authenticate, login
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count, Q, F, Value, BooleanField, Case, When, IntegerField
from django.db.models.functions import Concat, TruncDate, TruncMonth, TruncWeek
from django.utils import timezone
from .models import Violation, Payment, UserProfile, ActivityLog, Violator, Announcement, AnnouncementAcknowledgment, LocationHistory, Operator, Vehicle, OperatorApplication, Driver
from .user_portal.models import UserNotification, UserReport
from django.conf import settings
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, Http404
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import cv2
import numpy as np
from datetime import datetime, timedelta, date
import base64
from django.core.files.base import ContentFile
from django.utils import timezone
from django.contrib.auth.models import User
import random
import string
from .utils import log_activity
import requests
import json
from django.urls import reverse
import qrcode
from io import BytesIO
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from idanalyzer import CoreAPI
import os
from django.db import models
from django.contrib.sessions.backends.db import SessionStore
from .forms import (
    NCAPViolationForm, OperatorForm, ImportOperatorsForm,
    ViolationForm, PaymentForm, ProfileUpdateForm, UserUpdateForm, 
    ViolatorForm, SignatureForm, OperatorForm,
    OperatorImportForm, OperatorApplicationForm, DriverImportForm, DriverForm
)
from django.core.exceptions import PermissionDenied
import logging
import time
import uuid
import csv, io
import pandas as pd
import xlwt
from django.template.loader import render_to_string
import pytz
import re
import sys
import openpyxl
from decimal import Decimal

# Initialize logger
logger = logging.getLogger(__name__)

# Define choices after importing models but before any views
VIOLATION_CHOICES = [
    ('Illegal Parking', 'Illegal Parking (DTS)'),
    ('Entering Prohibited Zones', 'Entering Prohibited Zones'),
    ('Obstruction', 'Obstruction'),
    ('Unlicensed Driver', 'Unlicensed Driver'),
    ('Permitting Hitching', 'Permitting Hitching/Over Loading Passenger(s)'),
    ('Unregistered MV', 'Unregistered MV'),
    ('Refusal to Convey', 'Refusal to convey to proper destination'),
    ('Discourteous Driver', 'Discourteous driver/Conduct'),
    ('Defective Lights', 'No/Defective Lights'),
    ('Expired OR/CR', 'Expired OR/CR'),
    ('No License', 'Failure to Carry DL'),
    ('No Permit', "No MAYOR'S PERMIT/MTOP/POP/PDP"),
    ('Overcharging', 'Overcharging'),
    ('DUI', 'Driving under the influence of liquor/drugs'),
    ('Defective Muffler', 'Operating a vehicle with Defective Muffler'),
    ('Dilapidated', 'Operating a Dilapidated Motorcab'),
    ('Reckless Driving', 'Reckless Driving'),
    ('Others', 'Others')
]

VEHICLE_CLASSIFICATIONS = [
    ('Private', 'Private'),
    ('Public', 'Public'),
    ('Government', 'Government'),
    ('Commercial', 'Commercial')
]

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
                fine_amount=request.POST.get('fine_amount'),
                is_tdz_violation=request.POST.get('is_tdz_violation') == 'on',
                vehicle_type=request.POST.get('vehicle_type'),
                plate_number=request.POST.get('plate_number'),
                color=request.POST.get('color'),
                classification=request.POST.get('classification'),
                registration_number=request.POST.get('registration_number'),
                registration_date=request.POST.get('registration_date') or None,
                vehicle_owner=request.POST.get('vehicle_owner'),
                vehicle_owner_address=request.POST.get('vehicle_owner_address'),
                status='PENDING',
                enforcer=request.user,
                enforcer_signature_date=timezone.now(),
                user_account=user_account  # Link to user account if provided
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
            
            # Check if this violation should be associated with a user account
            user_account_id = request.POST.get('user_account_id')
            violator_source = request.POST.get('violator_source')
            
            user_account = None
            if user_account_id and violator_source == 'user':
                try:
                    user_account = User.objects.get(id=user_account_id)
                    print(f"Found user account: {user_account.username} (ID: {user_account_id})")
                except User.DoesNotExist:
                    print(f"User account with ID {user_account_id} not found")
                    user_account = None
            
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
                    license_number=license_number or '',  # Handle case where there's no license
                    phone_number=request.POST.get('phone_number'),
                    address=request.POST.get('address')
                )

            # Get list of selected violations
            violation_types = request.POST.getlist('violation_type[]')
            print("Selected violations:", violation_types)
            
            if not violation_types:
                return JsonResponse({
                    'success': False,
                    'message': "Please select at least one violation type"
                })

            # Create the violation ticket
            violation = Violation.objects.create(
                violator=violator,
                location=request.POST.get('location'),
                fine_amount=request.POST.get('fine_amount'),
                is_tdz_violation=request.POST.get('is_tdz_violation') == 'on',
                vehicle_type=request.POST.get('vehicle_type'),
                plate_number=request.POST.get('plate_number'),
                color=request.POST.get('color'),
                classification=request.POST.get('classification'),
                registration_number=request.POST.get('registration_number'),
                registration_date=request.POST.get('registration_date') or None,
                vehicle_owner=request.POST.get('vehicle_owner'),
                vehicle_owner_address=request.POST.get('vehicle_owner_address'),
                status='PENDING',
                enforcer=request.user,
                enforcer_signature_date=timezone.now(),
                user_account=user_account  # Link to user account if provided
            )
            
            # Record the association in the activity log
            if user_account:
                ActivityLog.objects.create(
                    user=request.user,
                    action=f"Linked violation #{violation.id} to user account {user_account.username}",
                    details=f"Violation ID: {violation.id} linked to user: {user_account.username}",
                    category="violation"
                )
                
                # Create a notification for the user
                UserNotification.objects.create(
                    user=user_account,
                    message=f"A new violation has been issued to you. Violation ID: {violation.id}",
                    type="VIOLATION",
                    reference_id=violation.id
                )

            # Initialize signature_data as None
            signature_data = None

            # Handle signature if provided
            signature_input = request.POST.get('signature_data')
            if signature_input:
                try:
                    # Check if signature_data is a filename (new approach) or base64 data (old approach)
                    if ';base64,' in signature_input:
                        # Handle old base64 format
                        format_data = signature_input.split(';base64,', 1)
                        if len(format_data) == 2:
                            format_info, imgstr = format_data
                            ext = format_info.split('/')[-1]
                            signature_file = ContentFile(base64.b64decode(imgstr), name=f'signature_{violation.id}.{ext}')
                            violation.violator_signature = signature_file
                            violation.violator_signature_date = timezone.now()
                            violation.save()
                            signature_data = signature_file.name
                    else:
                        # Handle new filename format
                        signature_path = os.path.join('signatures', signature_input)
                        if os.path.exists(signature_path):
                            with open(signature_path, 'rb') as f:
                                violation.violator_signature.save(
                                    f'signature_{violation.id}.png',
                                    ContentFile(f.read()),
                                    save=True
                                )
                            violation.violator_signature_date = timezone.now()
                            violation.save()
                            signature_data = signature_input
                except Exception as e:
                    print(f"Error processing signature: {str(e)}")

            # Add violation types
            violation_types_list = []
            for violation_type in violation_types:
                violation_types_list.append(violation_type)
            
            # Store as JSON
            violation.violation_types = json.dumps(violation_types_list)
            
            # Also store the first type in the single field for compatibility
            if violation_types_list:
                violation.violation_type = violation_types_list[0]
            
            violation.save()

            # Create ticket data dictionary
            ticket_data = {
                'id': violation.id,
                'first_name': violator.first_name,
                'last_name': violator.last_name,
                'license_number': violator.license_number,
                'phone_number': violator.phone_number,
                'address': violator.address,
                'vehicle_type': violation.vehicle_type,
                'plate_number': violation.plate_number,
                'color': violation.color,
                'classification': violation.classification,
                'registration_number': violation.registration_number,
                'registration_date': violation.registration_date,
                'location': violation.location,
                'violations': violation_types,
                'fine_amount': float(violation.fine_amount),
                'is_tdz_violation': violation.is_tdz_violation,
                'violation_date': violation.violation_date.strftime('%Y-%m-%d %H:%M:%S'),
                'signature_data': signature_data,
                'enforcer_name': request.user.get_full_name(),
                'enforcer_id': request.user.userprofile.enforcer_id
            }

            return JsonResponse({
                'success': True,
                'message': 'Ticket issued successfully',
                'ticket_data': ticket_data
            })

        except Exception as e:
            print("Error:", str(e))
            return JsonResponse({
                'success': False,
                'message': str(e)
            })

    return render(request, 'violations/issue_direct_ticket.html', {
        'violation_choices': VIOLATION_CHOICES,
        'vehicle_classifications': VEHICLE_CLASSIFICATIONS
    })


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
            # Check for existing username
            username = request.POST['username']
            email = request.POST['email']
            license_number = request.POST['license_number']
            
            # Check for duplicate username
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists. Please choose a different username.')
                return render(request, 'registration/register.html', {'form_data': request.POST})
            
            # Check for duplicate email
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email address already exists. Please use a different email.')
                return render(request, 'registration/register.html', {'form_data': request.POST})
            
            # Check for duplicate license
            if UserProfile.objects.filter(license_number=license_number).exists():
                messages.error(request, 'License number already registered. Please contact support if this is an error.')
                return render(request, 'registration/register.html', {'form_data': request.POST})
            
            # Validate password match
            if request.POST['password'] != request.POST.get('confirm_password', ''):
                messages.error(request, 'Passwords do not match.')
                return render(request, 'registration/register.html', {'form_data': request.POST})
            
            # Create user
            user = User.objects.create_user(
                username=username,
                password=request.POST['password'],
                email=email,
                first_name=request.POST['first_name'],
                last_name=request.POST['last_name']
            )

            # Create user profile
            profile = UserProfile.objects.get(user=user)  # Get profile created by signal
            profile.phone_number = request.POST['phone_number']
            profile.address = request.POST['address']
            profile.role = 'USER'  # Set role as USER
            profile.license_number = license_number  # Add license number
            profile.save()

            # Handle avatar upload
            if 'avatar' in request.FILES:
                profile.avatar = request.FILES['avatar']
                profile.save()

            messages.success(request, 'Registration successful! Please login.')
            return redirect('login')
        except IntegrityError as e:
            # Handle database integrity errors (e.g., unique constraints)
            if 'username' in str(e).lower():
                messages.error(request, 'Username already exists. Please choose a different username.')
            elif 'email' in str(e).lower():
                messages.error(request, 'Email address already exists. Please use a different email.')
            elif 'license_number' in str(e).lower():
                messages.error(request, 'License number already registered. Please contact support if this is an error.')
            else:
                messages.error(request, f'Registration failed due to database error: {str(e)}')
            return render(request, 'registration/register.html', {'form_data': request.POST})
        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
            return render(request, 'registration/register.html', {'form_data': request.POST})

    return render(request, 'registration/register.html')


@login_required
def profile(request):
    # Get the user's violations
    user_violations = Violation.objects.filter(user_account=request.user)
    
    # Count open (unpaid) violations
    open_violations_count = user_violations.exclude(status__in=['PAID', 'SETTLED']).count()
    
    # Calculate total fines due
    total_fines_due = user_violations.exclude(status__in=['PAID', 'SETTLED']).aggregate(
        total=models.Sum('fine_amount', default=0)
    )['total'] or 0
    
    # Get latest notifications
    notifications = UserNotification.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Add context for showing messages
    context = {
        'user_violations': user_violations,
        'open_violations_count': open_violations_count,
        'total_fines_due': total_fines_due,
        'notifications': notifications,
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
        
        # Get previous violations for the same violator
        previous_violations = Violation.objects.filter(
            violator=violation.violator
        ).exclude(
            id=violation.id
        ).order_by('-violation_date')
        
        # Use the appropriate template
        template_name = 'violations/ncap_violation_detail_modal.html' if is_ncap else 'violations/violation_detail_modal.html'
        
        context = {
            'violation': violation,
            'is_modal': True,
            'previous_violations': previous_violations
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
    
    # Get other pending violations from the same violator (excluding current one)
    previous_violations = Violation.objects.filter(
        violator=violation.violator,
        status='PENDING'
    ).exclude(id=violation_id).order_by('-violation_date')
    
    context = {
        'violation': violation,
        'previous_violations': previous_violations
    }
    
    return render(request, 'violations/adjudication_form.html', context)

@login_required
def submit_adjudication(request, violation_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
    
    violation = get_object_or_404(Violation, id=violation_id)
    
    try:
        # Process the main violation
        process_adjudication(request, violation)
        
        # Check if there are batch violations to process
        batch_violation_ids_json = request.POST.get('batch_violation_ids', '[]')
        if batch_violation_ids_json and batch_violation_ids_json != '[]':
            batch_violation_ids = json.loads(batch_violation_ids_json)
            
            # Log batch adjudication in the activity log
            if batch_violation_ids:
                ActivityLog.objects.create(
                    user=request.user,
                    action="BATCH_ADJUDICATION",
                    details=f"Batch adjudicated {len(batch_violation_ids)} violations along with violation #{violation_id}",
                    category="violation"
                )
            
            # Process each batch violation
            for batch_id in batch_violation_ids:
                try:
                    batch_violation = Violation.objects.get(id=batch_id)
                    
                    # Get removed violation types for this batch item
                    removed_types_key = f'removed_violation_types_{batch_id}'
                    removed_types_json = request.POST.get(removed_types_key, '[]')
                    
                    # Process the batch violation with its specific removed violations
                    process_adjudication(request, batch_violation, removed_types_json)
                    
                except Violation.DoesNotExist:
                    logger.error(f"Batch violation ID {batch_id} not found during adjudication")
                except Exception as e:
                    logger.error(f"Error processing batch violation {batch_id}: {str(e)}")
        
        return redirect('adjudication_list')
    
    except Exception as e:
        logger.error(f"Error in submit_adjudication: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)})

def process_adjudication(request, violation, batch_removed_types_json=None):
    """Helper function to process a single violation adjudication"""
    adjudication_status = request.POST.get('adjudication_status', 'adjudicated')
    requires_approval = request.POST.get('requires_approval', 'true') == 'true'
    settled_status = request.POST.get('settled_status', 'false') == 'true'
    
    # Get form data
    total_penalty = request.POST.get('total_penalty', '0')
    remarks = request.POST.get('remarks', '')
    settlement_reason = request.POST.get('settlement_reason', '')
    
    # Parse removed violations - use batch specific ones if provided
    if batch_removed_types_json:
        removed_violations_json = batch_removed_types_json
    else:
        removed_violations_json = request.POST.get('removed_violations', '[]')
    
    removed_violations = []
    try:
        removed_violations = json.loads(removed_violations_json)
    except json.JSONDecodeError:
        logger.error(f"Error parsing removed violations JSON: {removed_violations_json}")
    
    # Handle payment due date
    payment_due_str = request.POST.get('payment_due', '')
    payment_due_date = None
    if payment_due_str:
        try:
            payment_due_date = datetime.strptime(payment_due_str, '%Y-%m-%d').date()
        except ValueError:
            logger.error(f"Invalid payment due date format: {payment_due_str}")
    
    # Set adjudication status based on form data
    if settled_status:
        violation.status = 'SETTLED'
        violation.fine_amount = 0
        remarks = f"SETTLED: {settlement_reason or remarks}"
    elif len(removed_violations) == len(violation.get_violation_types()):
        violation.status = 'REMOVED'
        violation.fine_amount = 0
        remarks = f"REMOVED: All violations removed. {remarks}"
    else:
        violation.status = 'ADJUDICATED'
        
        # For batch items, recalculate the fine amount proportionally if violations were removed
        if batch_removed_types_json and removed_violations:
            original_types = violation.get_violation_types()
            remaining_count = len(original_types) - len(removed_violations)
            if remaining_count > 0 and len(original_types) > 0:
                # Adjust fine proportionally based on removed violations
                original_fine = float(violation.fine_amount)
                violation.fine_amount = original_fine * (remaining_count / len(original_types))
            else:
                # All violations removed for this batch item
                violation.fine_amount = 0
                violation.status = 'REMOVED'
        else:
            # For main violation, use the submitted total penalty
            violation.fine_amount = float(total_penalty)
            
            # For the main violation, note if it includes batch penalties
            batch_ids_json = request.POST.get('batch_violation_ids', '[]')
            if batch_ids_json and batch_ids_json != '[]':
                try:
                    batch_ids = json.loads(batch_ids_json)
                    if batch_ids and len(batch_ids) > 0:
                        # Get information about batch violations
                        batch_violations = Violation.objects.filter(id__in=batch_ids)
                        total_batch_amount = sum([v.fine_amount for v in batch_violations])
                        
                        # Create detailed batch information
                        batch_details = "\n\n=== BATCH ADJUDICATION SUMMARY ===\n"
                        batch_details += f"This adjudication includes {len(batch_ids)} additional violation(s) with a total of ₱{total_batch_amount:.2f}.\n"
                        batch_details += "Batch violations included:\n"
                        
                        for v in batch_violations:
                            batch_details += f"- Citation #{v.id}: {v.violation_type} (₱{v.fine_amount:.2f}) from {v.violation_date.strftime('%b %d, %Y')}\n"
                        
                        # Add batch details to remarks
                        remarks += batch_details
                except json.JSONDecodeError:
                    logger.error(f"Error parsing batch violation IDs: {batch_ids_json}")
                except Exception as e:
                    logger.error(f"Error processing batch details: {str(e)}")
        
        # Remove specific violations if any were unchecked
        if removed_violations:
            current_types = violation.get_violation_types()
            remaining_types = [t for t in current_types if t not in removed_violations]
            violation.violation_type = ', '.join(remaining_types)
    
    # Record adjudication details
    violation.adjudicated_by = request.user
    violation.adjudication_date = timezone.now()
    violation.adjudication_remarks = remarks
    violation.payment_due_date = payment_due_date
    violation.requires_approval = requires_approval
    
    # Save the updated violation
    violation.save()
    
    # Log the adjudication
    ActivityLog.objects.create(
        user=request.user,
        action="ADJUDICATION",
        details=f"Adjudicated violation #{violation.id} as {violation.status}",
        category="violation"
    )
    
    return violation

@login_required
def announcements_list(request):
    user_role = request.user.userprofile.role
    current_time = timezone.now()
    
    # Enhanced search functionality
    search_query = request.GET.get('search', '').strip()
    category_filter = request.GET.get('category', '')
    priority_filter = request.GET.get('priority', '')
    
    # For admins and supervisors, show all announcements by default including inactive ones
    if user_role in ['ADMIN', 'SUPERVISOR']:
        announcements = Announcement.objects.all().select_related('created_by').order_by('-created_at')
    else:
        # For regular users, show only active announcements
        announcements = Announcement.objects.filter(
            is_active=True
        ).select_related('created_by').order_by('-created_at')
    
    # Apply filters
    if search_query:
        announcements = announcements.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(created_by__first_name__icontains=search_query) |
            Q(created_by__last_name__icontains=search_query) |
            Q(created_by__userprofile__enforcer_id__icontains=search_query)
        ).distinct()
    
    if category_filter:
        announcements = announcements.filter(category=category_filter)
        
    if priority_filter:
        announcements = announcements.filter(priority=priority_filter)
    
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
        'category_filter': category_filter,
        'priority_filter': priority_filter,
        'total_count': paginator.count,
        'categories': Announcement.CATEGORY_CHOICES,
        'priorities': Announcement.PRIORITY_CHOICES,
        'admin_view': ''  # No longer needed but keep for backward compatibility
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
        rich_content = request.POST.get('rich_content')
        priority = request.POST.get('priority', 'MEDIUM')
        category = request.POST.get('category', 'GENERAL')
        target_audience = request.POST.get('target_audience', 'ALL')
        geographic_area = request.POST.get('geographic_area')
        
        # Boolean fields
        is_active = request.POST.get('is_active') == 'on'
        is_popup = request.POST.get('is_popup') == 'on'
        requires_acknowledgment = request.POST.get('requires_acknowledgment') == 'on'
        send_as_notification = request.POST.get('send_as_notification') == 'on'
        
        # Date fields
        publish_date = request.POST.get('publish_date')
        publish_date = timezone.make_aware(datetime.strptime(publish_date, '%Y-%m-%dT%H:%M')) if publish_date else None
        
        expiration_date = request.POST.get('expiration_date')
        expiration_date = timezone.make_aware(datetime.strptime(expiration_date, '%Y-%m-%dT%H:%M')) if expiration_date else None

        if title and content:
            announcement = Announcement.objects.create(
                title=title,
                content=content,
                rich_content=rich_content,
                priority=priority,
                category=category,
                target_audience=target_audience,
                geographic_area=geographic_area,
                is_active=is_active,
                is_popup=is_popup,
                requires_acknowledgment=requires_acknowledgment,
                publish_date=publish_date,
                expiration_date=expiration_date,
                created_by=request.user
            )
            
            # Create notifications if send_as_notification is checked or if it's a popup
            if send_as_notification or is_popup:
                create_notifications_from_announcement(announcement)
                
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
        rich_content = request.POST.get('rich_content')
        priority = request.POST.get('priority')
        category = request.POST.get('category', 'GENERAL')
        target_audience = request.POST.get('target_audience', 'ALL')
        geographic_area = request.POST.get('geographic_area')
        
        # Boolean fields
        is_active = request.POST.get('is_active') == 'on'
        is_popup = request.POST.get('is_popup') == 'on'
        requires_acknowledgment = request.POST.get('requires_acknowledgment') == 'on'
        send_as_notification = request.POST.get('send_as_notification') == 'on'
        
        # Date fields
        publish_date = request.POST.get('publish_date')
        publish_date = timezone.make_aware(datetime.strptime(publish_date, '%Y-%m-%dT%H:%M')) if publish_date else None
        
        expiration_date = request.POST.get('expiration_date')
        expiration_date = timezone.make_aware(datetime.strptime(expiration_date, '%Y-%m-%dT%H:%M')) if expiration_date else None

        if title and content:
            announcement.title = title
            announcement.content = content
            announcement.rich_content = rich_content
            announcement.priority = priority
            announcement.category = category
            announcement.target_audience = target_audience
            announcement.geographic_area = geographic_area
            announcement.is_active = is_active
            announcement.is_popup = is_popup
            announcement.requires_acknowledgment = requires_acknowledgment
            announcement.publish_date = publish_date
            announcement.expiration_date = expiration_date
            announcement.save()
            
            # Create notifications if send_as_notification is checked or if it's a popup
            if send_as_notification or is_popup:
                create_notifications_from_announcement(announcement)
                
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

def create_notifications_from_announcement(announcement):
    """Create user notifications from an announcement"""
    try:
        # Determine which users should receive this notification based on target audience
        if announcement.target_audience == 'ALL':
            users = User.objects.all()
        else:
            # Filter users by role matching the target audience
            users = User.objects.filter(userprofile__role=announcement.target_audience)
        
        # Create a notification for each user
        for user in users:
            # Check if notification referencing this announcement already exists for user
            if not UserNotification.objects.filter(user=user, reference_id=announcement.id, type='SYSTEM').exists():
                notification_type = 'SYSTEM'
                if announcement.priority == 'HIGH':
                    notification_type = 'VIOLATION'  # Use violation type for high priority
                
                UserNotification.objects.create(
                    user=user,
                    type=notification_type,
                    message=f"{announcement.title} - {announcement.content[:100]}" + ('...' if len(announcement.content) > 100 else ''),
                    reference_id=announcement.id
                )
        
        return True
    except Exception as e:
        print(f"Error creating notifications from announcement: {str(e)}")
        return False

@login_required
def delete_announcement(request, announcement_id):
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, 'You do not have permission to delete announcements.')
        return redirect('announcements_list')

    announcement = get_object_or_404(Announcement, id=announcement_id)
    announcement.delete()
    messages.success(request, 'Announcement deleted successfully.')
    return redirect('announcements_list')

@login_required
def get_popup_announcement(request):
    """API endpoint to get the latest popup announcement"""
    try:
        user_role = request.user.userprofile.role
        current_time = timezone.now()
        
        # Debug info
        print(f"Checking popup announcements for user {request.user.username}, role: {user_role}")
        
        # Get the latest active popup announcement for this user's role
        announcement = Announcement.objects.filter(
            is_active=True, 
            is_popup=True
        ).filter(
            # Check for target audience
            Q(target_audience='ALL') | Q(target_audience=user_role)
        ).filter(
            # Check for publish and expiration dates
            Q(publish_date__isnull=True) | Q(publish_date__lte=current_time)
        ).filter(
            Q(expiration_date__isnull=True) | Q(expiration_date__gt=current_time)
        ).order_by('-created_at').first()
        
        if announcement:
            # Debug
            print(f"Found popup announcement: {announcement.title} (ID: {announcement.id})")
            
            # Check if user needs to acknowledge and has already done so
            acknowledged = False
            if announcement.requires_acknowledgment:
                acknowledged = AnnouncementAcknowledgment.objects.filter(
                    announcement=announcement,
                    user=request.user
                ).exists()
                
                if acknowledged:
                    print(f"User has already acknowledged announcement {announcement.id}")
                    return JsonResponse({'status': 'no_announcements'})
            
            # Increment view count
            announcement.view_count += 1
            announcement.save(update_fields=['view_count'])
            
            # Prepare response data
            data = {
                'id': announcement.id,
                'title': announcement.title,
                'content': announcement.rich_content if announcement.rich_content else announcement.content,
                'priority': announcement.priority,
                'created_at': announcement.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'created_by': f"{announcement.created_by.first_name} {announcement.created_by.last_name}",
                'category': announcement.get_category_display() if announcement.category else None,
                'requires_acknowledgment': announcement.requires_acknowledgment
            }
            return JsonResponse(data)
        else:
            print("No active popup announcements found")
        
        return JsonResponse({'status': 'no_announcements'})
    except Exception as e:
        print(f"Error in get_popup_announcement: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def reset_popup_announcement(request, announcement_id):
    """Reset a popup announcement so it shows again for all users"""
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, 'You do not have permission to reset popup announcements.')
        return redirect('announcements_list')
        
    announcement = get_object_or_404(Announcement, id=announcement_id)
    
    # Make sure it's a popup announcement
    if not announcement.is_popup:
        messages.error(request, 'This is not a popup announcement.')
        return redirect('announcements_list')
    
    # Update the announcement to force a refresh (updated_at will change)
    announcement.save()
    
    # Clear session data for this announcement for all active sessions
    from django.contrib.sessions.models import Session
    active_sessions = Session.objects.filter(expire_date__gt=timezone.now())
    
    session_count = 0
    for session in active_sessions:
        try:
            session_data = session.get_decoded()
            if 'seen_popup_announcements' in session_data:
                seen_announcements = session_data['seen_popup_announcements']
                if announcement.id in seen_announcements:
                    seen_announcements.remove(announcement.id)
                    session_data['seen_popup_announcements'] = seen_announcements
                    session.session_data = SessionStore().encode(session_data)
                    session.save()
                    session_count += 1
        except:
            # Skip any problematic sessions
            continue
            
    messages.success(request, f'Popup announcement reset for {session_count} active sessions.')
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
    # For GET requests or non-POST requests, return a clear message
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error', 
            'message': 'This endpoint requires POST method'
        }, status=405)
    
    # If user is not an enforcer, return a clear message instead of a generic error
    if request.user.userprofile.role != 'ENFORCER':
        return JsonResponse({
            'status': 'error', 
            'message': 'Location tracking is only available for enforcers'
        }, status=403)

    try:
        data = json.loads(request.body)
        profile = request.user.userprofile
        
        # Update location efficiently
        profile.latitude = data['latitude']
        profile.longitude = data['longitude']
        profile.last_location_update = timezone.now()
        profile.is_active_duty = data.get('is_active', True)
        
        # Save additional data if provided
        if 'accuracy' in data:
            profile.accuracy = data['accuracy']
        if 'heading' in data:
            profile.heading = data['heading']
        if 'speed' in data:
            profile.speed = data['speed']
        if 'battery_level' in data:
            profile.battery_level = data['battery_level']
        if 'device_info' in data:
            profile.device_info = data['device_info']
        
        # Use update_fields to optimize the query
        profile.save()
        
        # Also save to location history for path tracking
        LocationHistory.objects.create(
            user_profile=profile,
            latitude=profile.latitude,
            longitude=profile.longitude,
            accuracy=profile.accuracy if hasattr(profile, 'accuracy') else None,
            heading=profile.heading if hasattr(profile, 'heading') else None,
            speed=profile.speed if hasattr(profile, 'speed') else None,
            is_active_duty=profile.is_active_duty,
            battery_level=profile.battery_level if hasattr(profile, 'battery_level') else None,
            device_info=profile.device_info if hasattr(profile, 'device_info') else None
        )
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.error(f"Error updating location: {str(e)}")
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

    # Base query to get all enforcers
    base_query = UserProfile.objects.filter(
        role='ENFORCER',
        latitude__isnull=False,
        longitude__isnull=False
    ).select_related('user').only(
        'id', 'user__first_name', 'user__last_name',
        'enforcer_id', 'role', 'latitude', 'longitude',
        'last_location_update', 'avatar', 'is_active_duty'
    )
    
    # Process all enforcers and mark them as active/inactive based on last update time
    locations = []
    for profile in base_query:
        is_active = profile.is_active_duty and profile.last_location_update and profile.last_location_update > inactive_threshold
        
        locations.append({
            'id': profile.id,
            'name': f"{profile.user.first_name} {profile.user.last_name}",
            'enforcer_id': profile.enforcer_id,
            'role': profile.role,
            'latitude': float(profile.latitude),
            'longitude': float(profile.longitude),
            'last_update': profile.last_location_update.isoformat() if profile.last_location_update else None,
            'avatar_url': profile.avatar.url if profile.avatar else None,
            'is_active': is_active,
            'inactive_time': (current_time - profile.last_location_update).total_seconds() // 60 if profile.last_location_update else None
        })

    return JsonResponse({
        'status': 'success',
        'locations': locations
    })

@login_required
def get_enforcer_path(request):
    """Get historical location data for an enforcer to display their movement path"""
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR', 'ENFORCER']:
        return JsonResponse({
            'status': 'error',
            'message': 'Permission denied'
        }, status=403)
    
    enforcer_id = request.GET.get('enforcer_id')
    hours = int(request.GET.get('hours', 24))  # Default to 24 hours
    
    if not enforcer_id:
        return JsonResponse({
            'status': 'error',
            'message': 'Enforcer ID is required'
        }, status=400)
    
    try:
        # Get the enforcer profile
        enforcer_profile = UserProfile.objects.get(id=enforcer_id)
        
        # Get location history for the specified time range
        time_threshold = timezone.now() - timezone.timedelta(hours=hours)
        
        path_query = LocationHistory.objects.filter(
            user_profile=enforcer_profile,
            timestamp__gt=time_threshold
        ).order_by('timestamp')
        
        # Format the path data
        path = [{
            'latitude': float(point.latitude),
            'longitude': float(point.longitude),
            'timestamp': point.timestamp.isoformat(),
            'is_active': point.is_active_duty,
            'accuracy': point.accuracy,
            'speed': point.speed,
            'heading': point.heading
        } for point in path_query]
        
        return JsonResponse({
            'status': 'success',
            'enforcer_id': enforcer_id,
            'enforcer_name': f"{enforcer_profile.user.first_name} {enforcer_profile.user.last_name}",
            'hours': hours,
            'path': path
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Enforcer not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error fetching enforcer path: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=500)

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
            # Check if the fine amount is zero, mark as SETTLED instead of APPROVED
            if violation.fine_amount == 0:
                violation.status = 'SETTLED'
                
                # Log the activity for zero amount (settled) cases
                log_action = 'Approved & Settled'
                log_details = f'Approved and settled Violation #{violation.id} (zero amount)'
            else:
                violation.status = 'APPROVED'
                
                # Log the activity for regular approvals
                log_action = 'Approved Adjudication'
                log_details = f'Approved adjudication for Violation #{violation.id}'
            
            violation.approved_by = request.user
            violation.approval_date = timezone.now()
            violation.save()
            
            # Log the activity
            log_activity(
                user=request.user,
                action=log_action,
                details=log_details,
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
    # Exclude violations with zero fine amounts as they're auto-settled
    violations = Violation.objects.filter(
        status='APPROVED'
    ).exclude(
        fine_amount=0
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

def track_violation(request):
    """View for tracking violations by ticket number"""
    if request.method == 'POST':
        ticket_number = request.POST.get('ticket_number')
        try:
            violation = Violation.objects.get(id=ticket_number)
            return render(request, 'track_violation.html', {
                'violation': violation,
                'found': True
            })
        except Violation.DoesNotExist:
            return render(request, 'track_violation.html', {
                'error': 'No violation found with this ticket number.',
                'found': False
            })
    return render(request, 'track_violation.html', {'found': None})

@login_required
def save_signature(request):
    if request.method == 'POST' and request.FILES.get('signature'):
        try:
            signature_file = request.FILES['signature']
            # Save to signatures directory
            filename = signature_file.name
            filepath = os.path.join('signatures', filename)
            
            # Ensure signatures directory exists
            os.makedirs('signatures', exist_ok=True)
            
            # Save the file
            with open(filepath, 'wb+') as destination:
                for chunk in signature_file.chunks():
                    destination.write(chunk)
            
            return JsonResponse({
                'success': True,
                'filename': filename,
                'message': 'Signature saved successfully'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error saving signature: {str(e)}'
            }, status=500)
    return JsonResponse({
        'success': False,
        'message': 'Invalid request'
    }, status=400)

@login_required
def get_signature(request, filename):
    try:
        filepath = os.path.join('signatures', filename)
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                return HttpResponse(f.read(), content_type='image/png')
        return HttpResponse('Signature not found', status=404)
    except Exception as e:
        return HttpResponse(f'Error retrieving signature: {str(e)}', status=500)

@login_required
def acknowledge_announcement(request, announcement_id):
    """API endpoint to acknowledge an announcement"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    
    try:
        announcement = get_object_or_404(Announcement, id=announcement_id)
        
        # Record acknowledgment
        AnnouncementAcknowledgment.objects.get_or_create(
            announcement=announcement,
            user=request.user
        )
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def resend_announcement_notification(request, announcement_id):
    """Resend an announcement as a notification to users"""
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, 'You do not have permission to resend announcement notifications.')
        return redirect('announcements_list')
    
    announcement = get_object_or_404(Announcement, id=announcement_id)
    
    # Send the announcement as a notification
    if create_notifications_from_announcement(announcement):
        messages.success(request, 'Announcement has been sent as notification successfully.')
    else:
        messages.error(request, 'Error sending notifications. Please try again.')
    
    return redirect('announcements_list')

@login_required
def mark_notification_read(request, notification_id):
    """API endpoint to mark a notification as read"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    
    try:
        notification = get_object_or_404(
            UserNotification,
            id=notification_id,
            user=request.user
        )
        notification.is_read = True
        notification.save()
        
        # Count unread notifications for the user
        unread_count = UserNotification.objects.filter(
            user=request.user, 
            is_read=False
        ).count()
        
        return JsonResponse({
            'status': 'success',
            'unread_count': unread_count
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def get_announcement_details(request, announcement_id):
    """API endpoint to get announcement details"""
    try:
        announcement = get_object_or_404(Announcement, id=announcement_id)
        
        # Check if user is allowed to see this announcement based on target audience
        if announcement.target_audience != 'ALL' and announcement.target_audience != request.user.userprofile.role:
            return JsonResponse({'status': 'error', 'message': 'You do not have permission to view this announcement'}, status=403)
        
        # Increment view count
        announcement.view_count += 1
        announcement.save()
        
        # Check if user has acknowledged this announcement
        acknowledged = AnnouncementAcknowledgment.objects.filter(
            announcement=announcement,
            user=request.user
        ).exists()
        
        # Format data for response
        data = {
            'id': announcement.id,
            'title': announcement.title,
            'content': announcement.content,
            'rich_content': announcement.rich_content,
            'priority': announcement.priority,
            'category': announcement.category,
            'created_at': announcement.created_at.isoformat(),
            'created_by': announcement.created_by.get_full_name() or announcement.created_by.username,
            'requires_acknowledgment': announcement.requires_acknowledgment,
            'is_acknowledged': acknowledged,
            'view_count': announcement.view_count
        }
        
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def save_ncap_violation(request):
    if request.method == 'POST':
        form = NCAPViolationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Process the uploaded image if it exists
                if 'image' in request.FILES:
                    image = request.FILES['image']
                    # Check if file extension is valid
                    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
                    ext = os.path.splitext(image.name)[1].lower()
                    
                    if not any(ext == valid_ext for valid_ext in valid_extensions):
                        messages.error(request, f"Unsupported file type. Please upload a JPG, PNG, or WEBP image.")
                        return redirect('create_ncap_violation')
                    
                    # Check file size (limit to 5MB)
                    if image.size > 5 * 1024 * 1024:  # 5MB in bytes
                        messages.error(request, "Image file is too large. Please upload an image less than 5MB.")
                        return redirect('create_ncap_violation')
                
                # Save the violation
                violation = form.save(commit=False)
                violation.enforcer = request.user
                violation.save()
                
                # Log the activity
                log_activity(
                    user=request.user,
                    action='Created NCAP Violation',
                    details=f'NCAP Violation created for {violation.violator.license_number}',
                    category='violation'
                )
                
                messages.success(request, "NCAP violation has been recorded successfully.")
                return redirect('ncap_violations_list')
                
            except Exception as e:
                # Log the error for debugging
                import traceback
                logger.error(f"Error saving NCAP violation: {str(e)}")
                logger.error(traceback.format_exc())
                
                # Provide a user-friendly error message
                error_message = str(e)
                if "filename" in error_message.lower():
                    messages.error(request, "Error saving the image file. Please try with a different image or a simpler filename.")
                else:
                    messages.error(request, f"An error occurred while saving the violation: {error_message}")
                
                return redirect('create_ncap_violation')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = NCAPViolationForm()
    
    # Return to the form with context
    context = {
        'form': form,
        'title': 'Create NCAP Violation',
        'button_text': 'Record Violation'
    }
    return render(request, 'violations/create_ncap_violation.html', context)

@login_required
def create_ncap_violation(request):
    """
    View function to display the form for creating a new NCAP violation
    """
    if request.method == 'POST':
        # The POST handling is done in save_ncap_violation view
        # This is just a fallback in case form is submitted directly to this URL
        return save_ncap_violation(request)
    
    # Create a new empty form
    form = NCAPViolationForm()
    
    # Render the template with the form
    context = {
        'form': form,
        'title': 'Create NCAP Violation',
        'button_text': 'Record Violation'
    }
    
    return render(request, 'violations/create_ncap_violation.html', context)

@login_required
def operator_list(request):
    """View to list all operators with search and pagination"""
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, "You don't have permission to access the operators management page.")
        return redirect('home')
    
    # Search functionality
    query = request.GET.get('q', '')
    if query:
        operators = Operator.objects.filter(
            Q(last_name__icontains=query) |
            Q(first_name__icontains=query) |
            Q(new_pd_number__icontains=query) |
            Q(old_pd_number__icontains=query) |
            Q(address__icontains=query)
        )
    else:
        operators = Operator.objects.all()
    
    # Clean up middle_initial values - convert 'nan' to None
    for operator in operators:
        if operator.middle_initial == 'nan':
            operator.middle_initial = None
        
    # Pagination
    paginator = Paginator(operators, 10)  # Show 10 operators per page
    page_number = request.GET.get('page')
    operators_page = paginator.get_page(page_number)
    
    context = {
        'operators': operators_page,
        'query': query,
        'title': 'Operators Management',
    }
    
    # Log activity
    ActivityLog.objects.create(
        user=request.user,
        action="Viewed operators list",
        category="general"
    )
    
    return render(request, 'operators/operator_list.html', context)


@login_required
def operator_detail(request, pk):
    """View to display detailed information about an operator"""
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to view operator details.")
        return redirect('login')
    
    # Get the operator or return 404
    operator = get_object_or_404(Operator, pk=pk)
    
    # Get vehicles associated with this operator
    vehicles = Vehicle.objects.filter(operator=operator).order_by('-created_at')
    
    context = {
        'operator': operator,
        'vehicles': vehicles,
        'title': f'Operator Details: {operator.full_name()}',
    }
    
    # Log activity
    ActivityLog.objects.create(
        user=request.user,
        action=f"Viewed operator details for: {operator.full_name()}",
        category="general"
    )
    
    return render(request, 'operators/operator_detail.html', context)


@login_required
def operator_create(request):
    """View to create a new operator"""
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, "You don't have permission to create operators.")
        return redirect('operator_list')
    
    if request.method == 'POST':
        form = OperatorForm(request.POST)
        if form.is_valid():
            operator = form.save()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action=f"Created operator: {operator.last_name}, {operator.first_name}",
                category="user"
            )
            
            messages.success(request, f"Operator {operator.last_name}, {operator.first_name} created successfully.")
            return redirect('operator_list')
    else:
        form = OperatorForm()
    
    context = {
        'form': form,
        'title': 'Create Operator',
    }
    
    return render(request, 'operators/operator_form.html', context)


@login_required
def operator_update(request, pk):
    """View to update an existing operator"""
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, "You don't have permission to update operators.")
        return redirect('operator_list')
    
    operator = get_object_or_404(Operator, pk=pk)
    
    if request.method == 'POST':
        form = OperatorForm(request.POST, instance=operator)
        if form.is_valid():
            operator = form.save()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action=f"Updated operator: {operator.last_name}, {operator.first_name}",
                category="user"
            )
            
            messages.success(request, f"Operator {operator.last_name}, {operator.first_name} updated successfully.")
            return redirect('operator_list')
    else:
        form = OperatorForm(instance=operator)
    
    context = {
        'form': form,
        'operator': operator,
        'title': 'Update Operator',
    }
    
    return render(request, 'operators/operator_form.html', context)


@login_required
def operator_delete(request, pk):
    """View to delete an operator"""
    if not request.user.userprofile.role in ['ADMIN']:
        messages.error(request, "You don't have permission to delete operators.")
        return redirect('operator_list')
    
    operator = get_object_or_404(Operator, pk=pk)
    
    if request.method == 'POST':
        operator_name = f"{operator.last_name}, {operator.first_name}"
        operator.delete()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action=f"Deleted operator: {operator_name}",
            category="user"
        )
        
        messages.success(request, f"Operator {operator_name} deleted successfully.")
        return redirect('operator_list')
    
    context = {
        'operator': operator,
        'title': 'Delete Operator',
    }
    
    return render(request, 'operators/operator_confirm_delete.html', context)


@login_required
def operator_vehicles(request, operator_id):
    """View to display all vehicles associated with an operator"""
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR', 'CLERK', 'TREASURER']:
        messages.error(request, "You don't have permission to view operator vehicles.")
        return redirect('operator_list')
    
    operator = get_object_or_404(Operator, pk=operator_id)
    vehicles = Vehicle.objects.filter(operator=operator)
    
    # Log activity
    ActivityLog.objects.create(
        user=request.user,
        action=f"Viewed vehicles for operator: {operator.last_name}, {operator.first_name}",
        category="user"
    )
    
    context = {
        'operator': operator, 
        'vehicles': vehicles,
        'title': f"{operator.first_name} {operator.last_name}'s Vehicles",
    }
    
    return render(request, 'operators/operator_vehicles.html', context)


@login_required
def operator_import(request):
    """View to import operators from an Excel or CSV file"""
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, "You don't have permission to import operators.")
        return redirect('operator_list')
    
    if request.method == 'POST':
        form = OperatorImportForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            
            # Get file extension to determine file type
            extension = file.name.split('.')[-1].lower()
            
            try:
                if extension == 'csv':
                    # Process CSV file
                    data = []
                    decoded_file = file.read().decode('utf-8')
                    io_string = io.StringIO(decoded_file)
                    reader = csv.DictReader(io_string)
                    for row in reader:
                        data.append(row)
                elif extension in ['xlsx', 'xls']:
                    # Process Excel file
                    df = pd.read_excel(file)
                    data = df.to_dict('records')
                    
                    # Debug info for the first few rows to diagnose the issue
                    print(f"Excel file columns: {df.columns.tolist()}")
                    print(f"First row: {data[0] if data else 'No data'}")
                    
                    # Check if the file has the header row as first data row or has unnamed columns
                    # This is to handle different Excel file formats that users might upload
                    cleaned_data = []
                    for row in data:
                        # Skip rows with NaN or None values in key fields
                        if pd.isna(row.get('LAST_NAME')) and pd.isna(row.get('last_name')) and pd.isna(row.get('Unnamed: 1')):
                            continue
                            
                        # Create a new row with cleaned data
                        clean_row = {}
                        
                        # Try to extract the data, accounting for various column formats
                        # For 'POTPOT OPERATOR 2024-2025' format where first row might be column headers
                        if 'POTPOT OPERATOR 2024-2025' in row or 'Unnamed: 1' in row:
                            # The first row likely contains header info
                            if row.get('POTPOT OPERATOR 2024-2025') == 'LASTNAME' or row.get('Unnamed: 1') == 'FIRST NAME':
                                continue  # Skip header rows
                                
                            # Extract values from possible column structures
                            clean_row['last_name'] = row.get('POTPOT OPERATOR 2024-2025')
                            clean_row['first_name'] = row.get('Unnamed: 1')
                            clean_row['middle_initial'] = row.get('Unnamed: 2')
                            clean_row['address'] = row.get('Unnamed: 3')
                            clean_row['old_pd_number'] = row.get('Unnamed: 4')
                            clean_row['new_pd_number'] = row.get('Unnamed: 5')
                        else:
                            # Try standard column names (with variations)
                            clean_row['last_name'] = row.get('LAST_NAME') or row.get('last_name') or row.get('Last Name')
                            clean_row['first_name'] = row.get('FIRST_NAME') or row.get('first_name') or row.get('First Name')
                            clean_row['middle_initial'] = row.get('M_I') or row.get('M.I.') or row.get('middle_initial')
                            clean_row['address'] = row.get('ADDRESS') or row.get('address')
                            clean_row['old_pd_number'] = row.get('OLD_PD_NO') or row.get('old_pd_number') or row.get('Old P.D. No.')
                            clean_row['new_pd_number'] = row.get('NEW_PD_NO') or row.get('new_pd_number') or row.get('NEW P.O NO.') or row.get('New P.D. No.')
                        
                        # Validate required fields
                        if clean_row.get('last_name') and clean_row.get('first_name') and clean_row.get('new_pd_number'):
                            # Convert any float types (from Excel) to strings
                            for key, value in clean_row.items():
                                if isinstance(value, float) and not pd.isna(value):
                                    # Convert to integer first if it's a whole number to remove .0
                                    if value.is_integer():
                                        clean_row[key] = str(int(value))
                                    else:
                                        clean_row[key] = str(value)
                            
                            cleaned_data.append(clean_row)
                    
                    # Replace the original data with the cleaned data
                    data = cleaned_data
                else:
                    messages.error(request, f"Unsupported file format: {extension}. Please upload a CSV or Excel file.")
                    return redirect('operator_import')
                
                # Preview the data
                context = {
                    'data': data,
                    'title': 'Preview Imported Operators',
                    'form': form,
                }
                
                # Store data in session for later processing
                request.session['import_data'] = data
                
                return render(request, 'operators/operator_import_preview.html', context)
                
            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
                return redirect('operator_import')
    else:
        form = OperatorImportForm()
    
    context = {
        'form': form,
        'title': 'Import Operators',
    }
    
    return render(request, 'operators/operator_import.html', context)


@login_required
def operator_import_confirm(request):
    """View to save imported operators after preview"""
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, "You don't have permission to import operators.")
        return redirect('operator_list')
    
    if request.method == 'POST':
        import_data = request.session.get('import_data', [])
        if not import_data:
            messages.error(request, "No import data found. Please try again.")
            return redirect('operator_import')
        
        # Process the data
        success_count = 0
        error_count = 0
        error_messages = []
        
        for row in import_data:
            try:
                # With our cleaned data, we can directly access the lowercase keys
                last_name = row.get('last_name')
                first_name = row.get('first_name')
                middle_initial = row.get('middle_initial')
                address = row.get('address')
                old_pd_number = row.get('old_pd_number')
                new_pd_number = row.get('new_pd_number')
                
                # Skip empty rows
                if not last_name or not first_name or not new_pd_number:
                    continue
                
                # Check if the operator already exists
                existing = Operator.objects.filter(new_pd_number=new_pd_number).first()
                if existing:
                    # Update existing operator
                    existing.last_name = last_name
                    existing.first_name = first_name
                    existing.middle_initial = middle_initial
                    existing.address = address
                    existing.old_pd_number = old_pd_number
                    existing.save()
                else:
                    # Create new operator
                    Operator.objects.create(
                        last_name=last_name,
                        first_name=first_name,
                        middle_initial=middle_initial,
                        address=address,
                        old_pd_number=old_pd_number,
                        new_pd_number=new_pd_number
                    )
                
                success_count += 1
            
            except Exception as e:
                error_count += 1
                error_messages.append(f"Error with row {success_count + error_count}: {str(e)}")
                continue
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action=f"Imported operators: {success_count} successful, {error_count} failed",
            category="user"
        )
        
        # Clear the session data
        del request.session['import_data']
        
        if error_count > 0:
            # Log the first few errors to help with debugging
            error_details = "; ".join(error_messages[:5])
            if len(error_messages) > 5:
                error_details += f"; and {len(error_messages) - 5} more errors"
            messages.warning(request, f"Import completed with issues: {success_count} operators imported successfully, {error_count} failed. Errors: {error_details}")
        else:
            messages.success(request, f"Import completed: {success_count} operators imported successfully.")
        
        return redirect('operator_list')
    
    return redirect('operator_import')


@login_required
def operator_export_excel(request):
    """View to export operators to Excel"""
    if not request.user.userprofile.role in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, "You don't have permission to export operators.")
        return redirect('home')
    
    # Create an Excel workbook
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Operators"
    
    # Add headers
    headers = ['Last Name', 'First Name', 'Middle Initial', 'Address', 'Old PD Number', 'New PD Number']
    for col_num, header in enumerate(headers, 1):
        sheet.cell(row=1, column=col_num).value = header
        sheet.cell(row=1, column=col_num).font = openpyxl.styles.Font(bold=True)
    
    # Add data rows
    operators = Operator.objects.all().order_by('last_name', 'first_name')
    for row_num, operator in enumerate(operators, 2):
        row = [
            operator.last_name,
            operator.first_name,
            operator.middle_initial or '',
            operator.address,
            operator.old_pd_number or '',
            operator.new_pd_number
        ]
        for col_num, cell_value in enumerate(row, 1):
            sheet.cell(row=row_num, column=col_num).value = cell_value
    
    # Adjust column widths
    for column in sheet.columns:
        max_length = 0
        column_letter = openpyxl.utils.get_column_letter(column[0].column)
        for cell in column:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        adjusted_width = max_length + 2
        sheet.column_dimensions[column_letter].width = adjusted_width
    
    # Create response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=operators_export.xlsx'
    
    # Log activity
    ActivityLog.objects.create(
        user=request.user,
        action=f"Exported operators to Excel",
        category="user"
    )
    
    # Save the workbook to the response
    workbook.save(response)
    return response


@login_required
def operator_apply(request):
    if request.user.userprofile.is_operator:
        messages.info(request, 'You are already registered as an operator.')
        return redirect('operator_dashboard')
            
    if request.method == 'POST':
        form = OperatorApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.save()
            
            messages.success(request, 'Your application has been submitted successfully. We will review it shortly.')
            return redirect('operator_application_status')
    else:
        form = OperatorApplicationForm()
            
    return render(request, 'operators/operator_apply.html', {
        'form': form
    })

@login_required
def operator_application_status(request):
    try:
        application = OperatorApplication.objects.filter(user=request.user).latest('submitted_at')
        return render(request, 'operators/operator_application_status.html', {
            'application': application
        })
    except OperatorApplication.DoesNotExist:
        messages.info(request, 'You have not submitted an operator application yet.')
        return redirect('user_portal:user_dashboard')

@login_required
def operator_dashboard(request):
    if not request.user.userprofile.is_operator:
        messages.error(request, 'You are not registered as an operator.')
        return redirect('user_portal:user_dashboard')
            
    # Get operator-specific information
    vehicles = Vehicle.objects.filter(operator__user=request.user)
    
    return render(request, 'operators/operator_dashboard.html', {
        'vehicles': vehicles
    })

@login_required
def operator_applications_manage(request):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('user_portal:user_dashboard')
            
    applications = OperatorApplication.objects.all().order_by('-submitted_at')
    
    return render(request, 'operators/operator_applications_manage.html', {
        'applications': applications
    })

@login_required
def operator_application_review(request, application_id):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('user_portal:user_dashboard')
            
    application = get_object_or_404(OperatorApplication, id=application_id)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if status in ['APPROVED', 'REJECTED']:
            application.status = status
            application.notes = notes
            application.processed_at = timezone.now()
            application.processed_by = request.user
            application.save()
            
            # If approved, update user profile
            if status == 'APPROVED':
                user_profile = application.user.userprofile
                user_profile.is_operator = True
                user_profile.operator_since = timezone.now()
                user_profile.save()
                
                # Create notification for user
                notification = UserNotification(
                    user=application.user,
                    message=f"Your operator application has been approved.",
                    type='OPERATOR',
                    reference_id=application.id
                )
                notification.save()
            else:
                # Create notification for rejection
                notification = UserNotification(
                    user=application.user,
                    message=f"Your operator application has been rejected. Reason: {notes}",
                    type='OPERATOR',
                    reference_id=application.id
                )
                notification.save()
            
            messages.success(request, f'Application {status.lower()} successfully.')
            return redirect('operator_applications_manage')
    
    return render(request, 'operators/operator_application_review.html', {
        'application': application
    })

@login_required
def driver_import(request):
    """View to import drivers from an Excel or CSV file - reads the first available worksheet"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to import drivers.")
        return redirect('user_portal:user_dashboard')
    
    if request.method == 'POST':
        form = DriverImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                import pandas as pd
                import io
                import sys
                import re
                
                # Get file from request
                file = request.FILES['file']
                skip_header = form.cleaned_data.get('skip_header', True)
                
                # Check file extension
                if file.name.endswith('.csv'):
                    # Process CSV file
                    try:
                        df = pd.read_csv(file)
                    except Exception as e:
                        # Try reading without headers
                        try:
                            df = pd.read_csv(file, header=None)
                            # Assign default column names
                            df.columns = [f"Column_{i}" for i in range(df.shape[1])]
                        except Exception as e2:
                            messages.error(request, f"Error reading CSV file: {str(e)}")
                            return redirect('driver_import')
                elif file.name.endswith('.xlsx'):
                    # Process Excel file
                    try:
                        # First try reading with headers
                        df = pd.read_excel(file)
                    except Exception as e:
                        try:
                            # Try reading without headers
                            df = pd.read_excel(file, header=None)
                            # Assign default column names
                            df.columns = [f"Column_{i}" for i in range(df.shape[1])]
                        except Exception as e2:
                            messages.error(request, f"Error reading Excel file: {str(e)}")
                            return redirect('driver_import')
                else:
                    messages.error(request, "Unsupported file format. Please upload a CSV or Excel file.")
                    return redirect('driver_import')
                
                # Debug info
                print(f"DataFrame shape: {df.shape}", file=sys.stderr)
                print(f"Column names: {df.columns.tolist()}", file=sys.stderr)
                print(f"First 3 rows:\n{df.head(3)}", file=sys.stderr)
                
                # If first row contains headers and skip_header is True, use the first row as column names
                if skip_header and not df.columns.str.contains('Column_').any():
                    # First row might contain more descriptive headers, show this for debugging
                    first_row = df.iloc[0].tolist()
                    print(f"First row (potential headers): {first_row}", file=sys.stderr)
                    
                    # Check if the first row looks like headers (strings instead of numbers)
                    headers_detected = all([not isinstance(x, (int, float)) or pd.isna(x) for x in first_row])
                    if headers_detected:
                        # Use first row as column names and skip it in the data
                        df.columns = [str(x).strip() if not pd.isna(x) else f"Column_{i}" for i, x in enumerate(first_row)]
                        df = df.iloc[1:]
                        print(f"Using first row as headers. New columns: {df.columns.tolist()}", file=sys.stderr)
                
                # Define additional patterns for better matching
                column_patterns = {
                    'LASTNAME': ['LASTNAME', 'LAST NAME', 'LAST', 'SURNAME', 'FAMILY NAME', 'LN', 'FAMILY', 'SECOND NAME', 'SECOND'],
                    'FIRSTNAME': ['FIRSTNAME', 'FIRST NAME', 'FIRST', 'GIVEN NAME', 'FN', 'GIVEN', 'NAME'],
                    'MI': ['MI', 'M.I.', 'MIDDLE INITIAL', 'MIDDLE', 'MIDDLE NAME', 'M.I', 'INIT', 'INITIAL'],
                    'ADDRESS': ['ADDRESS', 'ADDR', 'LOCATION', 'RESIDENCE', 'HOME ADDRESS', 'LOC', 'RES', 'HOME'],
                    'OLD_PD_NO': ['OLD PD NO', 'OLD P.D. NO.', 'OLD P.D. NO', 'OLD PD', 'PREVIOUS PD', 'OLD ID', 'PREVIOUS ID', 'OLD P.D NO', 'OLD', 'OLD NUMBER', 'PREV', 'PREVIOUS', 'OLD P.O.', 'OLD P.O. NO.', 'OLD P.O'],
                    'NEW_PD_NO': ['NEW PD NO', 'NEW P.D. NO.', 'NEW P.D. NO', 'NEW PD', 'CURRENT PD', 'NEW ID', 'CURRENT ID', 'PD NUMBER', 'ID NUMBER', 'NEW', 'PD NO', 'P.D. NO', 'PD', 'ID', 'NUMBER', 'NO', 'NEW P.O.', 'NEW P.O. NO.', 'NEW P.O']
                }
                
                # Clean column names for better matching
                clean_columns = {}
                for col in df.columns:
                    # Convert to uppercase, remove special characters, and trim whitespace
                    clean_col = re.sub(r'[^A-Z0-9 ]', '', str(col).upper()).strip()
                    clean_columns[col] = clean_col
                    
                print(f"Cleaned column names: {clean_columns}", file=sys.stderr)
                
                # Match each column to the most similar pattern
                column_mapping = {}
                
                # First try exact matches
                for field, patterns in column_patterns.items():
                    for col, clean_col in clean_columns.items():
                        for pattern in patterns:
                            if clean_col == pattern:
                                column_mapping[field] = col
                                break
                
                # If we're missing any fields, try partial matches
                for field in column_patterns:
                    if field not in column_mapping:
                        for col, clean_col in clean_columns.items():
                            # Skip columns already mapped
                            if col in column_mapping.values():
                                continue
                                
                            for pattern in column_patterns[field]:
                                if pattern in clean_col or clean_col in pattern:
                                    column_mapping[field] = col
                                    break
                
                # Last resort: for fields still missing, use positional assumptions
                required_positions = {
                    'LASTNAME': 0,     # First column
                    'FIRSTNAME': 1,    # Second column
                    'MI': 2,           # Third column
                    'ADDRESS': 3,      # Fourth column
                    'OLD_PD_NO': 4,    # Fifth column
                    'NEW_PD_NO': 5     # Sixth column
                }
                
                for field in column_patterns:
                    if field not in column_mapping and field in required_positions:
                        pos = required_positions[field]
                        if pos < len(df.columns):
                            column_mapping[field] = df.columns[pos]
                
                print(f"Detected column mapping: {column_mapping}", file=sys.stderr)
                
                # Check if all required columns are present
                required_columns = ['LASTNAME', 'FIRSTNAME', 'ADDRESS', 'NEW_PD_NO']
                missing_columns = [col for col in required_columns if col not in column_mapping]
                
                if missing_columns:
                    # Print more debug info to help diagnose the issue
                    messages.error(request, f"Could not find columns for: {', '.join(missing_columns)}. Please check your file has columns for these fields.")
                    messages.info(request, f"Available columns in your file: {', '.join(df.columns.tolist())}")
                    return redirect('driver_import')
                
                # Create a new DataFrame with mapped columns
                named_df = pd.DataFrame()
                for field, col in column_mapping.items():
                    named_df[field] = df[col]
                
                # Debug output
                print(f"Named columns: {named_df.columns.tolist()}", file=sys.stderr)
                print(f"First 3 rows after mapping:\n{named_df.head(3)}", file=sys.stderr)
                
                # Process data and validate
                data_to_import = []
                for _, row in named_df.iterrows():
                    # Preserve the exact P.O. numbers from the file
                    old_pd_number = str(row.get('OLD_PD_NO', '')).strip() if pd.notna(row.get('OLD_PD_NO')) else None
                    new_pd_number = str(row.get('NEW_PD_NO', '')).strip() if pd.notna(row.get('NEW_PD_NO')) else None
                    
                    # Debug output for P.O. numbers
                    print(f"Original P.O. numbers - Old: {old_pd_number}, New: {new_pd_number}", file=sys.stderr)
                    
                    if new_pd_number:
                        # Create record
                        driver_data = {
                            'last_name': str(row.get('LASTNAME', '')).strip(),
                            'first_name': str(row.get('FIRSTNAME', '')).strip(),
                            'middle_initial': str(row.get('MI', '')).strip() if pd.notna(row.get('MI')) else '',
                            'address': str(row.get('ADDRESS', '')).strip(),
                            'old_pd_number': old_pd_number,
                            'new_pd_number': new_pd_number,
                            'status': 'new',  # Default status
                            'note': ''
                        }
                        
                        # Debug output for created record
                        print(f"Created driver record: {driver_data}", file=sys.stderr)
                        
                        # Validate the data
                        if not driver_data['last_name'] or not driver_data['first_name'] or not driver_data['address']:
                            driver_data['status'] = 'error'
                            driver_data['note'] = 'Missing required fields'
                        else:
                            # Check if this driver already exists with the exact same P.O. number
                            try:
                                Driver.objects.get(new_pd_number=new_pd_number)
                                driver_data['status'] = 'update'
                                driver_data['note'] = 'Driver exists, will be updated'
                            except Driver.DoesNotExist:
                                # Find if there's a matching operator for this driver
                                try:
                                    matching_operator = Operator.objects.filter(
                                        last_name__iexact=driver_data['last_name'],
                                        first_name__iexact=driver_data['first_name'],
                                        address__iexact=driver_data['address']
                                    ).first()
                                    
                                    if matching_operator:
                                        driver_data['note'] = f'Will be linked to operator: {matching_operator.new_pd_number}'
                                except Exception:
                                    pass
                        
                        data_to_import.append(driver_data)
                
                if not data_to_import:
                    messages.error(request, "No valid driver data found in the file.")
                    return redirect('driver_import')
                
                # Store the data in the session for confirmation
                request.session['driver_import_data'] = data_to_import
                
                # Proceed to confirmation page
                return redirect('driver_import_confirm')
                
            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
                logger.exception("Error in driver import")
                import traceback
                print(traceback.format_exc(), file=sys.stderr)
                return redirect('driver_import')
    else:
        form = DriverImportForm()
    
    return render(request, 'drivers/driver_import.html', {
        'form': form
    })

@login_required
def driver_list(request):
    """View to display a list of all drivers with search and pagination"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to view the list of drivers.")
        return redirect('user_portal:user_dashboard')
    
    # Get search query
    search_query = request.GET.get('search', '')
    
    # Get all drivers ordered by last name, first name
    drivers = Driver.objects.all().order_by('last_name', 'first_name')
    
    # Apply search filter if provided
    if search_query:
        drivers = drivers.filter(
            Q(last_name__icontains=search_query) | 
            Q(first_name__icontains=search_query) |
            Q(new_pd_number__icontains=search_query) |
            Q(old_pd_number__icontains=search_query)
        )
    
    # Pagination - 20 drivers per page
    paginator = Paginator(drivers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'drivers/driver_list.html', {
        'drivers': page_obj,
        'search_query': search_query,
    })

@login_required
def driver_create(request):
    """View to create a new driver record"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to create driver records.")
        return redirect('user_portal:user_dashboard')
    
    if request.method == 'POST':
        form = DriverForm(request.POST)
        if form.is_valid():
            driver = form.save()
            
            # Log the activity
            ActivityLog.objects.create(
                user=request.user,
                action=f"Created driver record for {driver.first_name} {driver.last_name}",
                timestamp=timezone.now()
            )
            
            messages.success(request, f"Driver {driver.first_name} {driver.last_name} created successfully.")
            return redirect('driver_list')
    else:
        form = DriverForm()
    
    return render(request, 'drivers/driver_form.html', {
        'form': form,
        'title': 'Create Driver',
        'is_create': True
    })

@login_required
def driver_update(request, pk):
    """View to update an existing driver record"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to update driver records.")
        return redirect('user_portal:user_dashboard')
    
    try:
        driver = Driver.objects.get(pk=pk)
    except Driver.DoesNotExist:
        messages.error(request, "Driver not found.")
        return redirect('driver_list')
    
    if request.method == 'POST':
        form = DriverForm(request.POST, instance=driver)
        if form.is_valid():
            updated_driver = form.save()
            
            # Log the activity
            ActivityLog.objects.create(
                user=request.user,
                action=f"Updated driver: {updated_driver.first_name} {updated_driver.last_name} ({updated_driver.new_pd_number})",
                timestamp=timezone.now()
            )
            
            messages.success(request, f"Driver {updated_driver.first_name} {updated_driver.last_name} updated successfully.")
            return redirect('driver_list')
    else:
        form = DriverForm(instance=driver)
    
    return render(request, 'drivers/driver_form.html', {
        'form': form,
        'title': f'Update Driver: {driver.last_name}, {driver.first_name}',
        'submit_text': 'Update',
        'is_create': False
    })

@login_required
def driver_delete(request, pk):
    """View to delete an existing driver"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to delete drivers.")
        return redirect('user_portal:user_dashboard')
    
    driver = get_object_or_404(Driver, pk=pk)
    
    if request.method == 'POST':
        # Log the driver details before deletion
        driver_details = f"{driver.first_name} {driver.last_name} ({driver.new_pd_number})"
        
        # Delete the driver
        driver.delete()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action=f"Deleted driver: {driver_details}",
            timestamp=timezone.now()
        )
        
        messages.success(request, f"Driver {driver_details} deleted successfully.")
        return redirect('driver_list')
    
    return render(request, 'drivers/driver_confirm_delete.html', {
        'driver': driver
    })

@login_required
def driver_import_confirm(request):
    """View to confirm the import of drivers from Excel/CSV file"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('user_portal:user_dashboard')
        
    # Get the data from the session
    driver_data = request.session.get('driver_import_data', [])
    
    if not driver_data:
        messages.error(request, "No driver data to import. Please upload a file first.")
        return redirect('driver_import')
    
    # Calculate counts
    new_count = 0
    update_count = 0
    error_count = 0
    
    for item in driver_data:
        if item['status'] == 'error':
            error_count += 1
        elif item['status'] == 'update':
            update_count += 1
        else:
            new_count += 1
    
    if request.method == 'POST':
        # Process the data
        imported_count = 0
        updated_count = 0
        error_count = 0
        error_messages = []
        
        print(f"Processing {len(driver_data)} driver records for import", file=sys.stderr)
        
        for index, item in enumerate(driver_data):
            try:
                # Skip items already marked with errors
                if item['status'] == 'error':
                    error_count += 1
                    error_messages.append(f"Row {index+1}: {item['note']}")
                    print(f"Skipping row {index+1} - {item['note']}", file=sys.stderr)
                    continue
                
                # Print the item being processed for debugging
                print(f"Processing row {index+1}: {item}", file=sys.stderr)
                
                # Try to find a matching operator
                matching_operator = None
                try:
                    matching_operator = Operator.objects.filter(
                        last_name__iexact=item['last_name'],
                        first_name__iexact=item['first_name'],
                        address__iexact=item['address']
                    ).first()
                    
                    if matching_operator:
                        print(f"Found matching operator: {matching_operator}", file=sys.stderr)
                except Exception as e:
                    print(f"Error finding matching operator: {str(e)}", file=sys.stderr)
                
                # Use the PD number exactly as entered in the file - keep it as a plain number
                new_pd_number = item['new_pd_number']
                old_pd_number = item['old_pd_number']
                print(f"Using PD numbers as-is - Old: {old_pd_number}, New: {new_pd_number}", file=sys.stderr)
                
                # Check if driver with this PD number already exists
                try:
                    driver = Driver.objects.get(new_pd_number=new_pd_number)
                    # Update existing driver
                    print(f"Updating existing driver: {driver}", file=sys.stderr)
                    driver.last_name = item['last_name']
                    driver.first_name = item['first_name']
                    driver.middle_initial = item['middle_initial']
                    driver.address = item['address']
                    if item['old_pd_number']:
                        driver.old_pd_number = item['old_pd_number']
                    if matching_operator:
                        driver.operator = matching_operator
                    
                    # Set necessary fields directly using setattr to handle db schema changes
                    try:
                        # Set is_also_operator field (default False)
                        setattr(driver, 'is_also_operator', matching_operator is not None)
                    except Exception as e:
                        print(f"Warning: Couldn't set is_also_operator field: {str(e)}", file=sys.stderr)
                    
                    driver.save()
                    updated_count += 1
                except Driver.DoesNotExist:
                    # Create new driver - use raw SQL to handle missing model fields
                    print(f"Creating new driver with PD number: {new_pd_number}", file=sys.stderr)
                    
                    try:
                        # First attempt to create using the model
                        driver = Driver(
                            last_name=item['last_name'],
                            first_name=item['first_name'],
                            middle_initial=item['middle_initial'],
                            address=item['address'],
                            old_pd_number=item['old_pd_number'],
                            new_pd_number=new_pd_number,
                            operator=matching_operator
                        )
                        
                        # Set is_also_operator field
                        setattr(driver, 'is_also_operator', matching_operator is not None)
                        
                        # Save the driver
                        driver.save()
                        imported_count += 1
                    except Exception as e:
                        # If model approach fails, try direct SQL
                        print(f"Falling back to raw SQL: {str(e)}", file=sys.stderr)
                        
                        from django.db import connection
                        with connection.cursor() as cursor:
                            cursor.execute(
                                """
                                INSERT INTO traffic_violation_system_driver
                                (last_name, first_name, middle_initial, address, old_pd_number, new_pd_number, 
                                is_also_operator, operator_id, created_at, updated_at, vehicle_id)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                [
                                    item['last_name'],
                                    item['first_name'],
                                    item['middle_initial'] or '',
                                    item['address'],
                                    item['old_pd_number'] or '',
                                    new_pd_number,
                                    1 if matching_operator else 0,  # is_also_operator
                                    matching_operator.id if matching_operator else None,  # operator_id
                                    timezone.now(),  # created_at
                                    timezone.now(),  # updated_at
                                    None,  # vehicle_id
                                ]
                            )
                        imported_count += 1
            except Exception as e:
                error_count += 1
                error_detail = f"Row {index+1} ({item.get('last_name', 'Unknown')}, {item.get('first_name', 'Unknown')}): {str(e)}"
                error_messages.append(error_detail)
                print(f"Error importing driver: {error_detail}", file=sys.stderr)
                logger.error(f"Error importing driver {item.get('new_pd_number', 'Unknown')}: {str(e)}")
                import traceback
                print(traceback.format_exc(), file=sys.stderr)
        
        # Clear the session data
        if 'driver_import_data' in request.session:
            del request.session['driver_import_data']
        
        # Create activity log entry
        ActivityLog.objects.create(
            user=request.user,
            action=f"Imported {imported_count} new drivers, updated {updated_count} existing drivers",
            timestamp=timezone.now()
        )
        
        # Show success message
        if error_count > 0:
            messages.warning(request, f"Imported {imported_count} drivers, updated {updated_count} drivers, with {error_count} errors. Check the logs for details.")
            # Show first 5 errors in the UI
            if error_messages:
                top_errors = error_messages[:5]
                messages.error(request, f"Sample errors: {'; '.join(top_errors)}" + (" and more..." if len(error_messages) > 5 else ""))
        else:
            messages.success(request, f"Successfully imported {imported_count} new drivers and updated {updated_count} existing drivers.")
        
        return redirect('driver_list')
    
    # Render the confirmation template
    return render(request, 'drivers/driver_import_confirm.html', {
        'driver_data': driver_data,
        'new_count': new_count,
        'update_count': update_count,
        'error_count': error_count,
        'total_count': len(driver_data)
    })

@login_required
def driver_export_excel(request):
    """View to export drivers as Excel file"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to export drivers.")
        return redirect('user_portal:user_dashboard')
    
    try:
        import pandas as pd
        from io import BytesIO
        
        # Get all drivers ordered by last name, first name
        drivers = Driver.objects.all().order_by('last_name', 'first_name')
        
        # Create data for Excel file
        data = []
        for driver in drivers:
            data.append({
                'LASTNAME': driver.last_name,
                'FIRST NAME': driver.first_name,
                'M.I.': driver.middle_initial,
                'ADDRESS': driver.address,
                'OLD P.D NO.': driver.old_pd_number or '',
                'NEW P.D NO.': driver.new_pd_number,
                'OPERATOR': driver.operator.new_pd_number if driver.operator else ''
            })
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Create Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Write drivers data
            df.to_excel(writer, sheet_name='Drivers', index=False)
            
            # Create a template sheet for import
            template_df = pd.DataFrame(columns=[
                'LASTNAME', 'FIRST NAME', 'M.I.', 'ADDRESS', 'OLD P.D NO.', 'NEW P.D NO.'
            ])
            template_df.to_excel(writer, sheet_name='Template', index=False)
        
        # Prepare response
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=drivers.xlsx'
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action=f"Exported drivers to Excel",
            timestamp=timezone.now()
        )
        
        return response
    except Exception as e:
        messages.error(request, f"Error exporting drivers: {str(e)}")
        logger.error(f"Error exporting drivers: {str(e)}")
        return redirect('driver_list')

@login_required
def admin_reports_dashboard(request):
    # Check if user is admin
    if request.user.userprofile.role != 'ADMIN':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('admin_dashboard')
    
    # Get filters from request
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    user_id = request.GET.get('user_id', '')
    violation_type = request.GET.get('type', '')
    
    # Get all reports
    reports = UserReport.objects.all().select_related('user', 'assigned_to')
    
    # Apply filters if provided
    if status_filter:
        reports = reports.filter(status=status_filter)
    
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            reports = reports.filter(created_at__gte=date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            # Add a day to include the end date fully
            date_to = date_to + timedelta(days=1)
            reports = reports.filter(created_at__lt=date_to)
        except ValueError:
            pass
    
    if user_id:
        reports = reports.filter(user_id=user_id)
    
    if violation_type:
        reports = reports.filter(type=violation_type)
    
    # Calculate statistics for summary cards
    total_reports = UserReport.objects.count()
    pending_reports = UserReport.objects.filter(status='PENDING').count()
    in_progress_reports = UserReport.objects.filter(status='IN_PROGRESS').count()
    resolved_reports = UserReport.objects.filter(status='RESOLVED').count()
    closed_reports = UserReport.objects.filter(status='CLOSED').count()
    
    context = {
        'reports': reports,
        'total_reports': total_reports,
        'pending_reports': pending_reports,
        'in_progress_reports': in_progress_reports,
        'resolved_reports': resolved_reports,
        'closed_reports': closed_reports,
        'report_types': UserReport.REPORT_TYPES,
        'status_choices': UserReport.STATUS_CHOICES,
        'selected_status': status_filter,
        'selected_type': violation_type,
        'date_from': date_from if isinstance(date_from, str) else date_from.strftime('%Y-%m-%d') if date_from else '',
        'date_to': date_to if isinstance(date_to, str) else (date_to - timedelta(days=1)).strftime('%Y-%m-%d') if date_to else '',
        'user_id': user_id
    }
    
    return render(request, 'admin/reports_dashboard.html', context)


@login_required
def update_report(request, report_id):
    # Check if user is admin
    if request.user.userprofile.role != 'ADMIN':
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    # Only allow POST requests
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    
    try:
        report = UserReport.objects.get(id=report_id)
    except UserReport.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Report not found'}, status=404)
    
    # Get data from request
    status = request.POST.get('status')
    notes = request.POST.get('notes', '')
    notify_user = request.POST.get('notify_user') == 'true'
    
    # Validate status
    if status not in [s[0] for s in UserReport.STATUS_CHOICES]:
        return JsonResponse({'status': 'error', 'message': 'Invalid status'}, status=400)
    
    # Update report
    old_status = report.status
    report.status = status
    
    # Add notes if provided
    if notes:
        if report.resolution_notes:
            report.resolution_notes += f"\n\n{timezone.now().strftime('%Y-%m-%d %H:%M')} - {request.user.get_full_name()}:\n{notes}"
        else:
            report.resolution_notes = f"{timezone.now().strftime('%Y-%m-%d %H:%M')} - {request.user.get_full_name()}:\n{notes}"
    
    # If status is resolved or closed, add resolution timestamp
    if status in ['RESOLVED', 'CLOSED'] and not report.resolved_at:
        report.resolved_at = timezone.now()
    
    # Assign to current user if status is changed to in progress
    if status == 'IN_PROGRESS' and old_status != 'IN_PROGRESS':
        report.assigned_to = request.user
    
    report.save()
    
    # Create notification for user if requested
    if notify_user:
        status_display = dict(UserReport.STATUS_CHOICES)[status]
        message = f'Your report "{report.subject}" has been updated to {status_display}.'
        if notes:
            message += f' Admin notes: {notes}'
        
        UserNotification.objects.create(
            user=report.user,
            type='SYSTEM',
            message=message
        )
    
    # Log the activity
    ActivityLog.objects.create(
        user=request.user,
        action=f'Updated report #{report.id} status from {old_status} to {status}',
        object_id=report.id,
        object_type='UserReport'
    )
    
    return JsonResponse({
        'status': 'success',
        'message': 'Report updated successfully',
        'report': {
            'id': report.id,
            'status': status,
            'status_display': dict(UserReport.STATUS_CHOICES)[status],
            'assigned_to': report.assigned_to.get_full_name() if report.assigned_to else None,
            'resolution_notes': report.resolution_notes,
            'resolved_at': report.resolved_at.strftime('%Y-%m-%d %H:%M') if report.resolved_at else None
        }
    })


@login_required
def get_report_details(request, report_id):
    # Check if user is admin
    if request.user.userprofile.role != 'ADMIN':
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    try:
        report = UserReport.objects.select_related('user', 'assigned_to', 'user__userprofile').get(id=report_id)
    except UserReport.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Report not found'}, status=404)
    
    # Format the user and report details for JSON response
    user_profile = report.user.userprofile
    
    # Build report data
    report_data = {
        'id': report.id,
        'user': {
            'id': report.user.id,
            'full_name': report.user.get_full_name(),
            'username': report.user.username,
            'email': report.user.email,
            'license_number': user_profile.license_number,
            'phone_number': user_profile.phone_number,
            'avatar_url': user_profile.avatar.url if user_profile.avatar else None
        },
        'type': report.type,
        'type_display': report.get_type_display(),
        'subject': report.subject,
        'description': report.description,
        'location': report.location,
        'incident_date': report.incident_date.strftime('%Y-%m-%d %H:%M') if report.incident_date else None,
        'status': report.status,
        'status_display': report.get_status_display(),
        'created_at': report.created_at.strftime('%Y-%m-%d %H:%M'),
        'updated_at': report.updated_at.strftime('%Y-%m-%d %H:%M'),
        'assigned_to': report.assigned_to.get_full_name() if report.assigned_to else None,
        'resolution_notes': report.resolution_notes,
        'resolved_at': report.resolved_at.strftime('%Y-%m-%d %H:%M') if report.resolved_at else None
    }
    
    # Add attachment info if present
    if report.attachment:
        report_data['attachment'] = {
            'url': report.attachment.url,
            'filename': report.attachment.name.split('/')[-1]
        }
    else:
        report_data['attachment'] = None
    
    return JsonResponse({
        'status': 'success',
        'report': report_data
    })