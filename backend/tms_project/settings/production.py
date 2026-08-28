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

# CSP - Restrict connections to production backend URL
# Configure CSP_BACKEND_URL in environment variables to match your production backend
CSP_BACKEND_URL = config('CSP_BACKEND_URL', default='https://api.yourdomain.com')
CONTENT_SECURITY_POLICY['DIRECTIVES']['connect-src'] = (
    "'self'",
    CSP_BACKEND_URL,
    f"wss://{CSP_BACKEND_URL.replace('https://', '')}"
)

# HSTS (HTTP Strict Transport Security) - Production only
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=True, cast=bool)

# Database connection pooling (recommended for production)
DATABASES['default']['CONN_MAX_AGE'] = config('DB_CONN_MAX_AGE', default=600, cast=int)  # 10 minutes
DATABASES['default']['OPTIONS'] = {
    'connect_timeout': 10,
}

# Caching — Redis (shared with Celery broker, separate DB index)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
        },
        'KEY_PREFIX': 'tms',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Session configuration - Use cache in production
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# MinIO / S3-compatible object storage for media files
AWS_ACCESS_KEY_ID = config('MINIO_ACCESS_KEY', default='')
AWS_SECRET_ACCESS_KEY = config('MINIO_SECRET_KEY', default='')
AWS_STORAGE_BUCKET_NAME = config('MINIO_BUCKET_NAME', default='tms-media')
AWS_S3_ENDPOINT_URL = config('MINIO_ENDPOINT_URL', default='http://127.0.0.1:9000')
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = 'public-read'
AWS_QUERYSTRING_AUTH = False  # Serve files via clean public URLs
AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}

# Public URL base: nginx proxies /<bucket>/ → MinIO
AWS_S3_CUSTOM_DOMAIN = f"{config('MINIO_PUBLIC_DOMAIN')}/{AWS_STORAGE_BUCKET_NAME}"
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"

# Django 5.x+ uses STORAGES instead of deprecated STATICFILES_STORAGE
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Production logging - Log to file with rotation
# Add verbose formatter for production
LOGGING['formatters']['verbose'] = {
    'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
    'style': '{',
}

# Configure log directory (create via deployment script)
import os
LOG_DIR = config('LOG_DIR', default='/var/log/tms')

LOGGING['handlers']['production_file'] = {
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': os.path.join(LOG_DIR, 'django.log'),
    'maxBytes': 1024 * 1024 * 10,  # 10 MB
    'backupCount': 10,
    'formatter': 'verbose',
}

LOGGING['handlers']['error_file'] = {
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': os.path.join(LOG_DIR, 'django_errors.log'),
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
RATELIMIT_IP_META_KEY = config('RATELIMIT_IP_META_KEY', default='HTTP_X_FORWARDED_FOR')

print("🚀 Production settings loaded")
print(f"  - DEBUG: {DEBUG}")
print(f"  - SECURE_SSL_REDIRECT: {SECURE_SSL_REDIRECT}")
print(f"  - DATABASE: {DATABASES['default']['ENGINE']}")
