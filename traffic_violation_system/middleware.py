from django.shortcuts import redirect
from django.urls import reverse
import logging
import sys
import traceback
from django.conf import settings

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

class ErrorLoggingMiddleware:
    """
    Middleware that logs exceptions to the console.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.
        self.logger = logging.getLogger('traffic_violation_system')

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        response = self.get_response(request)
        # Code to be executed for each request/response after
        # the view is called.
        return response

    def process_exception(self, request, exception):
        """
        Process the exception and log it.
        """
        # Get the full traceback
        exc_info = sys.exc_info()
        # Format the traceback
        tb = ''.join(traceback.format_exception(*exc_info))
        # Log the exception
        self.logger.error(f"Unhandled exception: {str(exception)}\n{tb}")
        # Log request information
        self.logger.debug(f"Request path: {request.path}")
        self.logger.debug(f"Request method: {request.method}")
        self.logger.debug(f"Request user: {request.user}")
        # Continue processing
        return None