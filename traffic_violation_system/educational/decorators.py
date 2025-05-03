from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from functools import wraps

def educator_required(view_func):
    """
    Decorator for views that checks that the user is an educator or admin.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Check if user has a userprofile and is either educator or admin
        if hasattr(request.user, 'userprofile') and request.user.userprofile.role in ['EDUCATOR', 'ADMIN']:
            return view_func(request, *args, **kwargs)
        elif request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "You don't have permission to access this page.")
            return redirect('home')  # Redirect to home page
            
    return wrapper 