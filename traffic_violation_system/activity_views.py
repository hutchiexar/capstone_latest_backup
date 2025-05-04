from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.models import User
from datetime import datetime, timedelta

from .models import ActivityLog

@login_required
def activity_history(request):
    """
    View for activity history with role-based access control.
    - ADMIN users can see all activity logs
    - Other roles (ENFORCER, SUPERVISOR, etc.) can only see their own logs
    """
    # Get the user's role
    user_role = request.user.userprofile.role
    
    # Role-based filtering
    if user_role == 'ADMIN':
        # Admins can see all logs
        activities = ActivityLog.objects.select_related('user', 'user__userprofile').all()
    else:
        # Non-admin users can only see their own logs
        activities = ActivityLog.objects.select_related('user', 'user__userprofile').filter(user=request.user)

    # Enhanced search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        activities = activities.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(action__icontains=search_query) |
            Q(details__icontains=search_query) |
            Q(category__icontains=search_query) |
            Q(user__userprofile__enforcer_id__icontains=search_query)
        ).distinct()

    # Get filter parameters
    category = request.GET.get('category', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    user_id = request.GET.get('user_id', '')

    # Apply filters
    if category:
        activities = activities.filter(category=category)
    
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            activities = activities.filter(timestamp__gte=date_from)
        except ValueError:
            pass

    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            # Add one day to include the entire end date
            date_to = date_to + timedelta(days=1)
            activities = activities.filter(timestamp__lt=date_to)
        except ValueError:
            pass

    # User ID filtering - only applies to admins
    if user_id and user_role == 'ADMIN':
        activities = activities.filter(user_id=user_id)

    # Order by timestamp descending (most recent first)
    activities = activities.order_by('-timestamp')

    # Pagination - 25 activities per page
    paginator = Paginator(activities, 25)
    page = request.GET.get('page', 1)
    try:
        activities = paginator.page(page)
    except PageNotAnInteger:
        activities = paginator.page(1)
    except EmptyPage:
        activities = paginator.page(paginator.num_pages)

    # Get all categories for filters
    categories = ActivityLog.CATEGORY_CHOICES
    
    # For user filtering, only admins see all users
    if user_role == 'ADMIN':
        users = User.objects.filter(
            id__in=ActivityLog.objects.values_list('user_id', flat=True).distinct()
        ).select_related('userprofile')
    else:
        # Non-admins only see themselves in the user filter dropdown
        users = User.objects.filter(id=request.user.id).select_related('userprofile')

    context = {
        'activities': activities,
        'categories': categories,
        'users': users,
        'current_category': category,
        'current_user': user_id,
        'date_from': date_from,
        'date_to': date_to,
        'page_obj': activities,
        'search_query': search_query,
        'total_count': paginator.count,
        'user_role': user_role  # Pass user role to template
    }

    return render(request, 'activity_history.html', context)
