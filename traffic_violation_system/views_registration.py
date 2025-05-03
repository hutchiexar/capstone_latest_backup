from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.utils import timezone
import logging
from django.urls import reverse

from .models import UserProfile, EmailVerificationToken
from .utils.email_utils import send_verification_email

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