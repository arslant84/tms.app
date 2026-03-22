"""
Django base settings for tms_project.
These settings are common across all environments (development, staging, production).
Environment-specific settings should be in development.py or production.py.
"""

from pathlib import Path
import os
from datetime import timedelta
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',  # JWT authentication
    'rest_framework_simplejwt.token_blacklist',  # Token blacklist for logout
    'corsheaders',
    'csp',  # Content Security Policy
    'drf_spectacular',  # OpenAPI schema generation

    # Custom apps
    'accounts',
    'trf',
    'bookings',
    'insights',
    'visa',
    'accommodation',
    'transport',
    'workflows',
    'notifications',
    'reports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'csp.middleware.CSPMiddleware',  # Content Security Policy - add early for security
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Custom middleware for dynamic settings
    'tms_project.middleware.MaintenanceModeMiddleware',
    'tms_project.middleware.SessionTimeoutMiddleware',
    'tms_project.middleware.FileSizeValidationMiddleware',
    'tms_project.middleware.DynamicSettingsMiddleware',
]

ROOT_URLCONF = 'tms_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'tms_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': config('DB_NAME', default='tms'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 15,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # Where collectstatic will collect files

# Additional locations of static files (if you have app-specific static folders)
STATICFILES_DIRS = [
    # os.path.join(BASE_DIR, 'static'),  # Uncomment if you have a project-level static folder
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # SECURITY: JWT cookie authentication with token expiration (prevents XSS + session hijacking)
        'accounts.jwt_cookie_auth.JWTCookieAuthentication',
        # Fallback to legacy token auth for backward compatibility during migration
        'accounts.cookie_auth.CookieTokenAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,  # Items per page
    # OpenAPI schema generation with drf-spectacular
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# DRF Spectacular Settings (OpenAPI Documentation)
SPECTACULAR_SETTINGS = {
    'TITLE': 'TMS API',
    'DESCRIPTION': '''
## Travel Management System API

A comprehensive API for managing travel requests, bookings, approvals, and more.

### Features
- **Travel Requests (TRF/TSR)**: Create, submit, approve, and track travel requests
- **Bookings**: Flight and hotel booking management
- **Approvals**: Unified approval workflow across all request types
- **Visa Applications**: Manage visa application processes
- **Transport**: Transport request management
- **Accommodation**: Accommodation booking requests
- **Reports**: Comprehensive reporting and analytics
- **Notifications**: Real-time notification system

### Authentication
All endpoints require authentication via JWT tokens stored in HttpOnly cookies.
Login via `/api/login/` to obtain authentication cookies.

### Response Format
All responses follow a standardized format:
```json
{
    "success": true/false,
    "message": "Human-readable message",
    "data": {...},
    "meta": {
        "timestamp": "ISO datetime",
        "pagination": {...}
    }
}
```
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': False,
        'filter': True,
    },
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': False,
    'TAGS': [
        {'name': 'Authentication', 'description': 'User authentication and session management'},
        {'name': 'Users', 'description': 'User management operations'},
        {'name': 'Travel Requests', 'description': 'TRF/TSR travel request management'},
        {'name': 'Bookings', 'description': 'Flight and hotel booking operations'},
        {'name': 'Approvals', 'description': 'Unified approval workflow'},
        {'name': 'Visa', 'description': 'Visa application management'},
        {'name': 'Transport', 'description': 'Transport request operations'},
        {'name': 'Accommodation', 'description': 'Accommodation booking requests'},
        {'name': 'Reports', 'description': 'Reporting and analytics'},
        {'name': 'Notifications', 'description': 'Notification management'},
        {'name': 'Insights', 'description': 'Dashboard and analytics data'},
        {'name': 'Workflows', 'description': 'Workflow template management'},
    ],
}

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# CORS settings
CORS_ALLOW_ALL_ORIGINS = False  # SECURITY: Restricted to specific origins
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:4200,http://127.0.0.1:4200', cast=Csv())
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Email configuration - Brevo SMTP (configured via environment variables)
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp-relay.brevo.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='SynTra TMS <noreply@pctsb-travel.site>')
EMAIL_TIMEOUT = 10  # seconds

# Frontend URL for email links
# This is used to generate absolute URLs in email notifications
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:4200')

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Content Security Policy (CSP) - django-csp 3.7+ format
# SECURITY: Prevents XSS attacks by controlling which resources can be loaded
# Note: 'unsafe-inline' and 'unsafe-eval' are needed for Angular during development
# In production, consider using nonces or hashes for stricter CSP
CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'default-src': ("'self'",),
        'script-src': ("'self'", "'unsafe-inline'", "'unsafe-eval'"),  # Angular requires inline scripts
        'style-src': ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com"),  # Allow Google Fonts CSS
        'style-src-elem': ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com"),  # Allow external stylesheets
        'img-src': ("'self'", "data:", "https:"),  # Allow images from same origin, data URIs, and HTTPS
        'font-src': ("'self'", "data:", "https://fonts.gstatic.com"),  # Allow Google Fonts
        'connect-src': ("'self'",),  # API calls - will be extended in development.py
        'frame-ancestors': ("'none'",),  # Don't allow this site to be framed
        'base-uri': ("'self'",),  # Restrict base tag to prevent base tag injection
        'form-action': ("'self'",),  # Forms can only submit to same origin
        'object-src': ("'none'",),  # Block plugins like Flash
        'media-src': ("'self'",),  # Audio and video from same origin
        'frame-src': ("'self'",),  # Allow iframes from same origin
        'worker-src': ("'self'",),  # Web workers from same origin
        'manifest-src': ("'self'",),  # Web app manifest from same origin
    }
}

# CSP Reporting (optional - uncomment to enable violation reports)
# CONTENT_SECURITY_POLICY['REPORT_URI'] = '/csp-report/'
# CONTENT_SECURITY_POLICY['REPORT_ONLY'] = False  # Set to True to test CSP without enforcing

# CSRF Protection for cookie-based authentication
# Allow CSRF cookie to be sent from frontend
CSRF_COOKIE_HTTPONLY = False  # Frontend needs to read this for CSRF token
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = True  # Only send over HTTPS in production
CSRF_COOKIE_NAME = 'csrftoken'
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='http://localhost:4200,http://127.0.0.1:4200', cast=Csv())

# JWT Settings (Simple JWT)
# SECURITY: Tokens with expiration and rotation
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),  # Access token expires in 1 hour
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),  # Refresh token expires in 7 days
    'ROTATE_REFRESH_TOKENS': True,  # Generate new refresh token on refresh
    'BLACKLIST_AFTER_ROTATION': True,  # Blacklist old refresh tokens
    'UPDATE_LAST_LOGIN': True,  # Update last_login on token generation

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# Logging Configuration
# Clean, readable logs for development - ONLY application logs
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'app': {
            'format': '\033[1m{levelname}\033[0m {asctime} \033[36m{name}\033[0m {message}',
            'style': '{',
            'datefmt': '%H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'app',
            'level': 'INFO',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',  # Only show warnings and errors from unlisted loggers
    },
    'loggers': {
        # Silence Django framework logs completely
        'django': {
            'handlers': [],
            'level': 'ERROR',  # Only show errors
            'propagate': False,
        },
        'django.utils.autoreload': {
            'handlers': [],
            'level': 'ERROR',  # Completely suppress autoreload logs
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': [],
            'level': 'ERROR',  # No SQL logs
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'WARNING',  # Only show HTTP errors, not every request
            'propagate': False,
        },
        'django.template': {
            'handlers': [],
            'level': 'ERROR',
            'propagate': False,
        },
        # Application loggers - show all activity
        'accounts': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'approvals': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'workflows': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'trf': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'bookings': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'transport': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'insights': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'notifications': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'visa': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'accommodation': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
