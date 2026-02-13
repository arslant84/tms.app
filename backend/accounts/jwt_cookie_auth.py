"""
Custom JWT Cookie-based Authentication for TMS
Uses HttpOnly cookies for access and refresh tokens with expiration
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class JWTCookieAuthentication(BaseAuthentication):
    """
    JWT authentication using HttpOnly cookies instead of Authorization header.

    Provides token expiration and automatic refresh mechanism.
    Prevents XSS attacks by making tokens inaccessible to JavaScript.
    """

    access_cookie_name = 'access_token'
    refresh_cookie_name = 'refresh_token'

    def authenticate(self, request):
        """
        Authenticate the request using JWT from HttpOnly cookie.

        Returns:
            tuple: (user, validated_token) if authentication successful
            None: if no authentication attempted or token is invalid

        Note: Returns None instead of raising exception for invalid tokens
        to allow unauthenticated access to public endpoints like login.
        """
        # Try to get access token from cookie
        access_token = request.COOKIES.get(self.access_cookie_name)

        if not access_token:
            logger.debug(f"No access token cookie found for {request.path}")
            return None  # No authentication attempted

        try:
            user, token = self.authenticate_credentials(access_token)
            logger.info(f"JWT auth successful for user {user.id} ({user.email}), is_staff={user.is_staff}, is_superuser={user.is_superuser}")
            return (user, token)
        except exceptions.AuthenticationFailed as e:
            # Return None instead of raising exception - allows public endpoints to work
            # even when there's an invalid/expired token in cookies
            logger.warning(f"JWT authentication failed for {request.path}: {str(e)}")
            return None

    def authenticate_credentials(self, token_string):
        """
        Validate the JWT token and return the associated user.

        Args:
            token_string: JWT token string

        Returns:
            tuple: (user, validated_token)

        Raises:
            AuthenticationFailed: if token invalid or user inactive
        """
        try:
            # Validate and decode the access token
            validated_token = AccessToken(token_string)

            # Get user ID from token
            user_id = validated_token.get('user_id')

            # Get user from database
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise exceptions.AuthenticationFailed('User not found')

            if not user.is_active:
                raise exceptions.AuthenticationFailed('User inactive or deleted')

            return (user, validated_token)

        except (TokenError, InvalidToken) as e:
            raise exceptions.AuthenticationFailed(f'Invalid token: {str(e)}')

    def authenticate_header(self, request):
        """
        Return string to use in WWW-Authenticate header for 401 responses.
        """
        return 'Bearer'
