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

# Use the SafeFileStorage for better file handling
DEFAULT_FILE_STORAGE = 'traffic_violation_system.storage.SafeFileStorage'

# Disable security settings for initial testing
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Set up logging with more detailed file logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join('/opt/render/project/src/', 'app.log') if os.environ.get('RENDER', 'False') == 'True' else os.path.join(BASE_DIR, 'app.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'traffic_violation_system': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    },
} 