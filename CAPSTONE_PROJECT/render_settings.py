import os
import dj_database_url
from .settings import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Update secret key from environment
SECRET_KEY = os.environ.get('SECRET_KEY')

# Allow all hostnames from Render
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '.onrender.com').split(',')

# Configure database using DATABASE_URL environment variable
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
    )
}

# Static and Media files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/'
# Use Render disk for media files
if 'RENDER' in os.environ:
    MEDIA_ROOT = '/opt/render/project/src/media'
else:
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Configure WhiteNoise for static files
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

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
            'level': os.getenv('DJANGO_LOG_LEVEL', 'ERROR'),
        },
    },
} 