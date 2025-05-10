from django.http import JsonResponse
from django.contrib.auth.models import User
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.forms import PasswordResetForm
from django.template import loader
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

@csrf_exempt
@require_GET
def get_email_by_username(request):
    """
    Returns the email address for a given username if it exists.
    Used for pre-filling the email field on password reset form.
    """
    username = request.GET.get('username', '')
    response = {'email': ''}
    
    if username:
        # First try an exact match with the username
        try:
            user = User.objects.get(username=username)
            response['email'] = user.email
        except User.DoesNotExist:
            # If username doesn't exist, try to see if it's an email address itself
            if '@' in username:
                try:
                    user = User.objects.get(email=username)
                    response['email'] = user.email
                except User.DoesNotExist:
                    pass
    
    return JsonResponse(response)

class BrevoPasswordResetForm(PasswordResetForm):
    """Custom PasswordResetForm that sends emails using Brevo API"""
    
    def get_brevo_api_client(self):
        """Initialize and return the Brevo API client."""
        # Try to get API key from environment first, then settings
        api_key = os.environ.get('BREVO_API_KEY')
        
        # If not in environment, try the settings file
        if not api_key:
            # Get from traffic_violation_system.settings first, which has the hardcoded fallback
            try:
                from traffic_violation_system.settings import BREVO_API_KEY as TVS_KEY
                api_key = TVS_KEY
                logger.info("Using API key from traffic_violation_system.settings")
            except ImportError:
                logger.warning("Could not import traffic_violation_system.settings")
            
            # If still not found, try main settings
            if not api_key:
                api_key = getattr(settings, 'BREVO_API_KEY', '')
                logger.info("Using API key from main settings")
            
        if not api_key:
            logger.error("BREVO_API_KEY not found in environment or settings")
            raise ValueError("BREVO_API_KEY not set")
        
        # Log a masked version for debugging
        masked_key = f"{api_key[:5]}...{api_key[-5:]}" if len(api_key) > 10 else "***" 
        logger.info(f"Configured Brevo API Key: {masked_key}")
        
        # Set up configuration
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = api_key
        return sib_api_v3_sdk.ApiClient(configuration)
    
    def send_mail(self, subject_template_name, email_template_name,
                 context, from_email, to_email, html_email_template_name=None):
        """
        Override the send_mail method to use Brevo API instead of SMTP
        """
        # Get the subject
        subject = loader.render_to_string(subject_template_name, context)
        # Email subject must not contain newlines
        subject = ''.join(subject.splitlines())
        
        # Get the plain text body
        body = loader.render_to_string(email_template_name, context)
        
        # Get the HTML body
        if html_email_template_name:
            html_body = loader.render_to_string(html_email_template_name, context)
        else:
            html_body = body

        # Send email using Brevo API
        try:
            # Create API client instance
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(self.get_brevo_api_client())
            
            # Set up sender
            sender = {"name": "CTTMO Support", "email": from_email}
            
            # Create SendSmtpEmail object
            email = sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": to_email}],
                sender=sender,
                subject=subject,
                html_content=html_body,
                text_content=body
            )
            
            # Send the email
            api_response = api_instance.send_transac_email(email)
            logger.info(f"Password reset email sent successfully to {to_email}. Message ID: {api_response.message_id}")
            return True
            
        except ApiException as e:
            logger.error(f"Exception when sending password reset email: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error when sending password reset email: {e}")
            return False 