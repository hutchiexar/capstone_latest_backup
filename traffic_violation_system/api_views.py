from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import json

@login_required
def adjudication_statistics_api(request, timeframe):
    """
    API endpoint for adjudication statistics with different timeframes
    """
    try:
        # Import the analytics function
        from .adjudication_analytics import get_adjudication_trend_data
        
        # Get the data for the requested timeframe
        trend_data = get_adjudication_trend_data(timeframe)
        
        # Return as JSON
        return JsonResponse(trend_data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'error': str(e)
        }, status=500) 