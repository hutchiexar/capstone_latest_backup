import os
import logging
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)

def get_brevo_api_client():
    """Initialize and return the Brevo API client."""
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = os.environ.get('BREVO_API_KEY')
    return sib_api_v3_sdk.ApiClient(configuration)

def send_verification_email(user, token, request=None):
    """
    Send verification email to newly registered users.
    
    Args:
        user: User object
        token: EmailVerificationToken object
        request: HTTP request object (for building absolute URLs)
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Create API client instance
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(get_brevo_api_client())
        
        # Build verification URL
        if request:
            base_url = request.build_absolute_uri('/')[:-1]  # Remove trailing slash
            verification_link = f"{base_url}{reverse('verify_email', kwargs={'token': token.token})}"
        else:
            # Fallback if request is not available
            site_url = os.environ.get('SITE_URL', 'http://localhost:8000')
            verification_link = f"{site_url}{reverse('verify_email', kwargs={'token': token.token})}"
        
        # Get email expiration time (human readable)
        expiration_time = token.expires_at.strftime('%Y-%m-%d %H:%M:%S')
        hours_valid = 24  # Token validity in hours
        
        # Set up email content
        subject = "Verify Your CTTMO Traffic Violation Management System Account"
        sender = {"name": "CTTMO Support", "email": os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@cttmo.com')}
        
        # Email content with HTML
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eaeaea; border-radius: 5px;">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <h2 style="color: #0d6efd;">CTTMO Traffic Violation Management System</h2>
                    </div>
                    <p>Hello {user.first_name},</p>
                    <p>Thank you for registering with the CTTMO Traffic Violation Management System. To complete your registration and verify your email address, please click the button below:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{verification_link}" style="background-color: #0d6efd; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px; font-weight: bold;">Verify My Email</a>
                    </div>
                    <p>Alternatively, you can copy and paste the following link into your browser:</p>
                    <p style="word-break: break-all; background-color: #f5f5f5; padding: 10px; border-radius: 4px;">{verification_link}</p>
                    <p><strong>Please note:</strong> This verification link will expire in {hours_valid} hours (at {expiration_time}).</p>
                    <p>If you did not create an account, please disregard this email.</p>
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eaeaea; font-size: 12px; color: #666;">
                        <p>This is an automated message. Please do not reply to this email.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Plain text content as a fallback
        text_content = f"""
        Hello {user.first_name},
        
        Thank you for registering with the CTTMO Traffic Violation Management System. To complete your registration and verify your email address, please visit the following link:
        
        {verification_link}
        
        Please note: This verification link will expire in {hours_valid} hours (at {expiration_time}).
        
        If you did not create an account, please disregard this email.
        
        ---
        This is an automated message. Please do not reply to this email.
        """
        
        # Create SendSmtpEmail object
        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": user.email, "name": user.get_full_name()}],
            sender=sender,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
        
        # Send the email
        api_response = api_instance.send_transac_email(email)
        logger.info(f"Verification email sent successfully to {user.email}. Message ID: {api_response.message_id}")
        return True
    
    except ApiException as e:
        logger.error(f"Exception when sending verification email: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error when sending verification email: {e}")
        return False

def send_verification_reminder(user, token, request=None):
    """Send a reminder to verify email."""
    try:
        # Create API client instance
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(get_brevo_api_client())
        
        # Build verification URL
        if request:
            base_url = request.build_absolute_uri('/')[:-1]
            verification_link = f"{base_url}{reverse('verify_email', kwargs={'token': token.token})}"
        else:
            site_url = os.environ.get('SITE_URL', 'http://localhost:8000')
            verification_link = f"{site_url}{reverse('verify_email', kwargs={'token': token.token})}"
        
        # Get email expiration time
        expiration_time = token.expires_at.strftime('%Y-%m-%d %H:%M:%S')
        
        # Calculate hours remaining until expiration
        now = timezone.now()
        time_diff = token.expires_at - now
        hours_remaining = max(0, time_diff.total_seconds() / 3600)
        
        # Set up email content
        subject = "Reminder: Verify Your CTTMO Account"
        sender = {"name": "CTTMO Support", "email": os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@cttmo.com')}
        
        # Email content with HTML
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eaeaea; border-radius: 5px;">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <h2 style="color: #0d6efd;">CTTMO Traffic Violation Management System</h2>
                    </div>
                    <p>Hello {user.first_name},</p>
                    <p>This is a friendly reminder that you still need to verify your email address for your CTTMO account. To complete your registration, please click the button below:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{verification_link}" style="background-color: #0d6efd; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px; font-weight: bold;">Verify My Email</a>
                    </div>
                    <p>Alternatively, you can copy and paste the following link into your browser:</p>
                    <p style="word-break: break-all; background-color: #f5f5f5; padding: 10px; border-radius: 4px;">{verification_link}</p>
                    <p><strong>Please note:</strong> This verification link will expire in {int(hours_remaining)} hours (at {expiration_time}).</p>
                    <p>If you did not create an account, please disregard this email.</p>
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eaeaea; font-size: 12px; color: #666;">
                        <p>This is an automated message. Please do not reply to this email.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Plain text content as a fallback
        text_content = f"""
        Hello {user.first_name},
        
        This is a friendly reminder that you still need to verify your email address for your CTTMO account. To complete your registration, please visit the following link:
        
        {verification_link}
        
        Please note: This verification link will expire in {int(hours_remaining)} hours (at {expiration_time}).
        
        If you did not create an account, please disregard this email.
        
        ---
        This is an automated message. Please do not reply to this email.
        """
        
        # Create SendSmtpEmail object
        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": user.email, "name": user.get_full_name()}],
            sender=sender,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
        
        # Send the email
        api_response = api_instance.send_transac_email(email)
        logger.info(f"Verification reminder sent successfully to {user.email}. Message ID: {api_response.message_id}")
        return True
    
    except ApiException as e:
        logger.error(f"Exception when sending verification reminder: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error when sending verification reminder: {e}")
        return False 