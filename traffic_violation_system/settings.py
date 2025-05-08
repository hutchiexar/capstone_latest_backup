from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Hard-coded values are now fallbacks in case environment variables aren't set
# Always prefer to use environment variables for sensitive data
BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'hutchiejn@gmail.com')
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')

# Email verification settings
EMAIL_VERIFICATION_REQUIRED = True
EMAIL_VERIFICATION_TIMEOUT_HOURS = int(os.environ.get('EMAIL_VERIFICATION_TIMEOUT_HOURS', 24))
EMAIL_VERIFICATION_CODE_LENGTH = int(os.environ.get('EMAIL_VERIFICATION_CODE_LENGTH', 6))

# File Storage
DEFAULT_FILE_STORAGE = 'traffic_violation_system.storage.SafeFileStorage'

# Maximum filename length
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB limit 