"""
Production settings for tms_project.
These settings are optimized for production deployment with enhanced security and performance.
"""

from .base import *

# Debug mode disabled in production
DEBUG = False

# Strict allowed hosts in production
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

# Security settings - Strict for production
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)

# HSTS (HTTP Strict Transport Security) - Production only
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=True, cast=bool)

# Database connection pooling (recommended for production)
DATABASES['default']['CONN_MAX_AGE'] = config('DB_CONN_MAX_AGE', default=600, cast=int)  # 10 minutes
DATABASES['default']['OPTIONS'] = {
    'connect_timeout': 10,
}

# Caching configuration - Redis (recommended for production)
# Uncomment and configure when Redis is available:
# CACHES = {
#     'default': {
#         'BACKEND': 'django_redis.cache.RedisCache',
#         'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#             'SOCKET_CONNECT_TIMEOUT': 5,
#             'SOCKET_TIMEOUT': 5,
#             'CONNECTION_POOL_KWARGS': {
#                 'max_connections': 50,
#                 'retry_on_timeout': True,
#             },
#         },
#         'KEY_PREFIX': 'tms',
#         'TIMEOUT': 300,  # 5 minutes default
#     }
# }

# Session configuration - Use cache in production
# SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
# SESSION_CACHE_ALIAS = 'default'

# Static files - Use WhiteNoise for static file serving
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Production logging - Log to file with rotation
LOGGING['handlers']['production_file'] = {
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': '/var/log/tms/django.log',  # Adjust path as needed
    'maxBytes': 1024 * 1024 * 10,  # 10 MB
    'backupCount': 10,
    'formatter': 'verbose',
}

LOGGING['handlers']['error_file'] = {
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': '/var/log/tms/django_errors.log',  # Adjust path as needed
    'maxBytes': 1024 * 1024 * 10,  # 10 MB
    'backupCount': 10,
    'formatter': 'verbose',
    'level': 'ERROR',
}

LOGGING['root']['handlers'] = ['console', 'production_file', 'error_file']
LOGGING['root']['level'] = 'INFO'

# Error monitoring - Sentry (uncomment and configure when available)
# if config('SENTRY_DSN', default=None):
#     import sentry_sdk
#     from sentry_sdk.integrations.django import DjangoIntegration
#
#     sentry_sdk.init(
#         dsn=config('SENTRY_DSN'),
#         integrations=[DjangoIntegration()],
#         traces_sample_rate=0.1,
#         send_default_pii=False,
#         environment='production',
#     )

# Admin security - Restrict admin access
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Rate limiting (if django-ratelimit is installed)
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

print("🚀 Production settings loaded")
print(f"  - DEBUG: {DEBUG}")
print(f"  - SECURE_SSL_REDIRECT: {SECURE_SSL_REDIRECT}")
print(f"  - DATABASE: {DATABASES['default']['ENGINE']}")
