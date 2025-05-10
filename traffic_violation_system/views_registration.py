from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.utils import timezone
import logging
from django.urls import reverse
from django.contrib.auth import authenticate, login
from django.db.models import Q

from .models import UserProfile, EmailVerificationToken, Violation, ViolatorQRHash
from .utils.email_utils import send_verification_email
from .utils import log_activity
import uuid

# Configure logger
logger = logging.getLogger(__name__)

def register(request):
    """User registration view with email verification"""
    logger.info("Register view called with method: %s", request.method)
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
            
            # Check for duplicate license only if license_number is not empty
            if license_number and UserProfile.objects.filter(license_number=license_number).exists():
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
            profile.is_email_verified = False  # Email not verified yet
            profile.save()

            # Handle avatar upload
            if 'avatar' in request.FILES:
                profile.avatar = request.FILES['avatar']
                profile.save()
            
            # Check if violations were confirmed and should be linked
            violations_confirmed = request.POST.get('violations_confirmed', 'false').lower() == 'true'
            
            # If violations were confirmed, link them to the user
            if violations_confirmed:
                logger.info(f"Linking violations to newly registered user: {username}")
                
                # Check if specific violation IDs were provided
                violation_ids_str = request.POST.get('violation_ids', '')
                if violation_ids_str:
                    # Parse comma-separated violation IDs
                    try:
                        violation_ids = [int(vid.strip()) for vid in violation_ids_str.split(',') if vid.strip().isdigit()]
                        logger.info(f"Specific violation IDs provided: {violation_ids}")
                        
                        # Link the specific violations
                        violation_count = 0
                        for vid in violation_ids:
                            try:
                                violation = Violation.objects.get(id=vid, user_account__isnull=True)
                                with transaction.atomic():
                                    violation.user_account = user
                                    violation.save()
                                    violation_count += 1
                                    logger.info(f"Linked specific violation ID {vid} to user {username}")
                                    
                                    # Log activity
                                    log_activity(
                                        user=user, 
                                        action_type='VIOLATION_LINKED',
                                        description=f"Violation #{violation.id} automatically linked to user account during registration",
                                        object_id=violation.id, 
                                        object_type='Violation'
                                    )
                            except Violation.DoesNotExist:
                                logger.warning(f"Violation ID {vid} not found or already claimed")
                            except Exception as e:
                                logger.error(f"Error linking violation ID {vid} to user {username}: {str(e)}")
                        
                        if violation_count > 0:
                            messages.info(request, f"Successfully linked {violation_count} existing violations to your account.")
                        
                    except Exception as e:
                        logger.error(f"Error parsing violation IDs {violation_ids_str}: {str(e)}")
                        # Fall through to the general violation search below
                
                # If no specific violations were linked, fall back to searching by user information
                else:
                    # Find violations that match this user's information and are not claimed
                    first_name = request.POST['first_name']
                    last_name = request.POST['last_name']
                    
                    matching_violations = Violation.objects.filter(
                        user_account__isnull=True,
                        status__in=['PENDING', 'ADJUDICATED', 'APPROVED', 'OVERDUE']
                    )
                    
                    # Build the query for finding matching violations
                    query_filter = None
                    
                    # Match by license number if provided
                    if license_number:
                        query_filter = Q(violator__license_number__iexact=license_number)
                    
                    # Match by name
                    name_filter = Q(violator__first_name__iexact=first_name) & Q(violator__last_name__iexact=last_name)
                    
                    # Combine filters
                    if query_filter:
                        query_filter |= name_filter
                    else:
                        query_filter = name_filter
                    
                    # Apply filter
                    matching_violations = matching_violations.filter(query_filter)
                    
                    # Link each violation to the user
                    violation_count = 0
                    for violation in matching_violations:
                        try:
                            with transaction.atomic():
                                violation.user_account = user
                                violation.save()
                                violation_count += 1
                                logger.info(f"Linked violation ID {violation.id} to user {username}")
                                
                                # Log activity
                                log_activity(
                                    user=user, 
                                    action_type='VIOLATION_LINKED',
                                    description=f"Violation #{violation.id} automatically linked to user account during registration",
                                    object_id=violation.id, 
                                    object_type='Violation'
                                )
                        except Exception as e:
                            logger.error(f"Error linking violation to user {username}: {str(e)}")
                            
                    if violation_count > 0:
                        messages.info(request, f"Successfully linked {violation_count} existing violations to your account.")
            
            # Create verification token
            token = EmailVerificationToken.objects.create(
                user=user,
                expires_at=timezone.now() + timezone.timedelta(hours=24)
            )
            
            # Send verification email
            email_sent = send_verification_email(user, token, request)
            
            if email_sent:
                messages.success(request, 'Registration successful! Please check your email to verify your account.')
            else:
                messages.warning(request, 'Registration successful, but we could not send a verification email. Please request a new one from the verification page.')
            
            # Store the email in session for verification_pending page
            request.session['registration_email'] = email
            
            # Log the redirection target
            logger.info("Redirecting to verification_pending page after successful registration for email: %s", email)
            
            # Add a more robust redirect
            try:
                verification_url = reverse('verification_pending')
                logger.info("Generated verification_pending URL: %s", verification_url)
                
                # Redirect to verification pending page and return immediately
                response = redirect('verification_pending')
                # Set cache control headers to prevent caching
                response['Cache-Control'] = 'no-store, must-revalidate'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
                
                logger.info("Created redirect response to verification_pending")
                return response
            except Exception as e:
                logger.exception("Error during redirect to verification_pending: %s", str(e))
                # Fallback to direct redirect
                return redirect('verification_pending')

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
            logger.exception("Registration failed with exception: %s", str(e))
            messages.error(request, f'Registration failed: {str(e)}')
            return render(request, 'registration/register.html', {'form_data': request.POST})

    logger.info("Rendering registration form template (GET request)")
    return render(request, 'registration/register.html')

def register_with_violations(request, hash_id):
    """
    Registration view specifically for users who received a violation ticket with QR code.
    This links the violations to their new account automatically upon registration.
    """
    # Get the ViolatorQRHash or return 404
    qr_hash = get_object_or_404(ViolatorQRHash, hash_id=hash_id)
    
    # Check if the hash is expired
    if qr_hash.expires_at and qr_hash.expires_at < timezone.now():
        messages.error(request, "This registration link has expired. Please contact support.")
        return redirect('login')
    
    # Check if already registered
    if qr_hash.registered and qr_hash.user_account:
        messages.info(request, "You have already registered. Please log in.")
        return redirect('login')
    
    # Get all associated violations
    violations = qr_hash.get_violations()
    
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        first_name = qr_hash.first_name  # Use from QR hash
        last_name = qr_hash.last_name    # Use from QR hash
        license_number = qr_hash.license_number  # Use from QR hash if available
        phone_number = qr_hash.phone_number  # Use from QR hash if available
        
        # Manual override if provided
        if request.POST.get('first_name'):
            first_name = request.POST.get('first_name')
        if request.POST.get('last_name'):
            last_name = request.POST.get('last_name')
        if request.POST.get('license_number'):
            license_number = request.POST.get('license_number')
        if request.POST.get('phone_number'):
            phone_number = request.POST.get('phone_number')
        
        # Validate form data
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, 'registration/register_with_violations.html', {
                'qr_hash': qr_hash,
                'violations': violations,
            })
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return render(request, 'registration/register_with_violations.html', {
                'qr_hash': qr_hash,
                'violations': violations,
            })
        
        if license_number and UserProfile.objects.filter(license_number=license_number).exists():
            messages.error(request, "License number is already registered.")
            return render(request, 'registration/register_with_violations.html', {
                'qr_hash': qr_hash,
                'violations': violations,
            })
        
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'registration/register_with_violations.html', {
                'qr_hash': qr_hash,
                'violations': violations,
            })
        
        try:
            with transaction.atomic():
                # Create user account
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )
                
                # Create user profile
                profile = UserProfile.objects.create(
                    user=user,
                    license_number=license_number,
                    phone_number=phone_number,
                    role='DRIVER'  # Default role for violators
                )
                
                # Update QR hash to mark as registered
                qr_hash.registered = True
                qr_hash.user_account = user
                qr_hash.save()
                
                # Link all violations to the new user
                for violation in violations:
                    violation.user = user
                    violation.save()
                    
                    # Create notification for each violation
                    Notification.objects.create(
                        user=user,
                        title=f"Violation Ticket #{violation.id}",
                        message=f"A violation ticket has been linked to your account: {violation.violation_type} on {violation.date_of_violation}",
                        is_read=False,
                    )
                
                # Log the registration
                log_activity(
                    user=user,
                    action="REGISTRATION",
                    details=f"Registered through QR code with {len(violations)} linked violations"
                )
                
                # Log in the user
                login(request, user)
                
                messages.success(request, "Registration successful! Your violations have been linked to your account.")
                return redirect('driver_dashboard')  # Redirect to driver dashboard
                
        except Exception as e:
            messages.error(request, f"Registration failed: {str(e)}")
    
    # GET request - show registration form
    return render(request, 'registration/register_with_violations.html', {
        'qr_hash': qr_hash,
        'violations': violations,
    }) 