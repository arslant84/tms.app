"""
Development settings for tms_project.
These settings are optimized for local development with more verbose logging and debugging tools.
"""

from .base import *

# Debug mode enabled for development
DEBUG = True

# Allow all hosts in development (make it easier to test)
ALLOWED_HOSTS = ['*']

# Database - Development can use SQLite for quick testing (optional)
# Uncomment to use SQLite instead of PostgreSQL in development:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# CORS - Allow all origins in development for easier testing
CORS_ALLOW_ALL_ORIGINS = True

# CSP - Allow connections to localhost for API calls in development
CSP_CONNECT_SRC = ("'self'", "http://localhost:8000", "http://127.0.0.1:8000", "ws://localhost:8000", "ws://127.0.0.1:8000")

# Email - Use console backend in development (prints emails to console)
# Uncomment to print emails to console instead of sending them:
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Security settings - Relaxed for development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Django Debug Toolbar (if installed)
if 'debug_toolbar' in INSTALLED_APPS:
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1', 'localhost']

# More verbose logging in development
LOGGING['root']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'DEBUG'
LOGGING['loggers']['workflows']['level'] = 'DEBUG'
LOGGING['loggers']['notifications']['level'] = 'DEBUG'

# Add file handler for development debugging
LOGGING['handlers']['file'] = {
    'class': 'logging.FileHandler',
    'filename': BASE_DIR / 'logs' / 'debug.log',
    'formatter': 'verbose',
}
LOGGING['root']['handlers'].append('file')

# Create logs directory if it doesn't exist
import os
logs_dir = BASE_DIR / 'logs'
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

print("🔧 Development settings loaded")
print(f"  - DEBUG: {DEBUG}")
print(f"  - DATABASE: {DATABASES['default']['ENGINE']} - {DATABASES['default']['NAME']}")
print(f"  - EMAIL_BACKEND: {EMAIL_BACKEND}")
