from django.shortcuts import redirect
from django.urls import reverse, resolve
from django.contrib import messages
from django.conf import settings

import re
from .models import UserProfile

class AuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add basic cache control headers for all responses
        response['Cache-Control'] = 'no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        # Add X-Frame-Options header
        response['X-Frame-Options'] = 'SAMEORIGIN'
        
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # List of URLs that don't require authentication
        exempt_urls = [
            reverse('login'),
            reverse('landing_home'),
            reverse('about'),
            reverse('services'),
            reverse('contact'),
            reverse('register'),
            reverse('track_violation'),
        ]
        
        # Allow access to landing pages, static files, and media files
        if (request.path in exempt_urls or 
            request.path.startswith('/static/') or 
            request.path.startswith('/media/')):
            return None

        # Require authentication for all other pages
        if not request.user.is_authenticated:
            # Store the next URL in the session for redirect after login
            next_url = request.get_full_path()
            request.session['next'] = next_url
            return redirect('login')
        return None

class NoCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add cache control headers for authenticated users
        if request.user.is_authenticated:
            response['Cache-Control'] = 'private, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response

class EnforcerLocationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_authenticated:
            return None

        # Check if user is an enforcer
        try:
            profile = UserProfile.objects.get(user=request.user)
            if profile.role != 'ENFORCER' or not hasattr(profile, 'is_active_duty'):
                return None
            
            # Skip for API endpoints and certain views
            url_name = resolve(request.path_info).url_name
            if url_name in ['update_location', 'login', 'logout', 'profile', 'edit_profile'] or request.path.startswith('/api/'):
                return None
            
            # If enforcer is not on active duty, redirect to a notification page
            if not profile.is_active_duty:
                if url_name != 'inactive_duty_notification':
                    messages.warning(request, 'You need to be on active duty to access this feature.')
                    return redirect('inactive_duty_notification')
                
        except UserProfile.DoesNotExist:
            return None
        
        return None

class EmailVerificationMiddleware:
    """Middleware to check if a user has verified their email for protected views."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Paths that don't require email verification
        self.exempt_urls = [
            r'^/login/$',
            r'^/logout/$',
            r'^/register/$',
            r'^/verification/',  # All verification-related URLs
            r'^/static/',
            r'^/media/',
            r'^/admin/',
            r'^/api/',
        ]
        
        # Try to add any additional exempt paths from settings
        if hasattr(settings, 'EMAIL_VERIFICATION_EXEMPT_URLS'):
            self.exempt_urls.extend(settings.EMAIL_VERIFICATION_EXEMPT_URLS)
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip middleware if settings flag is disabled
        if not getattr(settings, 'EMAIL_VERIFICATION_REQUIRED', True):
            return None
            
        # Skip for non-authenticated users
        if not request.user.is_authenticated:
            return None
        
        # Check if the current path is exempt
        path = request.path_info
        if any(re.match(url, path) for url in self.exempt_urls):
            return None
        
        # Staff and superusers bypass verification
        if request.user.is_staff or request.user.is_superuser:
            return None
        
        # Check if user has verified their email
        try:
            profile = UserProfile.objects.get(user=request.user)
            if not profile.is_email_verified:
                # Store the originally requested URL for post-verification redirect
                request.session['next_after_verification'] = request.get_full_path()
                messages.warning(request, 'Please verify your email address to access this feature.')
                return redirect('verification_required')
                
        except UserProfile.DoesNotExist:
            # If profile doesn't exist, don't block access
            return None
        
        return None