"""
Custom Cookie-based Authentication for TMS
Replaces insecure localStorage token storage with HttpOnly cookies
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()


class CookieTokenAuthentication(BaseAuthentication):
    """
    Token authentication using HttpOnly cookies instead of localStorage.

    Prevents XSS attacks by making tokens inaccessible to JavaScript.
    Clients should include credentials in requests with: withCredentials: true
    """

    keyword = 'Token'
    cookie_name = 'auth_token'

    def authenticate(self, request):
        """
        Authenticate the request using token from HttpOnly cookie.

        Returns:
            tuple: (user, token) if authentication successful
            None: if no authentication attempted

        Raises:
            AuthenticationFailed: if authentication fails
        """
        # Try to get token from cookie first (new secure method)
        token_key = request.COOKIES.get(self.cookie_name)

        # Fallback to Authorization header for backward compatibility
        # This allows gradual migration
        if not token_key:
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith(f'{self.keyword} '):
                token_key = auth_header.split(' ')[1]

        if not token_key:
            return None  # No authentication attempted

        return self.authenticate_credentials(token_key)

    def authenticate_credentials(self, key):
        """
        Validate the token and return the associated user.

        Args:
            key: Token string

        Returns:
            tuple: (user, token)

        Raises:
            AuthenticationFailed: if token invalid or user inactive
        """
        try:
            token = Token.objects.select_related('user').get(key=key)
        except Token.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted')

        return (token.user, token)

    def authenticate_header(self, request):
        """
        Return string to use in WWW-Authenticate header for 401 responses.
        """
        return self.keyword
