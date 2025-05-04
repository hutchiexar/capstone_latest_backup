from django.shortcuts import redirect
from django.urls import reverse, resolve
from django.contrib import messages
from django.conf import settings

import re
from .models import UserProfile
import logging

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
            reverse('verification_pending'),
            reverse('verification_required'),
        ]
        
        # Check if URL is verification-related
        if 'verification' in request.path or 'verify_email' in request.path:
            return None
        
        # Allow access to landing pages, static files, and media files
        if (request.path in exempt_urls or 
            any(url in request.path for url in ['/verification/', '/verify/']) or
            request.path.startswith('/static/') or 
            request.path.startswith('/media/')):
            return None

        # Require authentication for all other pages
        if not request.user.is_authenticated:
            # Store the next URL in the session for redirect after login
            next_url = request.get_full_path()
            request.session['next'] = next_url
            return redirect('login')
            
        # For authenticated users, if they're enforcers and trying to access the root URL,
        # redirect them to enforcer_map instead of dashboard
        if request.path == '/' and hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'ENFORCER':
            return redirect('enforcer_map')
            
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
            r'^/login/?$',
            r'^/accounts/login/?$',
            r'^/logout/?$',
            r'^/accounts/logout/?$',
            r'^/register/?$',
            r'^/accounts/register/?$',
            r'^/verification/',
            r'^/accounts/password_reset/',
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
        
        # Log the current path for troubleshooting
        logger = logging.getLogger(__name__)
        logger.debug(f"EmailVerificationMiddleware: Checking path {path}")
        
        if any(re.match(url, path) for url in self.exempt_urls):
            logger.debug(f"EmailVerificationMiddleware: Path {path} is exempt")
            return None
        
        # Staff and superusers bypass verification
        if request.user.is_staff or request.user.is_superuser:
            logger.debug(f"EmailVerificationMiddleware: User {request.user.username} is staff or superuser, bypassing")
            return None
        
        # Check if user has verified their email
        try:
            profile = UserProfile.objects.get(user=request.user)
            if not profile.is_email_verified:
                # Store the originally requested URL for post-verification redirect
                request.session['next_after_verification'] = request.get_full_path()
                
                # Store the registration email for use on the verification page
                request.session['registration_email'] = request.user.email
                
                logger.info(f"EmailVerificationMiddleware: Redirecting unverified user {request.user.username} to verification_required")
                messages.warning(request, 'Email verification required. Please verify your email address to continue.')
                return redirect('verification_pending')
                
        except UserProfile.DoesNotExist:
            # If profile doesn't exist, don't block access
            logger.warning(f"EmailVerificationMiddleware: User {request.user.username} has no profile")
            return None
        
        return None

class AdjudicationAccessMiddleware:
    """Middleware to restrict adjudication access for ENFORCER, SUPERVISOR, and TREASURER roles."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # URLs that should be restricted 
        self.restricted_paths = [
            r'^/adjudication/',
            r'^/adjudication-dashboard/',
            r'^/adjudication_dashboard/',
            r'^/adjudication_list/',
            r'^/submit_adjudication/',
            r'^/adjudicate/',
            r'^/adjudication_form/',
            r'^/rejected_adjudications/',
            r'^/$',  # Main dashboard URL
            r'^/admin_dashboard/',
            r'^/dashboard/',
        ]
        
        # URLs related to ticketing
        self.ticketing_paths = [
            r'^/issue-ticket/',
            r'^/upload-violation/',
            r'^/ncap-upload/', 
        ]
        
        # QR Scanner path
        self.qr_scanner_paths = [
            r'^/qr-scanner/',
        ]
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip for non-authenticated users
        if not request.user.is_authenticated:
            return None
            
        # Check user role
        try:
            profile = UserProfile.objects.get(user=request.user)
            path = request.path_info
            
            # Skip restrictions for educators entirely
            if profile.role == 'EDUCATOR':
                return None
                
            # For treasurers, block adjudication, ticketing, and QR scanner
            if profile.role == 'TREASURER':
                # Block adjudication paths
                adjudication_paths = [url for url in self.restricted_paths if 'adjudication' in url]
                if any(re.match(url, path) for url in adjudication_paths):
                    messages.warning(request, 'Access to adjudication features is restricted for your role.')
                    return redirect('dashboard')
                
                # Block ticketing paths
                if any(re.match(url, path) for url in self.ticketing_paths):
                    messages.warning(request, 'Access to ticketing features is restricted for your role.')
                    return redirect('dashboard')
                
                # Block QR scanner
                if any(re.match(url, path) for url in self.qr_scanner_paths):
                    messages.warning(request, 'Access to QR scanner is restricted for your role.')
                    return redirect('dashboard')
            
            # For supervisors, specifically block adjudication-related paths
            if profile.role == 'SUPERVISOR':
                adjudication_paths = [url for url in self.restricted_paths if 'adjudication' in url]
                if any(re.match(url, path) for url in adjudication_paths):
                    messages.warning(request, 'Access to adjudication features is restricted for your role.')
                    return redirect('dashboard')
            
            # For enforcers, continue with existing restrictions
            if profile.role == 'ENFORCER':
                # Only restrict enforcer from specified paths 
                if any(re.match(url, path) for url in self.restricted_paths):
                    messages.warning(request, 'Access to this area is restricted for your role.')
                    return redirect('enforcer_map')
                
        except UserProfile.DoesNotExist:
            # If profile doesn't exist, don't block access
            return None
        
        return None

class EducatorAccessMiddleware:
    """Middleware to ensure educators can access the educational features."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # URLs related to educator features
        self.educator_paths = [
            r'^/educational/',
            r'^/educational/admin/',
            r'^/educational/admin/dashboard/',
            r'^/educational/admin/categories/',
            r'^/educational/admin/topics/',
            r'^/educational/admin/quizzes/',
            r'^/educational/categories-management/',
            r'^/educational/topics-management/',
            r'^/educational/quizzes-management/',
            r'^/educational/educator-dashboard/',
            r'^/announcements/',
            r'^/profile/',
            r'^/activity_history/',
            r'^/logout/',
            r'^/edit_profile/',
        ]
        
        # URLs that should redirect to the educational dashboard
        self.redirect_paths = [
            r'^/$',
            r'^/admin_dashboard/',
            r'^/dashboard/',
            r'^/violations/',
            r'^/payment/',
            r'^/issue-ticket/',
        ]
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip for non-authenticated users
        if not request.user.is_authenticated:
            return None
            
        # Check user role
        try:
            profile = UserProfile.objects.get(user=request.user)
            
            # Only process for educators
            if profile.role == 'EDUCATOR':
                path = request.path_info
                
                # Check if the current path is allowed
                is_allowed_path = any(re.match(pattern, path) for pattern in self.educator_paths)
                
                # If not an allowed path, check if it should be redirected
                if not is_allowed_path:
                    should_redirect = any(re.match(pattern, path) for pattern in self.redirect_paths)
                    
                    if should_redirect:
                        # If the user is trying to access a redirect path, send them to educational dashboard
                        messages.info(request, 'Redirected to the Education Portal dashboard.')
                        return redirect('educational:admin_index')
                    
                # Special handling for educational URLs
                if path.startswith('/educational/'):
                    # Handle specific URL patterns that might cause issues
                    if 'admin/topics' in path and not path.endswith('/'):
                        return redirect('educational:admin_topic_list')
                    
                    if 'admin/categories' in path and not path.endswith('/'):
                        return redirect('educational:admin_category_list')
                    
                    if 'admin/quizzes' in path and not path.endswith('/'):
                        return redirect('educational:admin_quiz_list')
                    
                    # If trying to access educational admin pages, ensure the URL is correct
                    if 'admin' in path and not re.match(r'^/educational/admin/?', path):
                        # Fix URL if needed - redirect to correct admin URL format
                        corrected_path = '/educational/admin/'
                        return redirect(corrected_path)
                        
        except UserProfile.DoesNotExist:
            # If profile doesn't exist, don't interfere
            return None
        
        return None