from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Brevo API settings
BREVO_API_KEY = ''
DEFAULT_FROM_EMAIL = 'hutchiexar@gmail.com'
SITE_URL = 'http://192.168.1.4:8004'

# Email verification settings
EMAIL_VERIFICATION_REQUIRED = True
EMAIL_VERIFICATION_TIMEOUT_HOURS = 24  # Token expiration in hours

# File Storage
DEFAULT_FILE_STORAGE = 'traffic_violation_system.storage.SafeFileStorage'

# Maximum filename length
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB limit 