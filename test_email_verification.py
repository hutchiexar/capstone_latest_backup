import os
import sys
import django
import logging
import uuid
from datetime import datetime, timedelta

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CAPSTONE_PROJECT.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from traffic_violation_system.models import EmailVerificationToken, UserProfile
from traffic_violation_system.utils.email_utils import send_verification_email

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_email_verification_code():
    """Test email verification code sending functionality with the Brevo API"""
    
    # Print environment variables for debugging
    api_key = os.environ.get('BREVO_API_KEY', '')
    masked_key = f"{api_key[:5]}...{api_key[-5:]}" if len(api_key) > 10 else "***"
    logger.info(f"BREVO_API_KEY: {masked_key}")
    logger.info(f"DEFAULT_FROM_EMAIL: {os.environ.get('DEFAULT_FROM_EMAIL', 'Not set')}")
    logger.info(f"SITE_URL: {os.environ.get('SITE_URL', 'Not set')}")
    
    test_email = input("Enter test email address: ")
    if not test_email:
        logger.error("Email address is required")
        return False
    
    try:
        # Check if a test user with this email already exists
        try:
            user = User.objects.get(email=test_email)
            logger.info(f"Using existing user: {user.username} ({user.email})")
        except User.DoesNotExist:
            # Create a test user
            username = f"testuser_{uuid.uuid4().hex[:8]}"
            user = User.objects.create_user(
                username=username,
                email=test_email,
                first_name="Test",
                last_name="User",
                password="password123"
            )
            logger.info(f"Created test user: {user.username} ({user.email})")
            
            # Create user profile if it doesn't exist
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'phone_number': '1234567890',
                    'address': 'Test Address',
                    'role': 'USER',
                    'is_email_verified': False
                }
            )
        
        # Delete any existing tokens for this user
        EmailVerificationToken.objects.filter(user=user).delete()
        
        # Create a test token
        token = EmailVerificationToken.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        logger.info(f"Created token with verification code: {token.verification_code}")
        
        # Send test email
        result = send_verification_email(user, token)
        
        if result:
            logger.info("✅ Email with verification code sent successfully!")
            logger.info(f"The verification code is: {token.verification_code}")
        else:
            logger.error("❌ Failed to send email with verification code.")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in test_email_verification_code: {str(e)}")
        return False

if __name__ == '__main__':
    print("Testing email verification code delivery...")
    success = test_email_verification_code()
    sys.exit(0 if success else 1) 