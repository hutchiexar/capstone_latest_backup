"""
Module for handling QR code-based violation registration.
This module provides functionality for generating QR codes for violations
and handling user registration with linked violations.
"""

import io
import base64
import uuid
import hashlib
import qrcode
import logging
from datetime import datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.db import transaction
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django import forms

from .models import Violation, ViolationType, UserProfile, ViolatorQRHash

logger = logging.getLogger(__name__)

# QR code hash table - in a real application, this would be stored in the database
# For now, we'll use an in-memory dictionary for simplicity
qr_hash_map = {}

class ExtendedUserCreationForm(UserCreationForm):
    """Extended UserCreationForm with additional fields for registration."""
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    license_number = forms.CharField(required=False)
    address = forms.CharField(required=False, widget=forms.Textarea)
    phone_number = forms.CharField(required=False)
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
    
    def clean_email(self):
        """Validate that the email is not already in use."""
        email = self.cleaned_data.get('email')
        
        # Basic format validation
        if email:
            # Check for @ symbol and proper domain format
            if '@' not in email:
                raise forms.ValidationError("Please enter a valid email address with '@' symbol.")
            
            # Split email into username and domain parts
            parts = email.split('@')
            if len(parts) != 2 or not parts[0] or not parts[1]:
                raise forms.ValidationError("Please enter a valid email address with username and domain.")
            
            # Check domain has at least one dot (for TLD)
            domain = parts[1]
            if '.' not in domain or domain.endswith('.'):
                raise forms.ValidationError("Please enter an email with a valid domain (example@domain.com).")
            
            # Check if email already exists in system
            if User.objects.filter(email__iexact=email).exists():
                # Get the existing user details for logging purposes
                existing_user = User.objects.get(email__iexact=email)
                logger.warning(
                    f"Registration attempt with existing email: {email}. "
                    f"Email belongs to user: {existing_user.username} (ID: {existing_user.id})"
                )
                raise forms.ValidationError("This email address is already registered. Please use a different email or login to your existing account.")
        
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user

def get_or_create_qr_hash(violation):
    """Get or create a QR hash for the given violation."""
    logger.info(f"get_or_create_qr_hash (views_violation_qr.py) called for violation ID: {violation.id}")
    
    # Get violator information from the violator relationship
    if hasattr(violation, 'violator') and violation.violator:
        # Get information from the violator object
        first_name = violation.violator.first_name.strip().lower() if violation.violator.first_name else "unknown"
        last_name = violation.violator.last_name.strip().lower() if violation.violator.last_name else "unknown"
        license_number = violation.violator.license_number.strip().upper().replace(' ', '') if violation.violator.license_number else None
        phone_number = violation.violator.phone_number if hasattr(violation.violator, 'phone_number') else None
        
        logger.info(f"Got violator info from related Violator model for violation {violation.id}")
    else:
        # Fallback to other fields that might exist on the Violation model
        logger.info(f"No violator relationship found for violation {violation.id}, checking direct fields")
        first_name = getattr(violation, 'first_name', getattr(violation, 'driver_name', "unknown"))
        if first_name:
            first_name = first_name.strip().lower()
            # If driver_name contains full name, try to split it
            if ' ' in first_name and not getattr(violation, 'last_name', None):
                name_parts = first_name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1]
            else:
                first_name = first_name
                last_name = getattr(violation, 'last_name', "unknown")
        else:
            first_name = "unknown"
            
        last_name = getattr(violation, 'last_name', "unknown")
        if last_name:
            last_name = last_name.strip().lower()
        else:
            last_name = "unknown"
            
        license_number = getattr(violation, 'license_number', None)
        if license_number:
            license_number = license_number.strip().upper().replace(' ', '')
            
        phone_number = getattr(violation, 'phone_number', None)
    
    logger.info(f"Standardized violator info: {first_name} {last_name}, license: {license_number}")
    
    # Additional vehicle information for logging purposes
    vehicle_type = getattr(violation, 'vehicle_type', 'Unknown')
    plate_number = getattr(violation, 'plate_number', 'Unknown')
    logger.info(f"Vehicle info for violation {violation.id}: Type: {vehicle_type}, Plate: {plate_number}")

    # First check if violation already has a QR hash
    if violation.qr_hash:
        logger.info(f"Violation {violation.id} already has QR hash: {violation.qr_hash.hash_id}")
        return violation.qr_hash.hash_id

    # Check for existing QR hash for the violator - FIRST APPROACH: By License + User Account
    logger.info(f"Checking for existing violations and QR hashes for the same violator")
    existing_hash = None
    
    # Try to find by license number first (most reliable)
    if license_number:
        logger.info(f"Looking for existing QR hash by license number: {license_number}")
        
        # Check if another violation with the same license number already has a QR hash
        existing_violation_with_hash = Violation.objects.filter(
            violator__license_number__iexact=license_number,
            qr_hash__isnull=False
        ).first()
        
        if existing_violation_with_hash and existing_violation_with_hash.qr_hash:
            existing_hash = existing_violation_with_hash.qr_hash
            logger.info(f"Found QR hash through another violation with same license: {existing_hash.hash_id}")
        else:
            # If no violation found with same license and QR hash, check QR hash table directly
            existing_hash = ViolatorQRHash.objects.filter(
                license_number__iexact=license_number
            ).first()
            if existing_hash:
                logger.info(f"Found existing QR hash by license in QRHash table: {existing_hash.hash_id}")
    
    # If not found by license, try by name
    if not existing_hash and first_name != "unknown" and last_name != "unknown":
        logger.info(f"Looking for existing QR hash by name: {first_name} {last_name}")
        
        # Check if another violation with the same name already has a QR hash
        existing_violation_with_hash = Violation.objects.filter(
            violator__first_name__iexact=first_name,
            violator__last_name__iexact=last_name,
            qr_hash__isnull=False
        ).first()
        
        if existing_violation_with_hash and existing_violation_with_hash.qr_hash:
            existing_hash = existing_violation_with_hash.qr_hash
            logger.info(f"Found QR hash through another violation with same name: {existing_hash.hash_id}")
        else:
            # If no violation found with same name and QR hash, check QR hash table directly
            existing_hash = ViolatorQRHash.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name
            ).first()
            if existing_hash:
                logger.info(f"Found existing QR hash by name in QRHash table: {existing_hash.hash_id}")
    
    # If we found an existing QR hash, use it
    if existing_hash:
        logger.info(f"Using existing QR hash {existing_hash.hash_id} for violation {violation.id}")
        
        # Check if this QR hash has linked violations and log them for debugging
        linked_violations = Violation.objects.filter(qr_hash=existing_hash).exclude(id=violation.id)
        if linked_violations.exists():
            logger.info(f"This QR hash is already linked to {linked_violations.count()} other violations")
            for v in linked_violations:
                v_vehicle_type = getattr(v, 'vehicle_type', 'Unknown')
                v_plate = getattr(v, 'plate_number', 'Unknown')
                logger.info(f"Linked violation ID: {v.id}, Vehicle: {v_vehicle_type}, Plate: {v_plate}")
        
        violation.qr_hash = existing_hash
        violation.save()
        return existing_hash.hash_id

    # If no existing hash was found, generate a new one
    logger.info(f"No existing QR hash found, generating new one for {first_name} {last_name}")
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
        phone_number=phone_number,
        expires_at=timezone.now() + timezone.timedelta(days=90)
    )
    logger.info(f"Created new QR hash: {hash_id}")

    # Link it to the violation
    violation.qr_hash = qr_hash
    violation.save()
    logger.info(f"Linked new QR hash to violation {violation.id}")

    return hash_id

def generate_qr_code(hash_id, base_url=None):
    """
    Generate a QR code for a violation hash.
    
    Args:
        hash_id: The hash ID for the violation
        base_url: The base URL for the application
        
    Returns:
        tuple: (bytes, str) The QR code image as bytes and the registration URL
    """
    if base_url is None:
        base_url = settings.BASE_URL if hasattr(settings, 'BASE_URL') else 'http://localhost:8000'
    
    # Create the registration URL with the hash
    # Instead of using reverse, we'll use a hard-coded URL pattern
    registration_url = f"{base_url}/register/violations/{hash_id}/"
    
    # Generate the QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(registration_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert the image to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes = img_bytes.getvalue()
    
    return img_bytes, registration_url

def violation_qr_code_image(request, violation_id):
    """
    Generate and serve a QR code image for a violation.
    
    Args:
        request: The HTTP request
        violation_id: The ID of the violation
        
    Returns:
        HttpResponse: The QR code image as a PNG
    """
    try:
        violation = get_object_or_404(Violation, id=violation_id)
        hash_id = get_or_create_qr_hash(violation)
        qr_img, _ = generate_qr_code(hash_id)
        
        return HttpResponse(qr_img, content_type='image/png')
    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
        return HttpResponse("Error generating QR code", status=500)

def violation_qr_code_print_view(request, violation_id):
    """
    Display a printable page with QR code for a violation ticket.
    
    Args:
        request: The HTTP request
        violation_id: The ID of the violation
        
    Returns:
        HttpResponse: Rendered template with the QR code
    """
    try:
        violation = get_object_or_404(Violation, id=violation_id)
        hash_id = get_or_create_qr_hash(violation)
        qr_img, registration_url = generate_qr_code(hash_id)
        
        # Convert QR code to base64 for embedding in HTML
        qr_code_base64 = base64.b64encode(qr_img).decode('utf-8')
        
        context = {
            'violation': violation,
            'qr_code_base64': qr_code_base64,
            'registration_url': registration_url
        }
        
        return render(request, 'violations/qr_code_print.html', context)
    except Exception as e:
        logger.error(f"Error rendering QR code print view: {str(e)}")
        messages.error(request, "Error generating QR code for printing.")
        return redirect('issue_direct_ticket')

def get_violation_qr_info(request, hash_id):
    """
    API endpoint to get information about a violation from its QR hash.
    
    Args:
        request: The HTTP request
        hash_id: The hash ID from the QR code
        
    Returns:
        JsonResponse: Violation information in JSON format
    """
    try:
        # First check the in-memory map
        violation_id = None
        for vid, hid in qr_hash_map.items():
            if hid == hash_id:
                violation_id = int(vid)
                logger.info(f"Found violation ID {violation_id} in memory for hash {hash_id}")
                break
        
        # If not found in memory, check the database
        if violation_id is None:
            try:
                # Look up the QR hash in the database
                qr_hash_obj = ViolatorQRHash.objects.filter(hash_id=hash_id).first()
                if qr_hash_obj:
                    # Find the violation linked to this QR hash
                    violation = Violation.objects.filter(qr_hash=qr_hash_obj).first()
                    if violation:
                        violation_id = violation.id
                        logger.info(f"Found violation ID {violation_id} in database for hash {hash_id}")
            except Exception as e:
                logger.error(f"Error looking up QR hash in database: {str(e)}")
        
        if violation_id is None:
            logger.warning(f"QR hash {hash_id} not found in memory or database")
            return JsonResponse({'error': 'Invalid or expired QR code'}, status=400)
        
        violation = get_object_or_404(Violation, id=violation_id)
        
        return JsonResponse({
            'violation_id': violation.id,
            'ticket_number': violation.ticket_number,
            'date_of_violation': violation.date_of_violation.strftime('%Y-%m-%d %H:%M'),
            'violation_type': violation.violation_type.name,
            'location': violation.location,
            'fine_amount': float(violation.violation_type.violation_fee),
            'status': violation.status
        })
    except Exception as e:
        logger.error(f"Error retrieving violation QR info: {str(e)}")
        return JsonResponse({'error': 'Error retrieving violation information'}, status=500)

def register_with_violations(request, hash_id=None):
    """
    View for users to register an account and link to existing violations.
    This is called from the QR code scan.
    """
    logger.info(f"Processing registration with violations for hash_id: {hash_id}")
    
    # Variables to keep track of what we've found
    violations_linked = []
    qr_hash = None
    
    # First, check if the hash_id exists and get associated violations
    try:
        if hash_id:
            # Try to get the QR hash record
            qr_hash = ViolatorQRHash.objects.get(hash_id=hash_id)
            logger.info(f"Found QR hash record for {hash_id}")
            
            # Check if it's already registered to a user account
            if qr_hash.registered and qr_hash.user_account:
                logger.warning(f"QR hash {hash_id} already registered to user {qr_hash.user_account.username}")
                messages.warning(
                    request, 
                    "This QR code has already been registered. Please log in to access your violations."
                )
                return redirect('login')
            
            # Get violations linked to this hash
            violations_linked = Violation.objects.filter(qr_hash=qr_hash)
            logger.info(f"Found {violations_linked.count()} violations linked to hash {hash_id}")
    except ViolatorQRHash.DoesNotExist:
        logger.error(f"QR hash {hash_id} not found")
        messages.error(request, "Invalid or expired QR code. Please contact the traffic enforcement office.")
        return redirect('login')
    except Exception as e:
        # Log the error and show a user-friendly message
        logger.error(f"Error checking QR hash {hash_id}: {str(e)}")
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('login')
    
    if not violations_linked:
        logger.error(f"No violations found for hash {hash_id}")
        messages.error(request, "Invalid or expired QR code. Please contact the traffic enforcement office.")
        return redirect('login')
        
    if request.method == 'POST':
        logger.info(f"Processing POST request for hash {hash_id}")
        form = ExtendedUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = None
                # Use a separate transaction for user creation and profile setup
                with transaction.atomic():
                    user = form.save()
                    
                    # Create or update user profile
                    # The UserProfile might already be created by a signal or other process
                    profile, created = UserProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'role': 'VIOLATOR',
                            'is_email_verified': False
                        }
                    )
                    
                    # Update profile with form data
                    license_number = form.cleaned_data.get('license_number')
                    logger.info(f"Form license number: {license_number}")
                    
                    # Standardize the license number (remove spaces, uppercase, etc.)
                    if license_number:
                        license_number = license_number.strip().upper().replace(' ', '')
                        logger.info(f"Standardized license number: {license_number}")
                    
                    # Set the license number if provided in the form
                    if license_number:
                        profile.license_number = license_number
                        logger.info(f"Setting profile license number to: {license_number}")
                    # If not in form but in QR hash, use that
                    elif qr_hash and qr_hash.license_number:
                        standardized_qr_license = qr_hash.license_number.strip().upper().replace(' ', '')
                        if standardized_qr_license:
                            profile.license_number = standardized_qr_license
                            logger.info(f"Using QR hash license number: {standardized_qr_license}")
                    
                    # Update other profile fields
                    if form.cleaned_data.get('address'):
                        profile.address = form.cleaned_data.get('address')
                    if form.cleaned_data.get('phone_number'):
                        profile.phone_number = form.cleaned_data.get('phone_number')
                    
                    # Save the updated profile
                    profile.save()
                    logger.info(f"Saved profile with license number: {profile.license_number}")
                    
                    # Log whether profile was created or updated
                    if created:
                        logger.info(f"Created new UserProfile for user {user.username}")
                    else:
                        logger.info(f"Updated existing UserProfile for user {user.username}")
                    
                    # Link all violations to the user
                    try:
                        if qr_hash or hash_id:
                            # If we don't have the qr_hash object yet, get it
                            if not qr_hash:
                                qr_hash = ViolatorQRHash.objects.get(hash_id=hash_id)
                            
                            # Find all violations associated with this QR hash
                            associated_violations = Violation.objects.filter(qr_hash=qr_hash)
                            linked_count = 0
                            
                            logger.info(f"Found {associated_violations.count()} violations to link to user {user.username}")
                            logger.info(f"User license number: {profile.license_number}")
                            
                            # Link all violations to the user
                            for v in associated_violations:
                                # Debug output to verify the violator's license number
                                violator_license = getattr(v.violator, 'license_number', 'None') if hasattr(v, 'violator') and v.violator else 'No violator'
                                logger.info(f"Violation ID {v.id} - Violator license: {violator_license}")
                                
                                # Link the user account directly to the violation
                                v.user_account = user
                                
                                # If the user has a license number and the violation has a violator,
                                # ensure the violator's license number matches the user's
                                if profile.license_number and hasattr(v, 'violator') and v.violator:
                                    # Standardize license numbers for comparison
                                    user_license = profile.license_number.strip().upper().replace(' ', '')
                                    violator_license_std = v.violator.license_number.strip().upper().replace(' ', '') if v.violator.license_number else None
                                    
                                    # Only update if different (using standardized comparison)
                                    if violator_license_std != user_license:
                                        logger.info(f"Updating violator's license number from {v.violator.license_number} to {profile.license_number} (Violation ID: {v.id})")
                                        v.violator.license_number = user_license
                                        v.violator.save(update_fields=['license_number'])
                                
                                # Save the violation with the updated user_account
                                v.save(update_fields=['user_account'])
                                linked_count += 1
                                logger.info(f"Linked violation ID {v.id} to user {user.username}")
                            
                            # Check for additional violations with the same violator info but not yet linked to a QR hash
                            if profile.license_number:
                                # Standardize the license number
                                std_license = profile.license_number.strip().upper().replace(' ', '')
                                
                                # Find violations with the same license number but not linked to this QR hash
                                additional_violations = Violation.objects.filter(
                                    violator__license_number__iexact=std_license,
                                    qr_hash__isnull=True,
                                    user_account__isnull=True  # Only get unlinked violations
                                )
                                
                                if additional_violations.exists():
                                    logger.info(f"Found {additional_violations.count()} additional violations with license {std_license} not linked to QR hash")
                                    
                                    for v in additional_violations:
                                        # Link to QR hash and user account
                                        v.qr_hash = qr_hash
                                        v.user_account = user
                                        v.save(update_fields=['qr_hash', 'user_account'])
                                        linked_count += 1
                                        logger.info(f"Linked additional violation ID {v.id} to user {user.username} and QR hash {qr_hash.hash_id}")
                            
                            # Check for violations with matching name but no license number
                            additional_name_violations = Violation.objects.filter(
                                violator__first_name__iexact=user.first_name,
                                violator__last_name__iexact=user.last_name,
                                qr_hash__isnull=True,
                                user_account__isnull=True  # Only get unlinked violations
                            )
                            
                            if additional_name_violations.exists():
                                logger.info(f"Found {additional_name_violations.count()} additional violations with name {user.first_name} {user.last_name} not linked to QR hash")
                                
                                for v in additional_name_violations:
                                    # Link to QR hash and user account
                                    v.qr_hash = qr_hash
                                    v.user_account = user
                                    v.save(update_fields=['qr_hash', 'user_account'])
                                    linked_count += 1
                                    logger.info(f"Linked additional violation ID {v.id} to user {user.username} and QR hash {qr_hash.hash_id}")
                            
                            # Double check that violations are now linked to the user
                            verification_count = Violation.objects.filter(user_account=user).count()
                            logger.info(f"Verification: User {user.username} now has {verification_count} violations linked to their account")
                            
                            logger.info(f"Successfully linked {linked_count} violations to user {user.username}")
                            
                            # Mark QR hash as registered
                            qr_hash.registered = True
                            qr_hash.user_account = user
                            qr_hash.save()
                            logger.info(f"Updated ViolatorQRHash {hash_id} to mark as registered for user {user.username}")
                        else:
                            # Fall back to linking just the current violation if no hash_id
                            if violations_linked:
                                violations_linked[0].user_account = user
                                violations_linked[0].save()
                                logger.info(f"Linked single violation ID {violations_linked[0].id} to user {user.username}")
                    except Exception as e:
                        logger.warning(f"Error linking violations to user: {str(e)}", exc_info=True)
                        
                        # Fall back to linking just the current violation if there was an error
                        if violations_linked:
                            # Check if this violation is already linked to another user
                            if violations_linked[0].user_account:
                                logger.warning(f"Violation ID {violations_linked[0].id} is already linked to user ID {violations_linked[0].user_account.id}")
                                
                                # Try to link to this user now
                                violations_linked[0].user_account = user
                                violations_linked[0].save()
                                logger.info(f"Fall back: Linked single violation ID {violations_linked[0].id} to user {user.username}")
                                
                                # Also update the violator's license number if needed
                                if profile.license_number and hasattr(violations_linked[0], 'violator') and violations_linked[0].violator:
                                    if violations_linked[0].violator.license_number != profile.license_number:
                                        logger.info(f"Updating violator's license number from {violations_linked[0].violator.license_number} to {profile.license_number}")
                                        violations_linked[0].violator.license_number = profile.license_number
                                        violations_linked[0].violator.save()
                        
                            # Try to additionally check if this user's license number matches any violations
                            # This is a backup in case the QR hash linking failed
                            if profile.license_number:
                                try:
                                    # Find violations with matching license number but no user account
                                    license_violations = Violation.objects.filter(
                                        violator__license_number=profile.license_number,
                                        user_account__isnull=True
                                    )
                                    
                                    if license_violations.exists():
                                        logger.info(f"Found {license_violations.count()} additional violations with license {profile.license_number}")
                                        for v in license_violations:
                                            v.user_account = user
                                            v.save()
                                            logger.info(f"Additionally linked violation ID {v.id} to user {user.username} by license number")
                                except Exception as license_error:
                                    logger.error(f"Error linking by license number: {str(license_error)}", exc_info=True)
                    
                    # After transaction completes, handle login in a separate step
                    if user:
                        try:
                            # Instead of using login() directly, authenticate first
                            authenticated_user = authenticate(
                                username=form.cleaned_data['username'],
                                password=form.cleaned_data['password1']
                            )
                            
                            if authenticated_user is not None:
                                # Use login with request argument
                                login(request, authenticated_user)
                                logger.info(f"User {authenticated_user.username} logged in successfully")
                                
                                messages.success(request, "Registration successful! The violation has been linked to your account.")
                                return redirect('user_portal:user_dashboard')
                            else:
                                logger.warning(f"Authentication failed after user creation for {user.username}")
                                messages.success(request, "Registration successful! Please log in with your new account.")
                                return redirect('login')
                        except Exception as login_error:
                            logger.error(f"Error during login process: {str(login_error)}", exc_info=True)
                            messages.success(request, "Registration successful! Please log in with your new account.")
                            return redirect('login')
                    else:
                        messages.error(request, "Registration failed. Please try again.")
            except Exception as e:
                logger.error(f"Error during registration: {str(e)}", exc_info=True)
                messages.error(request, "An error occurred during registration. Please try again.")
                # Add more specific error message for common issues
                if "Duplicate entry" in str(e) and "user_id" in str(e):
                    messages.error(request, "This username is already in use. Please try a different username.")
        else:
            logger.warning(f"Invalid form submission: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    logger.warning(f"Form error in {field}: {error}")
                    # Special handling for email errors to provide clearer feedback
                    if field == 'email' and "already registered" in error:
                        messages.warning(request, 
                            "This email address is already registered in our system. "
                            "If this is your account, please log in instead. "
                            "If you need help accessing your account, use the password reset feature."
                        )
                    else:
                        messages.error(request, f"{field.capitalize()}: {error}")
    else:
        logger.info(f"Generating registration form for hash {hash_id}")
        # Pre-fill form with violator details if available
        initial_data = {}
        
        # First check if we have data in the QR hash record
        if hash_id:
            try:
                if not qr_hash:
                    qr_hash = ViolatorQRHash.objects.get(hash_id=hash_id)
                initial_data = {
                    'first_name': qr_hash.first_name,
                    'last_name': qr_hash.last_name,
                    'license_number': qr_hash.license_number,
                    'phone_number': qr_hash.phone_number
                }
                # Add a placeholder username based on first and last name
                if qr_hash.first_name and qr_hash.last_name:
                    suggested_username = f"{qr_hash.first_name.lower()}.{qr_hash.last_name.lower()}"
                    initial_data['username'] = suggested_username
                    
                logger.info(f"Pre-filled form with data from QR hash record: {initial_data}")
            except Exception as e:
                logger.warning(f"Could not get QR hash record data: {str(e)}")
        
        # If we have a violation, use that data instead or complement existing data
        if violations_linked:
            # Try to get data from violator relationship
            try:
                if hasattr(violations_linked[0], 'violator') and violations_linked[0].violator:
                    violator_data = {
                        'first_name': violations_linked[0].violator.first_name,
                        'last_name': violations_linked[0].violator.last_name,
                        'license_number': getattr(violations_linked[0].violator, 'license_number', ''),
                        'phone_number': getattr(violations_linked[0].violator, 'phone_number', ''),
                        'address': getattr(violations_linked[0].violator, 'address', '')
                    }
                    
                    # Update initial data with violator data
                    initial_data.update(violator_data)
                    
                    # Add a placeholder username if not already set
                    if 'username' not in initial_data and violations_linked[0].violator.first_name and violations_linked[0].violator.last_name:
                        suggested_username = f"{violations_linked[0].violator.first_name.lower()}.{violations_linked[0].violator.last_name.lower()}"
                        initial_data['username'] = suggested_username
                        
                    logger.info(f"Updated form with data from violator relationship: {violator_data}")
                # If no violator relationship, try violation fields
                else:
                    # Extract first and last name from driver_name if available
                    first_name = getattr(violations_linked[0], 'first_name', '')
                    last_name = getattr(violations_linked[0], 'last_name', '')
                    
                    if not first_name and hasattr(violations_linked[0], 'driver_name') and violations_linked[0].driver_name:
                        name_parts = violations_linked[0].driver_name.split(' ', 1)
                        first_name = name_parts[0]
                        last_name = name_parts[1] if len(name_parts) > 1 else ''
                    
                    violation_data = {
                        'first_name': first_name,
                        'last_name': last_name,
                        'license_number': getattr(violations_linked[0], 'license_number', ''),
                        'phone_number': getattr(violations_linked[0], 'phone_number', ''),
                        'address': getattr(violations_linked[0], 'address', '')
                    }
                    
                    # Update initial data with violation data (only for empty fields)
                    for field, value in violation_data.items():
                        if not initial_data.get(field) and value:
                            initial_data[field] = value
                    
                    # Add a placeholder username if not already set
                    if 'username' not in initial_data and first_name and last_name:
                        suggested_username = f"{first_name.lower()}.{last_name.lower()}"
                        initial_data['username'] = suggested_username
                        
                    logger.info(f"Updated form with data from violation fields: {violation_data}")
            except Exception as e:
                logger.warning(f"Error getting violation field data: {str(e)}")
        
        # Create form with initial data
        form = ExtendedUserCreationForm(initial=initial_data)
        
        # Set CSS classes for all form fields
        for field_name, field in form.fields.items():
            field.widget.attrs['class'] = 'form-control'
    
    # Get violations associated with the hash
    violations_list = violations_linked
    logger.info(f"Rendering registration template with {len(violations_list)} violations")
    for v in violations_list:
        logger.info(f"Violation in context: ID={v.id}, Type={v.violation_type}, Amount={v.fine_amount}")
    
    # Log final context being sent to template
    logger.info(f"Template context: hash_id={hash_id}, violations_count={len(violations_list)}")
    
    return render(request, 'registration/register_with_violations.html', {
            'form': form,
        'violations': violations_list,
            'hash_id': hash_id
    })

def register_with_direct_violation(request, violation_id):
    """Register a new user with a direct violation ID."""
    logger.info(f"register_with_direct_violation called for violation ID: {violation_id}")
    
    # Get the violation
    try:
        violation = Violation.objects.get(pk=violation_id)
        logger.info(f"Found violation ID: {violation.id}, status: {violation.status}")
        
        # Check if this violation is already linked to a user account
        if violation.user_account:
            logger.warning(f"Violation {violation_id} is already linked to user: {violation.user_account.username}")
            messages.warning(request, 
                "This violation is already linked to an account. Please log in to that account, or contact support if you need assistance."
            )
            return redirect('login')
            
        # Check if the violation has a QR hash
        if violation.qr_hash:
            hash_id = violation.qr_hash.hash_id
            logger.info(f"Violation has QR hash: {hash_id}, registered: {violation.qr_hash.registered}")
            
            # Check if this QR hash is already registered
            if violation.qr_hash.registered:
                logger.warning(f"QR hash {hash_id} for violation {violation_id} is already registered")
                messages.warning(request, 
                    "This violation's QR code has already been registered. Please log in to view your violations, or contact support if you need assistance."
                )
                return redirect('login')
                
            # Check if this QR hash is linked to a user account
            if violation.qr_hash.user_account:
                logger.warning(f"QR hash {hash_id} for violation {violation_id} is already linked to user: {violation.qr_hash.user_account.username}")
                messages.warning(request, 
                    "This violation is already linked to an account. Please log in to that account, or contact support if you need assistance."
                )
                return redirect('login')
                
            # Check how many violations are linked to this QR hash
            linked_violations = list(violation.qr_hash.violations.all())
            violation_count = len(linked_violations)
            logger.info(f"QR hash {hash_id} has {violation_count} linked violations")
            
    except Violation.DoesNotExist:
        logger.warning(f"Violation not found: {violation_id}")
        messages.error(request, "Invalid violation ID. Please try again or contact support.")
        return redirect('login')
    except Exception as e:
        logger.error(f"Error checking violation {violation_id}: {str(e)}")
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('login') 
    
    # Use the hash_id to redirect to the register_with_violations view
    hash_id = violation.qr_hash.hash_id if violation.qr_hash else get_or_create_qr_hash(violation)
    logger.info(f"Redirecting to register_with_violations with hash: {hash_id}")
    return redirect('register_with_violations', hash_id=hash_id) 