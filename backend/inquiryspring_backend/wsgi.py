"""
WSGI config for InquirySpring Backend.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inquiryspring_backend.settings')

application = get_wsgi_application()
