from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import json
from django.http import JsonResponse
from traffic_violation_system.models import ViolationType
# Import the entire views module to access both the constants and the issue_ticket function
from traffic_violation_system import views
from django.utils.safestring import mark_safe

@login_required
def issue_direct_ticket(request):
    """
    Modified version of the issue_ticket function that properly handles session data
    from QR code scans. This allows for pre-populated form fields.
    """
    # Initialize context with session data if available
    initial_data = {}
    if 'ticket_data' in request.session:
        initial_data = request.session.get('ticket_data', {})
        # Add additional debug output
        print(f"Initial data from session: {initial_data}")
        # Don't delete the session data yet, we'll do it after successful submission

    # Handle form submission with the same logic as the original issue_ticket
    if request.method == 'POST':
        # Forward to the original issue_ticket view
        response = views.issue_ticket(request)
        
        # Clear session data after successful submission
        if 'ticket_data' in request.session:
            del request.session['ticket_data']
            request.session.modified = True
            
        return response

    # Get all active violation types for the dropdown
    violation_types = ViolationType.objects.filter(is_active=True, classification='REGULAR').order_by('category', 'name')
    
    # Convert to JSON for JavaScript use
    violation_types_json = json.dumps([{
        'name': vt.name, 
        'amount': str(vt.amount),
        'category': vt.category,
        'classification': vt.classification
    } for vt in violation_types])
    
    # Special handling for dates in the JSON serialization
    for key, value in initial_data.items():
        # Handle date objects by converting them to strings
        if hasattr(value, 'strftime'):
            initial_data[key] = value.strftime('%Y-%m-%d')
    
    # Convert initial_data to JSON for JavaScript with proper escaping
    try:
        initial_data_json = json.dumps(initial_data)
        print(f"Serialized initial data: {initial_data_json}")
    except Exception as e:
        print(f"Error serializing initial data: {str(e)}")
        initial_data_json = '{}'

    # Render the template with the initial data
    return render(request, 'violations/issue_direct_ticket.html', {
        'violation_choices': views.VIOLATION_CHOICES,
        'vehicle_classifications': views.VEHICLE_CLASSIFICATIONS,
        'violation_types': violation_types,
        'violation_types_json': violation_types_json,
        'initial_data': mark_safe(initial_data_json)  # Mark as safe to prevent double-escaping
    }) 