import os
from pathlib import Path
from .settings import *

# SECURITY WARNING: don't run with debug turned on in production!
# Set DEBUG to True temporarily to see error details
DEBUG = True

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
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Configure WhiteNoise for static files
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Add error logging middleware
MIDDLEWARE.append('traffic_violation_system.middleware.ErrorLoggingMiddleware')

STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Make sure media files are served correctly
DEFAULT_FILE_STORAGE = 'traffic_violation_system.storage.RenderMediaStorage'

# Disable security settings for initial testing
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Enhanced logging for debugging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'traffic_violation_system': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
} 