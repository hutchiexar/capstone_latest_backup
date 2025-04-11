import os
from pathlib import Path
from .settings import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Update secret key from environment
SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-secret-key-for-build-not-for-production')

# Allow all hostnames from Render
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '.onrender.com,localhost').split(',')

# Use SQLite for initial deployment testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Static and Media files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# On Render, we need to use a persistent directory for media files
# This is because the dyno filesystem is ephemeral
MEDIA_URL = '/media/'
# Use a persistent directory on Render
if os.environ.get('RENDER', 'False') == 'True':
    # Render provides a persistent disk at /opt/render/project/src/
    MEDIA_ROOT = os.path.join('/opt/render/project/src/', 'media')
else:
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Configure WhiteNoise for static files
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Make sure media files are served correctly
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Disable security settings for initial testing
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Set up logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        '': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
} 