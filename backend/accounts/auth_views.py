"""
Authentication views: login, logout, token refresh, password
change/reset, registration.

Split out of accounts/views.py (see
docs/CODEBASE_REFACTOR_ROADMAP.md item 1) - a pure file move, no
logic changed. MFA/user-management/settings views moved to their
own sibling modules in the same split.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login
from django.core import signing
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

# Import standardized response utilities
from utils.api_response import (
    created_response,
    error_response,
    success_response,
    unauthorized_response,
    validation_error_response,
)

logger = logging.getLogger(__name__)

from .models import AdminActionLog, ApplicationSetting, Department
from .serializers import (
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)

User = get_user_model()


@method_decorator(csrf_exempt, name="dispatch")
class LoginView(APIView):
    """User authentication endpoint."""

    authentication_classes = (
        []
    )  # No credentials on login; avoids SessionAuthentication CSRF enforcement
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="User Login",
        description="Authenticate user with email and password. Returns user data and sets HttpOnly JWT cookies.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "format": "email"},
                    "password": {"type": "string", "format": "password"},
                },
                "required": ["email", "password"],
            }
        },
        responses={
            200: UserSerializer,
            401: OpenApiTypes.OBJECT,
            429: OpenApiTypes.OBJECT,
        },
    )
    @method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True))
    def post(self, request, *args, **kwargs):
        # Get username and password from request
        username = request.data.get("email")
        password = request.data.get("password")

        logger.info(f"Login attempt for user: {username}")

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # MFA gate — if MFA is enabled, return a short-lived challenge
            # token instead of issuing JWT cookies (CTRL-0000001024/1063).
            if user.mfa_enabled:
                challenge_token = signing.dumps(
                    {"user_id": str(user.id)},
                    salt="mfa-login-challenge",
                )
                AdminActionLog.log_action(
                    user=user,
                    action_type="login_success",
                    description=f"MFA challenge issued for: {user.email}",
                    entity_type="User",
                    entity_id=str(user.id),
                    request=request,
                )
                return success_response(
                    data={"mfa_required": True, "challenge_token": challenge_token},
                    message="MFA verification required",
                    status_code=status.HTTP_200_OK,
                )

            # SECURITY: Log successful login for audit trail
            AdminActionLog.log_action(
                user=user,
                action_type="login_success",
                description=f"User logged in successfully: {user.email}",
                entity_type="User",
                entity_id=str(user.id),
                request=request,
            )

            # SECURITY: Generate JWT tokens with expiration
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # CTRL-0000001025 / CTRL-0000001061: privileged passwords expire after 30 days.
            is_privileged = user.is_admin or user.is_staff or user.is_superuser
            if is_privileged and user.password_last_changed:
                age_days = (timezone.now() - user.password_last_changed).days
                if age_days >= 30 and not user.password_change_required:
                    user.password_change_required = True
                    user.save(update_fields=["password_change_required"])
                    AdminActionLog.log_action(
                        user=user,
                        action_type="password_expired",
                        description=f"Privileged account password expired ({age_days} days old): {user.email}",
                        entity_type="User",
                        entity_id=str(user.id),
                        request=request,
                    )

            # CTRL-0000001063: privileged accounts must enrol MFA.
            # Issue JWT so they can reach the setup endpoint, but signal
            # the frontend to redirect to MFA setup before allowing access.
            mfa_setup_required = is_privileged and not user.mfa_enabled

            user_data = UserSerializer(user).data
            if mfa_setup_required:
                user_data["mfa_setup_required"] = True

            response = success_response(
                data=user_data,
                message=(
                    "Login successful — MFA setup required"
                    if mfa_setup_required
                    else "Login successful"
                ),
                status_code=status.HTTP_200_OK,
            )

            # SECURITY: Set JWT tokens in HttpOnly cookies
            # Access token for authentication (short-lived)
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,  # Prevents JavaScript access (XSS protection)
                secure=not settings.DEBUG,  # False in development (HTTP), True in production (HTTPS)
                samesite="Lax",  # CSRF protection
                max_age=3600,  # 1 hour (matches ACCESS_TOKEN_LIFETIME)
                path="/",
            )

            # Refresh token for getting new access tokens (long-lived)
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,  # Prevents JavaScript access (XSS protection)
                secure=not settings.DEBUG,  # False in development (HTTP), True in production (HTTPS)
                samesite="Lax",  # CSRF protection
                max_age=86400 * 7,  # 7 days (matches REFRESH_TOKEN_LIFETIME)
                path="/",
            )

            # Keep legacy token for backward compatibility during migration
            # TODO: Remove this after full JWT migration
            token, created = Token.objects.get_or_create(user=user)
            response.set_cookie(
                key="auth_token",
                value=token.key,
                httponly=True,
                secure=not settings.DEBUG,  # False in development (HTTP), True in production (HTTPS)
                samesite="Lax",
                max_age=86400 * 7,
                path="/",
            )

            return response
        else:
            logger.warning(f"Authentication failed for user: {username}")
            # SECURITY: Log failed login attempt for audit trail
            AdminActionLog.log_action(
                user=None,  # User not authenticated
                action_type="login_failed",
                description=f"Failed login attempt for email: {username}",
                entity_type="User",
                entity_id="",
                request=request,
            )
            # SECURITY: Generic error message to prevent user enumeration
            return unauthorized_response(message="Invalid credentials")


class LogoutView(APIView):
    """User logout endpoint."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Authentication"],
        summary="User Logout",
        description="Logout the current user. Blacklists refresh token and clears auth cookies.",
        responses={
            200: {"description": "Successfully logged out"},
            401: {"description": "Not authenticated"},
        },
    )
    def post(self, request):
        try:
            # SECURITY: Log logout for audit trail
            AdminActionLog.log_action(
                user=request.user,
                action_type="logout",
                description=f"User logged out: {request.user.email}",
                entity_type="User",
                entity_id=str(request.user.id),
                request=request,
            )

            # SECURITY: Blacklist the refresh token to prevent reuse
            refresh_token = request.COOKIES.get("refresh_token")
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()  # Add to blacklist
                except TokenError:
                    pass  # Token already invalid or blacklisted

            # Delete legacy token for backward compatibility
            # TODO: Remove this after full JWT migration
            try:
                request.user.auth_token.delete()
            except:
                pass

            # SECURITY: Clear all auth cookies
            response = success_response(
                message="Successfully logged out", status_code=status.HTTP_200_OK
            )
            response.delete_cookie("access_token", path="/")
            response.delete_cookie("refresh_token", path="/")
            response.delete_cookie("auth_token", path="/")  # Legacy token

            return response
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return error_response(
                message="Logout failed",
                errors={"detail": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TokenRefreshView(APIView):
    """
    Refresh access token using refresh token from HttpOnly cookie.

    SECURITY: Rotates refresh tokens and blacklists old ones.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # Get refresh token from cookie
        refresh_token_str = request.COOKIES.get("refresh_token")

        if not refresh_token_str:
            return unauthorized_response(message="Refresh token not found")

        try:
            # Validate and refresh the token
            refresh = RefreshToken(refresh_token_str)

            # SECURITY: Token rotation - generate new refresh token
            # Old token is automatically blacklisted (BLACKLIST_AFTER_ROTATION=True)
            new_access_token = str(refresh.access_token)

            # For full rotation, generate a completely new refresh token
            if hasattr(refresh, "rotate"):
                refresh.rotate()
            new_refresh_token = str(refresh)

            # Create standardized response
            response = success_response(
                message="Token refreshed successfully", status_code=status.HTTP_200_OK
            )

            # Set new access token cookie
            response.set_cookie(
                key="access_token",
                value=new_access_token,
                httponly=True,
                secure=not settings.DEBUG,  # False in development (HTTP), True in production (HTTPS)
                samesite="Lax",
                max_age=3600,  # 1 hour
                path="/",
            )

            # Set new refresh token cookie
            response.set_cookie(
                key="refresh_token",
                value=new_refresh_token,
                httponly=True,
                secure=not settings.DEBUG,  # False in development (HTTP), True in production (HTTPS)
                samesite="Lax",
                max_age=86400 * 7,  # 7 days
                path="/",
            )

            return response

        except TokenError as e:
            logger.warning(f"Token refresh failed: {str(e)}")
            return unauthorized_response(message=f"Invalid refresh token: {str(e)}")


class PasswordChangeView(APIView):
    """
    Change password for authenticated user.
    SECURITY: Clears password_change_required flag after successful change.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors, message="Invalid password data"
            )

        user = request.user
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        # Verify old password
        if not user.check_password(old_password):
            return error_response(
                message="Current password is incorrect",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # CTRL-0000001025: enforce minimum 1-day password age for privileged accounts.
        # Skip when password_change_required is True (forced change must not be blocked).
        is_privileged = user.is_admin or user.is_staff or user.is_superuser
        if (
            is_privileged
            and not user.password_change_required
            and user.password_last_changed
        ):
            age_seconds = (timezone.now() - user.password_last_changed).total_seconds()
            if age_seconds < 86400:
                return error_response(
                    message="Password was changed less than 24 hours ago. Please wait before changing again.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        # Set new password
        user.set_password(new_password)
        user.password_change_required = False
        user.password_last_changed = timezone.now()  # CTRL-0000001025
        user.save()

        return success_response(
            data={"password_change_required": False},
            message="Password changed successfully",
            status_code=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    """
    Request a password reset. Sends email with reset token.
    SECURITY: Rate limited to prevent abuse.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Request Password Reset",
        description="Request a password reset email. Rate limited to 3 requests per hour.",
        request=PasswordResetRequestSerializer,
        responses={
            200: {"description": "If the email exists, a reset link will be sent"},
            429: {"description": "Rate limit exceeded"},
        },
    )
    @method_decorator(ratelimit(key="ip", rate="3/h", method="POST", block=False))
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors, message="Invalid email data"
            )

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email, is_active=True)

            # Generate reset token (64 characters, URL-safe)
            reset_token = get_random_string(64)

            # Store token and expiry in user model (expires in 1 hour)
            user.password_reset_token = reset_token
            user.password_reset_token_expires = timezone.now() + timedelta(hours=1)
            user.save()

            # Send email with reset link
            reset_url = (
                f"{settings.FRONTEND_URL}/auth/reset-password#token={reset_token}"
            )

            email_notifications_enabled = ApplicationSetting.get_setting(
                "enable_email_notifications", True
            )

            if not email_notifications_enabled:
                logger.warning(
                    "Email notifications disabled globally - skipping password reset email to %s",
                    email,
                )
            else:
                try:
                    send_mail(
                        subject="Password Reset Request - SynTra TMS",
                        message=f"""Hello {user.name},

You have requested to reset your password for your SynTra Travel Management System account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you did not request this password reset, please ignore this email and your password will remain unchanged.

Best regards,
SynTra TMS Team""",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                except Exception as e:
                    # Log email sending failure but don't expose it to user
                    logger.error(
                        f"Failed to send password reset email to {email}: {str(e)}"
                    )
                    # Continue execution - token is saved, user will see generic success message

        except User.DoesNotExist:
            # SECURITY: Don't reveal if email exists or not
            pass

        # SECURITY: Always return success to prevent email enumeration
        return success_response(
            message="If an account exists with this email, a password reset link has been sent.",
            status_code=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    Confirm password reset with token and set new password.
    SECURITY: Token expires after 1 hour.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Confirm Password Reset",
        description="Reset password using the token from the reset email.",
        request=PasswordResetConfirmSerializer,
        responses={
            200: {"description": "Password reset successfully"},
            400: {"description": "Invalid or expired token"},
        },
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors, message="Invalid reset data"
            )

        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        try:
            user = User.objects.get(
                password_reset_token=token,
                password_reset_token_expires__gt=timezone.now(),
            )

            # Set new password
            user.set_password(new_password)
            user.password_reset_token = None
            user.password_reset_token_expires = None
            user.password_change_required = False
            user.password_last_changed = timezone.now()  # CTRL-0000001025
            user.save()

            logger.info(f"Password reset successful for user: {user.email}")
            return success_response(
                message="Password reset successfully. You can now log in with your new password.",
                status_code=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            return error_response(
                message="Invalid or expired reset token",
                status_code=status.HTTP_400_BAD_REQUEST,
            )


class RegisterView(APIView):
    """
    Public endpoint for user self-registration.

    Security Features:
    - Rate limited (3 per hour per IP)
    - Users cannot select their own role
    - Automatically assigned to "Registered User" role
    - All registrations are audit logged
    - No auto-login (prevents bot abuse)
    """

    authentication_classes = []  # Public endpoint - no authentication required
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="User Self-Registration",
        description="Register a new user account. Users cannot select roles - admin assigns roles later.",
        request=UserRegistrationSerializer,
        responses={
            201: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                    "data": {"type": "object"},
                },
            },
            400: {"description": "Validation error"},
            429: {"description": "Rate limit exceeded"},
        },
        examples=[
            OpenApiExample(
                "Registration Request",
                value={
                    "email": "user@example.com",
                    "name": "John Doe",
                    "password": "SecurePass123!",
                    "password_confirm": "SecurePass123!",
                    "staff_id": "EMP-12345",
                    "phone": "+1234567890",
                    "department": "IT Department",
                    "gender": "Male",
                },
            )
        ],
    )
    @method_decorator(ratelimit(key="ip", rate="3/h", method="POST", block=False))
    def post(self, request):
        # Check if rate limited
        was_limited = getattr(request, "limited", False)
        if was_limited:
            return error_response(
                message="Too many registration attempts. Please try again later.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = UserRegistrationSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors,
                message="Registration failed. Please correct the errors below.",
            )

        try:
            user = serializer.save()

            # Get IP address from request
            ip_address = self.get_client_ip(request)

            AdminActionLog.log_action(
                user=user,
                action_type="user_created",
                description=f"User self-registered: {user.email} ({user.name})",
                entity_type="User",
                entity_id=str(user.id),
                request=request,
            )

            logger.info(
                f"New user registration: {user.email} (ID: {user.id})",
                extra={
                    "user_id": str(user.id),
                    "email": user.email,
                    "ip_address": ip_address,
                },
            )

            return created_response(
                data={
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "staff_id": user.staff_id,
                    "role": (
                        {"id": str(user.role.id), "name": user.role.name}
                        if user.role
                        else None
                    ),
                    "department": (
                        {"id": str(user.department.id), "name": user.department.name}
                        if user.department
                        else None
                    ),
                },
                message="Registration successful! You can now login with your credentials.",
            )

        except Exception as e:
            logger.error(
                f"Registration failed: {str(e)}", extra={"error": str(e)}, exc_info=True
            )
            return error_response(
                message="Registration failed. Please try again later.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
