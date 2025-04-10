from django.shortcuts import redirect
from django.urls import reverse
import traceback
import logging
import sys
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from django.conf import settings

logger = logging.getLogger('traffic_violation_system')

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

class ErrorLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log unhandled exceptions in detail to help diagnose 500 errors.
    """
    def process_exception(self, request, exception):
        """Log the exception details for debugging."""
        logger.error(f"ERROR HANDLING REQUEST: {request.path}")
        logger.error(f"USER: {request.user}")
        logger.error(f"EXCEPTION: {exception}")
        logger.error(traceback.format_exc())
        
        # Only show debug info directly on response if in DEBUG mode
        if settings.DEBUG:
            error_msg = f"<h1>Error processing request</h1>"
            error_msg += f"<p>Path: {request.path}</p>"
            error_msg += f"<p>User: {request.user}</p>"
            error_msg += f"<p>Exception: {exception}</p>"
            error_msg += f"<pre>{traceback.format_exc()}</pre>"
            return HttpResponse(error_msg, content_type='text/html', status=500)
        
        return None  # Let Django handle the response