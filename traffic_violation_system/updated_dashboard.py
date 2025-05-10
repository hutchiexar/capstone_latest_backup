from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Violation

@login_required
def admin_dashboard(request):
    today = timezone.now()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Get violations statistics
    violations = Violation.objects.all()
    total_violations = violations.count()
    weekly_violations = violations.filter(violation_date__gte=week_ago).count()
    monthly_violations = violations.filter(violation_date__gte=month_ago).count()

    # Get status-based counts
    pending_violations = violations.filter(status='PENDING').count()
    paid_violations_count = violations.filter(status='PAID').count()
    settled_violations = violations.filter(status='SETTLED').count()
    overdue_violations = violations.filter(status='OVERDUE').count()

    # Calculate revenue statistics
    paid_violations = violations.filter(status='PAID')
    total_revenue = paid_violations.aggregate(total=Sum('fine_amount'))['total'] or 0
    monthly_revenue = paid_violations.filter(
        receipt_date__gte=month_ago
    ).aggregate(total=Sum('fine_amount'))['total'] or 0
    weekly_revenue = paid_violations.filter(
        receipt_date__gte=week_ago
    ).aggregate(total=Sum('fine_amount'))['total'] or 0

    # Get violations trend data (last 30 days)
    dates = []
    violations_data = []
    
    for i in range(30, -1, -1):
        date = today - timedelta(days=i)
        # Format date as ISO string for proper JavaScript parsing
        dates.append(date.strftime('%Y-%m-%d'))
        count = violations.filter(
            violation_date__date=date.date()
        ).count()
        violations_data.append(count)

    # Import adjudication analytics data
    from .adjudication_analytics import (
        get_adjudication_summary,
        get_adjudication_trend_data,
        get_adjudication_type_breakdown,
        get_adjudication_performance
    )
    
    # Get adjudication analytics
    adjudication_summary = get_adjudication_summary()
    adjudication_trend = get_adjudication_trend_data('month')
    adjudication_types = get_adjudication_type_breakdown()
    adjudication_performance = get_adjudication_performance()
    
    # Paginate recent violations
    recent_violations = violations.order_by('-violation_date')
    paginator = Paginator(recent_violations, 5)  # Show 5 violations per page
    page = request.GET.get('page', 1)
    
    try:
        paginated_violations = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        paginated_violations = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        paginated_violations = paginator.page(paginator.num_pages)
    
    context = {
        'total_violations': total_violations,
        'total_revenue': total_revenue,
        'pending_violations': pending_violations,
        'overdue_violations': overdue_violations,
        'weekly_violations': weekly_violations,
        'monthly_violations': monthly_violations,
        'weekly_revenue': weekly_revenue,
        'monthly_revenue': monthly_revenue,
        'paid_violations': paid_violations_count,
        'settled_violations': settled_violations,
        'dates': json.dumps(dates, cls=DjangoJSONEncoder),
        'violations_data': json.dumps(violations_data),
        'recent_violations': paginated_violations,
        'is_paginated': True,
        
        # Adjudication data
        'adjudication_summary': adjudication_summary,
        'adjudication_trend': {
            'dates': json.dumps(adjudication_trend['dates'], cls=DjangoJSONEncoder),
            'approved_series': json.dumps(adjudication_trend['approved_series']),
            'rejected_series': json.dumps(adjudication_trend['rejected_series']),
            'pending_series': json.dumps(adjudication_trend['pending_series'])
        },
        'adjudication_types': {
            'labels': json.dumps(adjudication_types['labels']),
            'values': json.dumps(adjudication_types['values'])
        },
        'adjudication_performance': {
            'avg_days': adjudication_performance['avg_days_to_adjudicate'],
            'month_labels': json.dumps(adjudication_performance['month_labels']),
            'month_values': json.dumps(adjudication_performance['month_values'])
        }
    }

    return render(request, 'violations/admin_dashboard.html', context) 