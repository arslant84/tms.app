"""
Custom middleware for TMS application
"""

import json
import logging
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

logger = logging.getLogger(__name__)


class DebugMeEndpointMiddleware:
    """Temporary: log every request that reaches /api/users/me/ with cookie info."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/api/users/me/':
            has_access = bool(request.COOKIES.get('access_token'))
            has_refresh = bool(request.COOKIES.get('refresh_token'))
            proto = request.META.get('HTTP_X_FORWARDED_PROTO', 'not-set')
            logger.warning(
                f"[DEBUG /me/] method={request.method} "
                f"access_cookie={'YES' if has_access else 'NO'} "
                f"refresh_cookie={'YES' if has_refresh else 'NO'} "
                f"x-forwarded-proto={proto} "
                f"host={request.get_host()}"
            )
        return self.get_response(request)

# Cache timeout for settings (5 minutes)
SETTINGS_CACHE_TIMEOUT = 300


class MaintenanceModeMiddleware:
    """
    Middleware to block access when maintenance mode is enabled.
    Reads from ApplicationSetting model to check if maintenance mode is active.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check cache first, then database
        maintenance_mode = cache.get("setting_maintenance_mode")
        if maintenance_mode is None:
            # Import here to avoid circular imports
            from accounts.models import ApplicationSetting

            maintenance_mode = ApplicationSetting.get_setting("maintenance_mode", False)
            cache.set(
                "setting_maintenance_mode", maintenance_mode, SETTINGS_CACHE_TIMEOUT
            )

        if maintenance_mode:
            # Allow superusers and staff to access
            if request.user.is_authenticated and (
                request.user.is_superuser or request.user.is_staff
            ):
                response = self.get_response(request)
                return response

            # Allow access to admin panel and static/media files
            if (
                request.path.startswith("/admin/")
                or request.path.startswith("/static/")
                or request.path.startswith("/media/")
            ):
                response = self.get_response(request)
                return response

            # Block all other requests
            if request.path.startswith("/api/"):
                # Return JSON response for API requests
                return JsonResponse(
                    {
                        "error": "System under maintenance",
                        "message": "The system is currently undergoing maintenance. Please try again later.",
                        "maintenance_mode": True,
                    },
                    status=503,
                )
            else:
                # Return HTML response for web requests
                return HttpResponse(
                    "<html><head><title>Maintenance</title></head>"
                    '<body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">'
                    "<h1>🔧 System Under Maintenance</h1>"
                    "<p>The system is currently undergoing maintenance. Please try again later.</p>"
                    '<p style="color: #666;">We apologize for any inconvenience.</p>'
                    "</body></html>",
                    status=503,
                )

        response = self.get_response(request)
        return response


class SessionTimeoutMiddleware:
    """
    Middleware to enforce session timeout based on ApplicationSetting.
    Sessions expire after the configured timeout period of inactivity.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check cache first, then database
            timeout_minutes = cache.get("setting_session_timeout_minutes")
            if timeout_minutes is None:
                # Import here to avoid circular imports
                from accounts.models import ApplicationSetting

                timeout_minutes = ApplicationSetting.get_setting(
                    "session_timeout_minutes", 480
                )  # Default: 8 hours
                cache.set(
                    "setting_session_timeout_minutes",
                    timeout_minutes,
                    SETTINGS_CACHE_TIMEOUT,
                )

            # Get last activity time from session
            last_activity = request.session.get("last_activity")

            if last_activity:
                # Convert string to datetime if needed
                if isinstance(last_activity, str):
                    from datetime import datetime

                    last_activity = datetime.fromisoformat(last_activity)

                # Calculate time since last activity
                time_since_activity = timezone.now() - last_activity

                # Check if session has timed out
                if time_since_activity > timedelta(minutes=timeout_minutes):
                    # Session expired - clear it
                    request.session.flush()

                    # Return 401 for API requests
                    if request.path.startswith("/api/"):
                        return JsonResponse(
                            {
                                "error": "Session expired",
                                "message": "Your session has expired due to inactivity. Please log in again.",
                                "session_expired": True,
                            },
                            status=401,
                        )

            # Update last activity time
            request.session["last_activity"] = timezone.now().isoformat()

        response = self.get_response(request)
        return response


class FileSizeValidationMiddleware:
    """
    Middleware to enforce maximum file upload size based on ApplicationSetting.
    Checks Content-Length header before processing the request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only check for POST/PUT/PATCH requests with file uploads
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.META.get("CONTENT_LENGTH")

            if content_length:
                # Check cache first, then database
                max_size = cache.get("setting_max_file_upload_size")
                if max_size is None:
                    # Import here to avoid circular imports
                    from accounts.models import ApplicationSetting

                    max_size = ApplicationSetting.get_setting(
                        "max_file_upload_size", 10485760
                    )  # Default: 10MB
                    cache.set(
                        "setting_max_file_upload_size", max_size, SETTINGS_CACHE_TIMEOUT
                    )

                # Check if request size exceeds limit
                if int(content_length) > max_size:
                    # Calculate size in MB for user-friendly message
                    max_size_mb = max_size / (1024 * 1024)
                    actual_size_mb = int(content_length) / (1024 * 1024)

                    # Return error response
                    if request.path.startswith("/api/"):
                        return JsonResponse(
                            {
                                "error": "File too large",
                                "message": f"Upload size ({actual_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb:.2f} MB).",
                                "max_size_bytes": max_size,
                                "max_size_mb": round(max_size_mb, 2),
                            },
                            status=413,
                        )
                    else:
                        return HttpResponse(
                            f"<html><head><title>File Too Large</title></head>"
                            f'<body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">'
                            f"<h1>❌ File Too Large</h1>"
                            f"<p>Upload size ({actual_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb:.2f} MB).</p>"
                            f"</body></html>",
                            status=413,
                        )

        response = self.get_response(request)
        return response


class DynamicSettingsMiddleware:
    """
    Middleware to load and apply dynamic settings from ApplicationSetting model.
    This ensures settings like timezone are applied for each request.
    Uses caching to minimize database queries.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        import pytz
        from django.utils import timezone as tz

        # Apply timezone setting dynamically with caching
        try:
            timezone_str = cache.get("setting_timezone")
            if timezone_str is None:
                # Import here to avoid circular imports
                from accounts.models import ApplicationSetting

                timezone_str = ApplicationSetting.get_setting("timezone", "UTC")
                cache.set("setting_timezone", timezone_str, SETTINGS_CACHE_TIMEOUT)

            # Activate timezone for this request
            request_timezone = pytz.timezone(timezone_str)
            tz.activate(request_timezone)
        except Exception:
            # Fall back to default timezone
            tz.deactivate()

        response = self.get_response(request)

        # Deactivate timezone after request
        tz.deactivate()

        return response


class SecurityHeadersMiddleware:
    """
    Strips the Server header to prevent version fingerprinting and adds
    Referrer-Policy to control cross-origin referrer leakage.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Server"] = "TMS"
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("Cross-Origin-Resource-Policy", "same-site")
        return response


def clear_settings_cache():
    """
    Utility function to clear all cached settings.
    Call this when ApplicationSettings are updated.

    Usage:
        from tms_project.middleware import clear_settings_cache
        clear_settings_cache()
    """
    cache_keys = [
        "setting_maintenance_mode",
        "setting_session_timeout_minutes",
        "setting_max_file_upload_size",
        "setting_timezone",
    ]
    for key in cache_keys:
        cache.delete(key)
