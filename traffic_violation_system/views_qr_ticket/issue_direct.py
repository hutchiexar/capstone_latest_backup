from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
import json
import io
import base64
import qrcode
import uuid
import hashlib
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.conf import settings
from traffic_violation_system.models import ViolationType, Violation, ViolatorQRHash
# Import the entire views module to access both the constants and the issue_ticket function
from traffic_violation_system import views
from django.utils.safestring import mark_safe
from django.utils import timezone
import logging
from django.contrib import messages
from django.urls import reverse
from django.db import transaction
from decimal import Decimal
import os

def get_or_create_qr_hash(violation):
    """
    Get or create a QR hash for a given violation.
    This ensures that the same violator gets the same QR hash across different tickets,
    even when vehicle information differs.
    """
    logger = logging.getLogger(__name__)
    
    logger.info(f"get_or_create_qr_hash (issue_direct.py) called for violation ID: {violation.id}")
    
    # Standardize violator information
    if hasattr(violation, 'violator') and violation.violator:
        first_name = violation.violator.first_name.strip().lower() if violation.violator.first_name else "unknown"
        last_name = violation.violator.last_name.strip().lower() if violation.violator.last_name else "unknown"
        license_number = violation.violator.license_number.strip().upper().replace(' ', '') if violation.violator.license_number else None
        plate_number = violation.plate_number.strip().upper() if violation.plate_number else None
        logger.info(f"Got violator info from Violator model: {first_name} {last_name}, license: {license_number}, plate: {plate_number}")
    else:
        # If no violator relationship, try direct fields
        first_name = getattr(violation, 'first_name', getattr(violation, 'driver_name', "unknown"))
        if isinstance(first_name, str) and first_name.strip():
            first_name = first_name.strip().lower()
            # Try to split driver_name if it contains full name
            if ' ' in first_name and not getattr(violation, 'last_name', None):
                name_parts = first_name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1]
            else:
                last_name = getattr(violation, 'last_name', "unknown")
                if isinstance(last_name, str) and last_name.strip():
                    last_name = last_name.strip().lower()
                else:
                    last_name = "unknown"
        else:
            first_name = "unknown"
            last_name = "unknown"
            
        license_number = getattr(violation, 'license_number', None)
        if license_number and isinstance(license_number, str) and license_number.strip():
            license_number = license_number.strip().upper().replace(' ', '')
        else:
            license_number = None
            
        plate_number = getattr(violation, 'plate_number', None)
        if plate_number and isinstance(plate_number, str) and plate_number.strip():
            plate_number = plate_number.strip().upper()
        else:
            plate_number = None
            
        logger.info(f"Got violator info from direct fields: {first_name} {last_name}, license: {license_number}, plate: {plate_number}")
    
    # First check if the violation already has a QR hash
    if violation.qr_hash:
        logger.info(f"Violation {violation.id} already has QR hash: {violation.qr_hash.hash_id}")
        return violation.qr_hash.hash_id
    
    # Check for existing violations with the same violator
    existing_hash = None
    
    # COMPREHENSIVE SEARCH APPROACH:
    # 1. First try to find by license number (most reliable)
    # 2. Then by name if license not found
    # 3. Then check if other violations exist for the same person
    
    # First check by license number
    if license_number:
        logger.info(f"Looking for existing QR hash by license: {license_number}")
        
        # Check if any violation exists with this license number and has a QR hash
        existing_violation = Violation.objects.filter(
            violator__license_number__iexact=license_number, 
            qr_hash__isnull=False
        ).first()
        
        if existing_violation and existing_violation.qr_hash:
            existing_hash = existing_violation.qr_hash
            logger.info(f"Found QR hash through existing violation with same license: {existing_hash.hash_id}")
    else:
            # Direct check in QR hash table
            existing_hash = ViolatorQRHash.objects.filter(license_number__iexact=license_number).first()
            if existing_hash:
                logger.info(f"Found existing QR hash by license in hash table: {existing_hash.hash_id}")
    
    # If not found by license number, try by name
    if not existing_hash and first_name != "unknown" and last_name != "unknown":
        logger.info(f"Looking for existing QR hash by name: {first_name} {last_name}")
        
        # Check if any violation exists with this name and has a QR hash
        existing_violation = Violation.objects.filter(
            violator__first_name__iexact=first_name,
            violator__last_name__iexact=last_name,
            qr_hash__isnull=False
        ).first()
        
        if existing_violation and existing_violation.qr_hash:
            existing_hash = existing_violation.qr_hash
            logger.info(f"Found QR hash through existing violation with same name: {existing_hash.hash_id}")
        else:
            # Direct check in QR hash table
            existing_hash = ViolatorQRHash.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name
            ).first()
            if existing_hash:
                logger.info(f"Found existing QR hash by name in hash table: {existing_hash.hash_id}")
    
    # If we found an existing QR hash, link it to this violation
    if existing_hash:
        logger.info(f"Using existing QR hash {existing_hash.hash_id} for violation {violation.id}")
        
        # Check how many violations are already linked to this QR hash
        linked_violations = Violation.objects.filter(qr_hash=existing_hash).exclude(id=violation.id)
        if linked_violations.exists():
            logger.info(f"This QR hash is already linked to {linked_violations.count()} other violations")
            # Log some details about these violations for debugging
            for v in linked_violations[:3]:  # Limit to first 3 for log brevity
                v_plate = getattr(v, 'plate_number', 'Unknown')
                logger.info(f"Linked violation ID: {v.id}, Plate: {v_plate}")
        
        violation.qr_hash = existing_hash
        violation.save()
        return existing_hash.hash_id
    
    # If no existing hash was found, generate a new one
    logger.info(f"No existing QR hash found, generating new one for {first_name} {last_name}")
    
    # Call the centralized hash generation method from the model
    hash_id = ViolatorQRHash.generate_hash(
        first_name=first_name,
        last_name=last_name,
        license_number=license_number
    )
    
    # Create new QR hash with 90-day expiration
    qr_hash = ViolatorQRHash.objects.create(
        hash_id=hash_id,
        first_name=first_name,
        last_name=last_name,
        license_number=license_number,
        expires_at=timezone.now() + timezone.timedelta(days=90)
    )
    logger.info(f"Created new QR hash: {hash_id}")
    
    # Link it to the violation
    violation.qr_hash = qr_hash
    violation.save()
    logger.info(f"Linked new QR hash to violation {violation.id}")
    
    return hash_id

def generate_qr_code(request, hash_id):
    """
    Generate a QR code image for a hash
    """
    # Generate the registration URL with the hash
    url = request.build_absolute_uri(f"/register/violations/{hash_id}/")
    
    # Create the QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes for response
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    return buffer.getvalue(), url

@login_required
def violation_qr_code_print_view(request, violation_id):
    """
    View to display a printable page with the QR code for a violation ticket
    """
    violation = get_object_or_404(Violation, id=violation_id)
    
    # Get or create QR hash for this violation
    if not hasattr(violation, 'qr_hash') or not violation.qr_hash:
        qr_hash = get_or_create_qr_hash(violation)
        violation.qr_hash = qr_hash
        violation.save()
    
    # Generate QR code image
    qr_image, registration_url = generate_qr_code(request, violation.qr_hash)
    
    # Convert to base64 for embedding in HTML
    qr_image_base64 = base64.b64encode(qr_image).decode('utf-8')
    
    context = {
        'violation': violation,
        'qr_image_base64': qr_image_base64,
        'registration_url': registration_url,
    }
    
    return render(request, 'violations/print_qr_code.html', context)

# Form class definition (added to fix the error)
from django import forms

class DirectTicketForm(forms.Form):
    """Form for issuing a direct ticket to a violator."""
    direct_ticket_details = forms.CharField(widget=forms.Textarea, required=False)
    citation_number = forms.CharField(max_length=50)
    issue_date = forms.DateField()
    court_date = forms.DateField()
    fine_amount = forms.DecimalField(max_digits=10, decimal_places=2)

def save_signature_data_url(data_url):
    """
    Save a signature data URL to a file.
    
    Args:
        data_url: The data URL string containing the image data
        
    Returns:
        The filename of the saved signature image
    """
    if not data_url or not data_url.startswith('data:'):
        return None
    
    try:
        # Extract the base64 encoded data
        header, encoded = data_url.split(',', 1)
        
        # Get the file extension from the header (default to png)
        extension = 'png'
        if 'image/jpeg' in header:
            extension = 'jpg'
        elif 'image/png' in header:
            extension = 'png'
            
        # Decode the base64 data
        image_data = base64.b64decode(encoded)
        
        # Create a unique filename
        filename = f"signature_{uuid.uuid4()}.{extension}"
        
        # Create the signatures directory if it doesn't exist
        signatures_dir = os.path.join(settings.MEDIA_ROOT, 'signatures')
        os.makedirs(signatures_dir, exist_ok=True)
        
        # Write the image data to a file
        filepath = os.path.join(signatures_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(image_data)
            
        # Return the filename to be stored in the violation record
        return filename
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error saving signature data URL: {str(e)}", exc_info=True)
        return None

@login_required
def issue_direct_ticket(request, violation_id):
    """Issue a direct ticket to a violator for a specific violation."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Check if user can issue direct tickets
    if not request.user.has_perm('traffic_violation_system.issue_direct_tickets'):
        messages.error(request, 'You do not have permission to issue direct tickets.')
        return redirect('dashboard')

    # Get violation
    try:
        violation = Violation.objects.get(pk=violation_id)
    except Violation.DoesNotExist:
        messages.error(request, 'Violation not found.')
        return redirect('dashboard')

    # Ensure violation can be issued directly
    if violation.status != 'PENDING':
        messages.error(request, 'This violation cannot be issued directly as it is already processed.')
        return redirect('violation_detail', pk=violation_id)

    if request.method == 'POST':
        form = DirectTicketForm(request.POST)
        
        if form.is_valid():
            # Get form data
            direct_ticket_details = form.cleaned_data['direct_ticket_details']
            citation_number = form.cleaned_data['citation_number']
            issue_date = form.cleaned_data['issue_date']
            court_date = form.cleaned_data['court_date']
            fine_amount = form.cleaned_data['fine_amount']
            
            # Process signature data
            signature_data = request.POST.get('signature_data')
            is_signature_data_url = request.POST.get('is_signature_data_url') == 'true'
            signature_refused = request.POST.get('signature_refused') == 'true'
            
            # If we have a signature data URL, save it to a file
            if is_signature_data_url and signature_data and signature_data.startswith('data:'):
                logger.info("Processing signature data URL")
                signature_filename = save_signature_data_url(signature_data)
                if signature_filename:
                    logger.info(f"Saved signature as {signature_filename}")
                    signature_data = signature_filename
            
            try:
                with transaction.atomic():
                    logger.info(f"Starting direct ticket issuance for violation {violation_id}")
                    
                    # Update violation status
                    violation.status = 'ISSUED_DIRECT'
                    violation.direct_ticket_details = direct_ticket_details
                    violation.citation_number = citation_number
                    violation.fine_amount = fine_amount
                    violation.court_date = court_date
                    violation.issue_date = issue_date
                    violation.issued_by = request.user
                    
                    # Set signature data if available
                    if signature_refused:
                        violation.signature_refused = True
                        violation.refusal_note = request.POST.get('refusal_note', '')
                        logger.info(f"Violator refused to sign: {violation.refusal_note}")
                    elif signature_data:
                        violation.signature_file = signature_data
                        logger.info(f"Signature saved for violation {violation_id}")
                    
                    # Use get_or_create_qr_hash function to ensure consistency
                    hash_id = get_or_create_qr_hash(violation)
                    logger.info(f"Got QR hash ID: {hash_id} for violation {violation_id}")
                    
                    # Verify the violation has a qr_hash (sanity check)
                    violation.refresh_from_db()  # Refresh to ensure we have the latest data
                    if not violation.qr_hash:
                        logger.warning(f"Violation {violation_id} still has no QR hash after get_or_create_qr_hash call")
                        
                        # Try to find the QR hash by hash_id and link it manually
                        try:
                            qr_hash = ViolatorQRHash.objects.get(hash_id=hash_id)
                            violation.qr_hash = qr_hash
                            logger.info(f"Manually linked QR hash {hash_id} to violation {violation_id}")
                        except ViolatorQRHash.DoesNotExist:
                            logger.error(f"Failed to find QR hash with ID {hash_id}")
                    
                    # Save violation with all updates
                    violation.save()
                    
                    # Create QR code URL
                    qr_url = request.build_absolute_uri(
                        reverse('get_violation_qr_info', args=[violation.qr_hash.hash_id])
                    )
                    
                    # Add success message with QR code
                    messages.success(
                        request, 
                        mark_safe(
                            f'Direct ticket issued successfully with citation #{citation_number}.<br>'
                            f'QR Code: <a href="{qr_url}" target="_blank">View QR Code</a>'
                        )
                    )
                    
                    # Log direct ticket issuance
                    logger.info(
                        f"Direct ticket issued for violation {violation.id} "
                        f"with citation #{citation_number} by {request.user.username}"
                    )
                    
                    # Send notification if phone number is available
                    if violation.phone_number:
                        try:
                            # Check if we should send SMS based on settings or user preferences
                            send_direct_ticket_sms(
                                violation.phone_number,
                                violation.first_name,
                                citation_number,
                                fine_amount,
                                court_date,
                                qr_url
                            )
                            messages.info(request, f"SMS notification sent to {violation.phone_number}")
                        except Exception as e:
                            logger.error(f"Failed to send SMS: {str(e)}")
                            messages.warning(request, f"Failed to send SMS notification: {str(e)}")
                    
                    # Prepare ticket data for printing
                    try:
                        violator = violation.violator
                        ticket_data = {
                            'id': violation.id,
                            'citation_number': violation.citation_number,
                            'violation_date': violation.violation_date.strftime('%Y-%m-%d %H:%M'),
                            'first_name': violator.first_name,
                            'last_name': violator.last_name,
                            'license_number': violator.license_number or 'N/A',
                            'address': violator.address or 'N/A',
                            'phone_number': violator.phone_number or 'N/A',
                            'vehicle_type': violation.vehicle_type,
                            'plate_number': violation.plate_number or 'N/A',
                            'color': violation.color or 'N/A',
                            'registration_number': violation.registration_number or 'N/A',
                            'location': violation.location,
                            'violations': violation.get_violation_types(),
                            'fine_amount': float(violation.fine_amount),
                            'is_tdz_violation': violation.is_tdz_violation,
                            'enforcer': request.user.get_full_name(),
                            'enforcer_id': request.user.userprofile.enforcer_id if hasattr(request.user, 'userprofile') else 'N/A',
                            'registration_url': qr_url,
                            'signature_data': violation.signature_file,
                            'signature_refused': violation.signature_refused,
                            'refusal_note': violation.refusal_note or ''
                        }
                        
                        # Return JSON response for AJAX requests
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'success': True,
                                'ticket_data': ticket_data,
                                'qr_print_url': reverse('violation_qr_code_print_view', args=[violation.id])
                            })
                    except Exception as e:
                        logger.error(f"Error preparing ticket data: {str(e)}")
                        # Continue with regular response if ticket data preparation fails
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'success': True,
                                'message': 'Ticket issued successfully, but data preparation for printing failed.'
                            })
                    
                    return redirect('violation_detail', pk=violation.id)
            except Exception as e:
                logger.error(f"Error issuing direct ticket: {str(e)}", exc_info=True)
                messages.error(request, f"An error occurred while issuing the direct ticket: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': str(e)
                    })
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
    else:
        # Pre-fill the form with violation data
        initial_data = {
            'citation_number': f"AUTO-{violation.id}",
            'issue_date': timezone.now().date(),
            'court_date': (timezone.now() + timezone.timedelta(days=30)).date(),
            'fine_amount': violation.violation_type.default_fine if violation.violation_type else Decimal('50.00')
        }
        form = DirectTicketForm(initial=initial_data)

    context = {
        'form': form,
        'violation': violation
    }
    
    return render(request, 'ticket_issue/direct_ticket_form.html', context)

# Function stub for send_direct_ticket_sms (added to fix the error)
def send_direct_ticket_sms(phone_number, first_name, citation_number, fine_amount, court_date, qr_url):
    """Send SMS notification for direct ticket issuance"""
    # Implement SMS sending logic here
    logger = logging.getLogger(__name__)
    logger.info(f"Would send SMS to {phone_number} for citation {citation_number}")
    # This is a placeholder - actual SMS sending would be implemented here
    pass

@login_required
def direct_ticket_form(request):
    """Display the direct ticket form page"""
    # Set up logger
    logger = logging.getLogger(__name__)
    
    # Get all active violation types for the dropdown
    violation_types = ViolationType.objects.filter(is_active=True, classification='REGULAR').order_by('category', 'name')
    
    # Convert to JSON for JavaScript use
    violation_types_json = json.dumps([{
        'name': vt.name, 
        'amount': str(vt.amount),
        'category': vt.category,
        'classification': vt.classification
    } for vt in violation_types])

    # Initialize initial_data from session if available
    initial_data = {}
    
    # Check if we have ticket data in the session
    if 'ticket_data' in request.session:
        logger.info("Found ticket_data in session")
        ticket_data = request.session['ticket_data']
        logger.info(f"Session ticket_data: {ticket_data}")
        
        # Populate initial_data from session
        initial_data = {
            'first_name': ticket_data.get('first_name', ''),
            'last_name': ticket_data.get('last_name', ''),
            'license_number': ticket_data.get('license_number', ''),
            'phone_number': ticket_data.get('phone_number', ''),
            'address': ticket_data.get('address', ''),
            'vehicle_type': ticket_data.get('vehicle_type', ''),
            'plate_number': ticket_data.get('plate_number', ''),
            'color': ticket_data.get('color', ''),
            'classification': ticket_data.get('classification', ''),
            'registration_number': ticket_data.get('registration_number', ''),
            'registration_date': ticket_data.get('registration_date', ''),
            'vehicle_owner': ticket_data.get('vehicle_owner', ''),
            'vehicle_owner_address': ticket_data.get('vehicle_owner_address', ''),
        }
        
        # Add user_account_id if available
        if 'user_account_id' in ticket_data:
            initial_data['user_account_id'] = ticket_data['user_account_id']
        
        # Add driver_id if available
        if 'driver_id' in ticket_data:
            initial_data['driver_id'] = ticket_data['driver_id']
            
        # Set violator source for tracking
        initial_data['violator_source'] = ticket_data.get('data_source', 'manual')
        
        logger.info(f"Populated initial_data from session: {initial_data}")
    else:
        logger.warning("No ticket_data found in session")
    
    # Special handling for dates in the JSON serialization
    for key, value in initial_data.items():
        # Handle date objects by converting them to strings
        if hasattr(value, 'strftime'):
            initial_data[key] = value.strftime('%Y-%m-%d')
    
    # Convert initial_data to JSON for JavaScript with proper escaping
    try:
        initial_data_json = json.dumps(initial_data)
        logger.info(f"Serialized initial data: {initial_data_json}")
    except Exception as e:
        logger.error(f"Error serializing initial data: {str(e)}")
        initial_data_json = '{}'

    # Render the template with the initial data
    return render(request, 'violations/issue_direct_ticket.html', {
        'violation_choices': views.VIOLATION_CHOICES,
        'vehicle_classifications': views.VEHICLE_CLASSIFICATIONS,
        'violation_types': violation_types,
        'violation_types_json': violation_types_json,
        'initial_data': mark_safe(initial_data_json),  # Mark as safe to prevent double-escaping
        'ticket_data': request.session.get('ticket_data', {})  # Pass the raw session data too
    }) 