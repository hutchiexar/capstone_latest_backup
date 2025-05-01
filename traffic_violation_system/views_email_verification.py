from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseBadRequest
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.urls import reverse
from django.conf import settings

from .models import User, UserProfile, EmailVerificationToken
from .utils.email_utils import send_verification_email, send_verification_reminder


def verify_email(request, token):
    """
    Verify user's email address using the token from the verification link.
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
            
            messages.warning(request, 'Your verification link has expired. We have sent a new verification email to your address.')
            return render(request, 'registration/verification_expired.html', {'user': user})
        
        # Mark the user as verified
        profile = UserProfile.objects.get(user=user)
        profile.is_email_verified = True
        profile.save()
        
        # Delete the verification token
        verification_token.delete()
        
        # Show success message
        messages.success(request, 'Your email has been successfully verified! You can now log in to your account.')
        return render(request, 'registration/verification_success.html', {'user': user})
        
    except Exception as e:
        messages.error(request, f'Error verifying email: {str(e)}')
        return render(request, 'registration/verification_failed.html')


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
            messages.success(request, 'A new verification email has been sent to your address.')
        else:
            messages.error(request, 'Failed to send verification email. Please try again later.')
        
        return redirect('verification_pending')
    
    except User.DoesNotExist:
        messages.error(request, 'No account found with that email address')
        return redirect('verification_pending')
    
    except Exception as e:
        messages.error(request, f'Error resending verification email: {str(e)}')
        return redirect('verification_pending')


def verification_pending(request):
    """
    Show verification pending page where users can request a new verification email.
    """
    return render(request, 'registration/verification_pending.html')


def verification_required(request):
    """
    Inform users that they need to verify their email to access certain features.
    """
    return render(request, 'registration/verification_required.html') 