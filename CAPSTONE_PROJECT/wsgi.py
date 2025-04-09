"""
WSGI config for CAPSTONE_PROJECT project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Check if we're running on Render.com
if 'RENDER' in os.environ:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CAPSTONE_PROJECT.render_settings")
else:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CAPSTONE_PROJECT.settings")

application = get_wsgi_application()
