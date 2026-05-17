"""
Development settings for tms_project.
These settings are optimized for local development with more verbose logging and debugging tools.
"""

from .base import *

# Debug mode enabled for development
DEBUG = True

# Allow all hosts in development (make it easier to test)
ALLOWED_HOSTS = ["*"]

# Database - Development can use SQLite for quick testing (optional)
# Uncomment to use SQLite instead of PostgreSQL in development:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# CORS - Restrict to Angular dev server origins only (fixes ZAP Cross-Domain Misconfiguration)
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]

# CSP - Allow unsafe-eval in development for Angular JIT compilation
CONTENT_SECURITY_POLICY["DIRECTIVES"]["script-src"] = (
    "'self'",
    "'unsafe-inline'",
    "'unsafe-eval'",
)
CONTENT_SECURITY_POLICY["DIRECTIVES"]["script-src-elem"] = (
    "'self'",
    "'unsafe-inline'",
    "'unsafe-eval'",
)

# CSP - Allow connections to localhost for API calls in development
CONTENT_SECURITY_POLICY["DIRECTIVES"]["connect-src"] = (
    "'self'",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "ws://localhost:8000",
    "ws://127.0.0.1:8000",
)

# Email - Use console backend in development (prints emails to console)
# Uncomment to print emails to console instead of sending them:
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable rate limiting in development so test/form submissions are never blocked
RATELIMIT_ENABLE = False

# Security settings - Relaxed for development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Django Debug Toolbar (if installed)
if "debug_toolbar" in INSTALLED_APPS:
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INTERNAL_IPS = ["127.0.0.1", "localhost"]

# Clean application logging (configured in base.py)
# LOGGING configuration now in base.py - only shows application logs, not Django framework noise

print("[DEV] Development settings loaded")
print(f"  - DEBUG: {DEBUG}")
print(
    f"  - DATABASE: {DATABASES['default']['ENGINE']} - {DATABASES['default']['NAME']}"
)
print(f"  - EMAIL_BACKEND: {EMAIL_BACKEND}")
