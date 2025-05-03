from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseBadRequest
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
import logging

from .models import User, UserProfile, EmailVerificationToken
from .utils.email_utils import send_verification_email, send_verification_reminder

logger = logging.getLogger(__name__)


def verify_code(request):
    """
    Verify user's email address using the verification code from the email.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid request method')
    
    verification_code = request.POST.get('verification_code')
    email = request.POST.get('email')
    
    if not verification_code or not email:
        messages.error(request, 'Both verification code and email are required')
        return redirect('verification_pending')
    
    try:
        # Find the user by email
        user = User.objects.get(email=email)
        
        # Find the token with matching verification code
        try:
            # Get the most recent token for this user with the given code
            verification_token = EmailVerificationToken.objects.filter(
                user=user,
                verification_code=verification_code
            ).order_by('-created_at').first()
            
            if not verification_token:
                logger.warning(f"Invalid verification code for user {email}")
                messages.error(request, 'Invalid verification code. Please check and try again.')
                return redirect('verification_pending')
                
            # Check if token is expired
            if not verification_token.is_valid():
                # Create a new token for the user
                new_token = EmailVerificationToken.objects.create(user=user)
                
                # Send a new verification email
                send_verification_email(user, new_token, request)
                
                # Delete expired token
                verification_token.delete()
                
                messages.warning(request, 'Your verification code has expired. We have sent a new verification code to your email address.')
                return redirect('verification_pending')
            
            # Mark the user as verified
            profile = UserProfile.objects.get(user=user)
            profile.is_email_verified = True
            profile.save()
            
            # Delete all verification tokens for this user
            EmailVerificationToken.objects.filter(user=user).delete()
            
            # Show success message
            messages.success(request, 'Your email has been successfully verified! You can now log in to your account.')
            return redirect('verification_success')
            
        except Exception as e:
            logger.exception(f"Error verifying code: {str(e)}")
            messages.error(request, 'Error verifying your email. Please try again.')
            return redirect('verification_pending')
            
    except User.DoesNotExist:
        messages.error(request, 'No account found with that email address')
        return redirect('verification_pending')


def verify_email(request, token):
    """
    Legacy email verification function for existing email verification links.
    """
    try:
        # Find the token in the database
        verification_token = get_object_or_404(EmailVerificationToken, token=token)
        user = verification_token.user
        
        # Check if token is expired
        if not verification_token.is_valid():
            # Create a new token for the user
            new_token = EmailVerificationToken.objects.create(user=user)
            
            # Send a new verification email
            send_verification_email(user, new_token, request)
            
            # Delete expired token
            verification_token.delete()
            
            messages.warning(request, 'Your verification link has expired. We have sent a new verification code to your email address.')
            return redirect('verification_pending')
        
        # Mark the user as verified
        profile = UserProfile.objects.get(user=user)
        profile.is_email_verified = True
        profile.save()
        
        # Delete the verification token
        verification_token.delete()
        
        # Show success message
        messages.success(request, 'Your email has been successfully verified! You can now log in to your account.')
        return redirect('verification_success')
        
    except Exception as e:
        logger.exception(f"Error verifying email: {str(e)}")
        messages.error(request, f'Error verifying email: {str(e)}')
        return redirect('verification_failed')


def verification_pending(request):
    """
    Show verification pending page where users can request a new verification email.
    """
    context = {}
    
    # Check for email in session from registration
    registration_email = request.session.get('registration_email')
    if registration_email:
        context['user_email'] = registration_email
    # If not in session, try to get from authenticated user
    elif request.user.is_authenticated:
        context['user_email'] = request.user.email
    
    return render(request, 'registration/verification_pending.html', context)


def verification_required(request):
    """
    Show verification required page for users who haven't verified their email.
    """
    context = {}
    if request.user.is_authenticated:
        context['user_email'] = request.user.email
    return render(request, 'registration/verification_required.html', context)


def verification_success(request):
    """
    Show verification success page after successful email verification.
    """
    return render(request, 'registration/verification_success.html')


def verification_failed(request):
    """
    Show verification failed page if email verification failed.
    """
    return render(request, 'registration/verification_failed.html')


def verification_expired(request):
    """
    Show verification expired page if email verification token expired.
    """
    return render(request, 'registration/verification_expired.html')


def resend_verification(request):
    """
    Resend verification email to the user.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid request method')
    
    email = request.POST.get('email')
    if not email:
        messages.error(request, 'Email address is required')
        return redirect('verification_pending')
    
    try:
        user = User.objects.get(email=email)
        
        # Check if user is already verified
        profile = UserProfile.objects.get(user=user)
        if profile.is_email_verified:
            messages.info(request, 'Your email is already verified. You can log in to your account.')
            return redirect('login')
        
        # Delete any existing tokens for this user
        EmailVerificationToken.objects.filter(user=user).delete()
        
        # Create a new token and send verification email
        token = EmailVerificationToken.objects.create(user=user)
        
        email_sent = send_verification_email(user, token, request)
        
        if email_sent:
            messages.success(request, 'A new verification code has been sent to your email address.')
            # Store the email in session
            request.session['registration_email'] = email
        else:
            logger.error(f"Failed to send verification email to {email} due to server-side email issues.")
            messages.error(request, 'Failed to send verification email due to server-side issues. Our team has been notified. Please try again later or contact support if the problem persists.')
        
        return redirect('verification_pending')
    
    except User.DoesNotExist:
        messages.error(request, 'No account found with that email address')
        return redirect('verification_pending')
    
    except Exception as e:
        logger.exception(f"Unexpected error resending verification email to {email}: {str(e)}")
        messages.error(request, f'An unexpected error occurred. Please try again later.')
        return redirect('verification_pending') 