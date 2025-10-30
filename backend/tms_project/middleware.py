"""
Custom middleware for TMS application
"""
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from datetime import timedelta
import json


class MaintenanceModeMiddleware:
    """
    Middleware to block access when maintenance mode is enabled.
    Reads from ApplicationSetting model to check if maintenance mode is active.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Import here to avoid circular imports
        from accounts.models import ApplicationSetting

        # Check if maintenance mode is enabled
        maintenance_mode = ApplicationSetting.get_setting('maintenance_mode', False)

        if maintenance_mode:
            # Allow superusers and staff to access
            if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
                response = self.get_response(request)
                return response

            # Allow access to admin panel and static/media files
            if request.path.startswith('/admin/') or \
               request.path.startswith('/static/') or \
               request.path.startswith('/media/'):
                response = self.get_response(request)
                return response

            # Block all other requests
            if request.path.startswith('/api/'):
                # Return JSON response for API requests
                return JsonResponse({
                    'error': 'System under maintenance',
                    'message': 'The system is currently undergoing maintenance. Please try again later.',
                    'maintenance_mode': True
                }, status=503)
            else:
                # Return HTML response for web requests
                return HttpResponse(
                    '<html><head><title>Maintenance</title></head>'
                    '<body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">'
                    '<h1>🔧 System Under Maintenance</h1>'
                    '<p>The system is currently undergoing maintenance. Please try again later.</p>'
                    '<p style="color: #666;">We apologize for any inconvenience.</p>'
                    '</body></html>',
                    status=503
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
        # Import here to avoid circular imports
        from accounts.models import ApplicationSetting

        if request.user.is_authenticated:
            # Get configured session timeout (in minutes)
            timeout_minutes = ApplicationSetting.get_setting('session_timeout_minutes', 480)  # Default: 8 hours

            # Get last activity time from session
            last_activity = request.session.get('last_activity')

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
                    if request.path.startswith('/api/'):
                        return JsonResponse({
                            'error': 'Session expired',
                            'message': 'Your session has expired due to inactivity. Please log in again.',
                            'session_expired': True
                        }, status=401)

            # Update last activity time
            request.session['last_activity'] = timezone.now().isoformat()

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
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_length = request.META.get('CONTENT_LENGTH')

            if content_length:
                # Import here to avoid circular imports
                from accounts.models import ApplicationSetting

                # Get configured max file size (in bytes)
                max_size = ApplicationSetting.get_setting('max_file_upload_size', 10485760)  # Default: 10MB

                # Check if request size exceeds limit
                if int(content_length) > max_size:
                    # Calculate size in MB for user-friendly message
                    max_size_mb = max_size / (1024 * 1024)
                    actual_size_mb = int(content_length) / (1024 * 1024)

                    # Return error response
                    if request.path.startswith('/api/'):
                        return JsonResponse({
                            'error': 'File too large',
                            'message': f'Upload size ({actual_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb:.2f} MB).',
                            'max_size_bytes': max_size,
                            'max_size_mb': round(max_size_mb, 2)
                        }, status=413)
                    else:
                        return HttpResponse(
                            f'<html><head><title>File Too Large</title></head>'
                            f'<body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">'
                            f'<h1>❌ File Too Large</h1>'
                            f'<p>Upload size ({actual_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb:.2f} MB).</p>'
                            f'</body></html>',
                            status=413
                        )

        response = self.get_response(request)
        return response


class DynamicSettingsMiddleware:
    """
    Middleware to load and apply dynamic settings from ApplicationSetting model.
    This ensures settings like timezone are applied for each request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Import here to avoid circular imports
        from accounts.models import ApplicationSetting
        from django.utils import timezone as tz
        import pytz

        # Apply timezone setting dynamically
        try:
            timezone_str = ApplicationSetting.get_setting('timezone', 'UTC')
            # Activate timezone for this request
            request_timezone = pytz.timezone(timezone_str)
            tz.activate(request_timezone)
        except Exception as e:
            # Fall back to default timezone
            tz.deactivate()

        response = self.get_response(request)

        # Deactivate timezone after request
        tz.deactivate()

        return response
