from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import json
import logging

# Configure logging
logger = logging.getLogger(__name__)

@login_required
def adjudication_statistics_api(request, timeframe):
    """
    API endpoint for adjudication statistics with different timeframes
    """
    try:
        # Import the analytics function
        from .adjudication_analytics import get_adjudication_trend_data
        
        # Log the request
        logger.info(f"Adjudication statistics API called with timeframe: {timeframe}")
        
        # Validate timeframe parameter
        valid_timeframes = ['week', 'month', 'year']
        if timeframe not in valid_timeframes:
            logger.warning(f"Invalid timeframe requested: {timeframe}")
            return JsonResponse({
                'error': f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}"
            }, status=400)
        
        # Get the data for the requested timeframe
        trend_data = get_adjudication_trend_data(timeframe)
        
        # Log success
        logger.info(f"Successfully retrieved adjudication data for timeframe: {timeframe}")
        logger.debug(f"Pending series data: {trend_data['pending_series']}")
        
        # Return as JSON
        return JsonResponse(trend_data)
    except Exception as e:
        # Log the error with full stack trace
        import traceback
        error_message = str(e)
        stack_trace = traceback.format_exc()
        logger.error(f"Error in adjudication_statistics_api: {error_message}\n{stack_trace}")
        
        # Return error response
        return JsonResponse({
            'error': f"Failed to retrieve adjudication statistics: {error_message}"
        }, status=500) 