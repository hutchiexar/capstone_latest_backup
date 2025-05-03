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
    Send verification email with one-time code to newly registered users.
    
    Args:
        user: User object
        token: EmailVerificationToken object with verification_code
        request: HTTP request object (for building absolute URLs)
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Log API key status (masked for security)
        api_key = os.environ.get('BREVO_API_KEY', '')
        if not api_key:
            logger.error("BREVO_API_KEY not found in environment variables")
            return False
        
        masked_key = f"{api_key[:5]}...{api_key[-5:]}" if len(api_key) > 10 else "***"
        logger.info(f"Using Brevo API Key: {masked_key}")
        
        # Create API client instance
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(get_brevo_api_client())
        
        # Get verification code
        verification_code = token.verification_code
        
        # Get email expiration time (human readable)
        expiration_time = token.expires_at.strftime('%Y-%m-%d %H:%M:%S')
        hours_valid = 24  # Token validity in hours
        
        # Set up email content
        subject = "Verify Your CTTMO Traffic Violation Management System Account"
        sender = {"name": "CTTMO Support", "email": os.environ.get('DEFAULT_FROM_EMAIL', 'hutchiejn@gmail.com')}
        
        # Email content with HTML
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eaeaea; border-radius: 5px;">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <h2 style="color: #0d6efd;">CTTMO Traffic Violation Management System</h2>
                    </div>
                    <p>Hello {user.first_name},</p>
                    <p>Thank you for registering with the CTTMO Traffic Violation Management System. To complete your registration and verify your email address, please use the verification code below:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <div style="font-size: 28px; letter-spacing: 5px; font-weight: bold; background-color: #f5f5f5; padding: 15px; border-radius: 4px; display: inline-block;">{verification_code}</div>
                    </div>
                    <p><strong>Please note:</strong> This verification code will expire in {hours_valid} hours (at {expiration_time}).</p>
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
        
        Thank you for registering with the CTTMO Traffic Violation Management System. To complete your registration and verify your email address, please use the following verification code:
        
        {verification_code}
        
        Please note: This verification code will expire in {hours_valid} hours (at {expiration_time}).
        
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
    """Send a reminder to verify email with verification code."""
    try:
        # Create API client instance
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(get_brevo_api_client())
        
        # Get verification code
        verification_code = token.verification_code
        
        # Get email expiration time
        expiration_time = token.expires_at.strftime('%Y-%m-%d %H:%M:%S')
        
        # Calculate hours remaining until expiration
        now = timezone.now()
        time_diff = token.expires_at - now
        hours_remaining = max(0, time_diff.total_seconds() / 3600)
        
        # Set up email content
        subject = "Reminder: Verify Your CTTMO Account"
        sender = {"name": "CTTMO Support", "email": os.environ.get('DEFAULT_FROM_EMAIL', 'hutchiejn@gmail.com')}
        
        # Email content with HTML
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eaeaea; border-radius: 5px;">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <h2 style="color: #0d6efd;">CTTMO Traffic Violation Management System</h2>
                    </div>
                    <p>Hello {user.first_name},</p>
                    <p>This is a friendly reminder that you still need to verify your email address for your CTTMO account. To complete your registration, please use the verification code below:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <div style="font-size: 28px; letter-spacing: 5px; font-weight: bold; background-color: #f5f5f5; padding: 15px; border-radius: 4px; display: inline-block;">{verification_code}</div>
                    </div>
                    <p><strong>Please note:</strong> This verification code will expire in {int(hours_remaining)} hours (at {expiration_time}).</p>
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
        
        This is a friendly reminder that you still need to verify your email address for your CTTMO account. To complete your registration, please use the following verification code:
        
        {verification_code}
        
        Please note: This verification code will expire in {int(hours_remaining)} hours (at {expiration_time}).
        
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