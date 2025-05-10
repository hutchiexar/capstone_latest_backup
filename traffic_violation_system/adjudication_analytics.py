from django.db.models import Count, Q, F, Sum, Avg, Case, When, IntegerField, FloatField
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, ExtractMonth, ExtractYear
from django.utils import timezone
from datetime import datetime, timedelta
import json
from .models import Violation

def get_adjudication_summary():
    """
    Get summary statistics for adjudicated violations
    """
    today = timezone.now()
    last_month = today - timedelta(days=30)
    last_week = today - timedelta(days=7)
    
    # Overall counts
    total_adjudications = Violation.objects.filter(
        adjudicated_by__isnull=False,
        adjudication_date__isnull=False
    ).count()
    
    approved_count = Violation.objects.filter(status='APPROVED').count()
    rejected_count = Violation.objects.filter(status='REJECTED').count()
    pending_count = Violation.objects.filter(status__in=['ADJUDICATED', 'PENDING']).count()
    
    # Recent period counts
    weekly_adjudications = Violation.objects.filter(
        adjudication_date__gte=last_week,
        adjudicated_by__isnull=False
    ).count()
    
    monthly_adjudications = Violation.objects.filter(
        adjudication_date__gte=last_month,
        adjudicated_by__isnull=False
    ).count()
    
    # Calculate approval rate
    if total_adjudications > 0:
        approval_rate = (approved_count / total_adjudications) * 100
    else:
        approval_rate = 0
    
    return {
        'total_adjudications': total_adjudications,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'pending_count': pending_count,
        'weekly_adjudications': weekly_adjudications,
        'monthly_adjudications': monthly_adjudications,
        'approval_rate': round(approval_rate, 1)
    }

def get_adjudication_trend_data(timeframe='month'):
    """
    Get trend data for adjudications over time
    timeframe: 'week', 'month', or 'year'
    """
    today = timezone.now()
    
    if timeframe == 'week':
        start_date = today - timedelta(days=7)
        date_trunc = TruncDate('adjudication_date')
        date_format = '%Y-%m-%d'
    elif timeframe == 'month':
        start_date = today - timedelta(days=30)
        date_trunc = TruncDate('adjudication_date')
        date_format = '%Y-%m-%d'
    else:  # year
        start_date = today - timedelta(days=365)
        date_trunc = TruncMonth('adjudication_date')
        date_format = '%Y-%m'
    
    # Get adjudication counts by date
    adjudication_data = Violation.objects.filter(
        adjudication_date__gte=start_date,
        adjudicated_by__isnull=False
    ).annotate(
        date=date_trunc
    ).values('date').annotate(
        total=Count('id'),
        approved=Count('id', filter=Q(status='APPROVED')),
        rejected=Count('id', filter=Q(status='REJECTED')),
        pending=Count('id', filter=Q(status__in=['ADJUDICATED', 'PENDING']))
    ).order_by('date')
    
    # Also include violations that have PENDING status without adjudication date
    pending_data = Violation.objects.filter(
        violation_date__gte=start_date,
        status='PENDING',
        adjudication_date__isnull=True
    ).annotate(
        date=TruncDate('violation_date')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Convert pending_data to dictionary for easy lookup
    pending_dict = {item['date'].strftime(date_format): item['count'] for item in pending_data}
    
    # Convert to lists for chart data
    dates = []
    approved_series = []
    rejected_series = []
    pending_series = []
    
    # Convert to dict for easier date filling
    data_dict = {item['date'].strftime(date_format): item for item in adjudication_data}
    
    # Fill in dates with no data
    if timeframe == 'week' or timeframe == 'month':
        delta = timedelta(days=1)
    else:  # year
        delta = timedelta(days=30)  # approximate for months
    
    current_date = start_date
    while current_date <= today:
        date_str = current_date.strftime(date_format)
        
        if date_str in data_dict:
            item = data_dict[date_str]
            dates.append(date_str)
            approved_series.append(item['approved'])
            rejected_series.append(item['rejected'])
            
            # Add any additional pending violations from pending_dict
            additional_pending = pending_dict.get(date_str, 0)
            pending_series.append(item['pending'] + additional_pending)
        else:
            dates.append(date_str)
            approved_series.append(0)
            rejected_series.append(0)
            
            # Use pending_dict if available for this date
            pending_series.append(pending_dict.get(date_str, 0))
        
        current_date += delta
    
    # Add debug information
    print(f"Generated adjudication trend data for {timeframe}")
    print(f"Dates: {dates}")
    print(f"Pending Series: {pending_series}")
    
    return {
        'dates': dates,
        'approved_series': approved_series,
        'rejected_series': rejected_series,
        'pending_series': pending_series
    }

def get_adjudication_type_breakdown():
    """
    Get breakdown of violation types that have been adjudicated
    """
    # Get top violation types that have been adjudicated
    violation_types = Violation.objects.filter(
        adjudicated_by__isnull=False
    ).values('violation_type').annotate(
        count=Count('id')
    ).order_by('-count')[:8]  # Get top 8 types
    
    labels = []
    values = []
    
    for vtype in violation_types:
        labels.append(vtype['violation_type'])
        values.append(vtype['count'])
    
    return {
        'labels': labels,
        'values': values
    }

def get_adjudication_performance():
    """
    Get performance metrics for adjudication process
    """
    # Calculate average time to adjudicate (in days)
    violations_with_dates = Violation.objects.filter(
        adjudicated_by__isnull=False,
        adjudication_date__isnull=False,
        violation_date__isnull=False
    )
    
    # Calculate average manually instead of using database aggregation
    total_days = 0
    count = 0
    
    for violation in violations_with_dates:
        if violation.adjudication_date and violation.violation_date:
            delta = violation.adjudication_date - violation.violation_date
            total_days += delta.total_seconds() / (60 * 60 * 24)  # Convert to days
            count += 1
    
    avg_time = total_days / count if count > 0 else 0
    
    # Get monthly adjudication counts for the past year
    today = timezone.now()
    year_ago = today - timedelta(days=365)
    
    monthly_counts = Violation.objects.filter(
        adjudication_date__gte=year_ago,
        adjudicated_by__isnull=False
    ).annotate(
        month=TruncMonth('adjudication_date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    month_labels = []
    month_values = []
    
    for item in monthly_counts:
        month_labels.append(item['month'].strftime('%b %Y'))
        month_values.append(item['count'])
    
    return {
        'avg_days_to_adjudicate': round(avg_time, 1),
        'month_labels': month_labels,
        'month_values': month_values
    } 