from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.utils import timezone

from .models import UserProfile, EmailVerificationToken
from .utils.email_utils import send_verification_email

def register(request):
    """User registration view with email verification"""
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
            
            # Redirect to verification pending page
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
            messages.error(request, f'Registration failed: {str(e)}')
            return render(request, 'registration/register.html', {'form_data': request.POST})

    return render(request, 'registration/register.html') 