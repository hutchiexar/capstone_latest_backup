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
from traffic_violation_system.models import EmailVerificationToken
from traffic_violation_system.utils.email_utils import send_verification_email

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_email_sending():
    """Test email sending functionality with the Brevo API"""
    
    # Print environment variables for debugging
    logger.info(f"BREVO_API_KEY: {os.environ.get('BREVO_API_KEY', 'Not set')[:10]}...")
    logger.info(f"DEFAULT_FROM_EMAIL: {os.environ.get('DEFAULT_FROM_EMAIL', 'Not set')}")
    logger.info(f"SITE_URL: {os.environ.get('SITE_URL', 'Not set')}")
    
    try:
        # Use the first user in the database or create a test user
        user = User.objects.first()
        
        if not user:
            logger.info("No users found in the database. Creating a test user.")
            user = User.objects.create_user(
                username="testuser",
                email="test@example.com",
                first_name="Test",
                last_name="User",
                password="password123"
            )
        
        logger.info(f"Using user: {user.username} ({user.email})")
        
        # Create a test token
        token = EmailVerificationToken.objects.create(
            user=user,
            token=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        logger.info(f"Created token: {token.token}")
        
        # Send test email
        result = send_verification_email(user, token)
        
        if result:
            logger.info("✅ Email sent successfully!")
        else:
            logger.error("❌ Failed to send email.")
        
        # Clean up - delete the token
        token.delete()
        
        return result
        
    except Exception as e:
        logger.error(f"Error in test_email_sending: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting email test...")
    success = test_email_sending()
    sys.exit(0 if success else 1) 