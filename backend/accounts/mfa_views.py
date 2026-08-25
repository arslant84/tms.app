"""
MFA (multi-factor authentication) setup/confirm/verify/disable views.

Split out of accounts/views.py (see
docs/CODEBASE_REFACTOR_ROADMAP.md item 1) - a pure file move, no
logic changed. Auth/user-management/settings views moved to their
own sibling modules in the same split.
"""

import logging

import pyotp
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.core import signing
from django.core.signing import BadSignature, SignatureExpired
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

# Import standardized response utilities
from utils.api_response import (
    error_response,
    success_response,
    unauthorized_response,
    validation_error_response,
)

logger = logging.getLogger(__name__)

from .models import AdminActionLog
from .serializers import (
    MFAConfirmSerializer,
    MFADisableSerializer,
    MFAVerifySerializer,
    UserSerializer,
)

User = get_user_model()

# ---------------------------------------------------------------------------
# MFA Views — CTRL-0000001024 / CTRL-0000001063
# ---------------------------------------------------------------------------


class MFASetupView(APIView):
    """
    GET  /api/auth/mfa/setup/
    Returns a TOTP secret and QR provisioning URI.
    The user scans the QR code in their authenticator app, then calls
    MFAConfirmView to activate MFA on their account.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.mfa_enabled:
            return error_response(
                message="MFA is already enabled on this account.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Generate a new secret (overwriting any previous unconfirmed setup)
        secret = pyotp.random_base32()
        user.mfa_secret = secret
        user.save(update_fields=["mfa_secret"])

        totp = pyotp.TOTP(secret)
        qr_uri = totp.provisioning_uri(name=user.email, issuer_name="TMS Application")

        return success_response(
            data={"secret": secret, "qr_uri": qr_uri},
            message="Scan the QR code with your authenticator app, then confirm with /mfa/confirm/",
            status_code=status.HTTP_200_OK,
        )


class MFAConfirmView(APIView):
    """
    POST /api/auth/mfa/confirm/
    Verifies the first OTP from the authenticator app and enables MFA.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = MFAConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        user = request.user
        otp = serializer.validated_data["otp"]

        if not user.mfa_secret:
            return error_response(
                message="No MFA setup in progress. Call /mfa/setup/ first.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(otp, valid_window=1):
            AdminActionLog.log_action(
                user=user,
                action_type="mfa_failed",
                description=f"MFA confirm failed (invalid OTP): {user.email}",
                entity_type="User",
                entity_id=str(user.id),
                request=request,
            )
            return error_response(
                message="Invalid OTP code. Please try again.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user.mfa_enabled = True
        user.save(update_fields=["mfa_enabled"])

        AdminActionLog.log_action(
            user=user,
            action_type="mfa_enabled",
            description=f"MFA enabled for user: {user.email}",
            entity_type="User",
            entity_id=str(user.id),
            request=request,
        )

        return success_response(
            data={"mfa_enabled": True},
            message="MFA has been enabled on your account.",
            status_code=status.HTTP_200_OK,
        )


class MFAVerifyView(APIView):
    """
    POST /api/auth/mfa/verify/
    Called after a login attempt returns mfa_required=true.
    Validates the challenge_token and OTP, then issues full JWT cookies.
    """

    permission_classes = [permissions.AllowAny]

    @method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True))
    def post(self, request):
        serializer = MFAVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        challenge_token = serializer.validated_data["challenge_token"]
        otp = serializer.validated_data["otp"]

        # Decode the challenge token (max age 5 minutes)
        try:
            data = signing.loads(
                challenge_token, salt="mfa-login-challenge", max_age=300
            )
        except SignatureExpired:
            return unauthorized_response(
                message="MFA challenge expired. Please log in again."
            )
        except BadSignature:
            return unauthorized_response(message="Invalid challenge token.")

        user = User.objects.filter(id=data.get("user_id")).first()
        if not user or not user.mfa_enabled or not user.mfa_secret:
            return unauthorized_response(message="Invalid MFA session.")

        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(otp, valid_window=1):
            AdminActionLog.log_action(
                user=user,
                action_type="mfa_failed",
                description=f"MFA login verification failed: {user.email}",
                entity_type="User",
                entity_id=str(user.id),
                request=request,
            )
            return unauthorized_response(message="Invalid OTP code.")

        # CTRL-0000001025: check password age for privileged accounts after MFA verification.
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

        # OTP valid — issue JWT tokens (same flow as normal login)
        AdminActionLog.log_action(
            user=user,
            action_type="login_success",
            description=f"MFA-verified login for: {user.email}",
            entity_type="User",
            entity_id=str(user.id),
            request=request,
        )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token_str = str(refresh)

        response = success_response(
            data=UserSerializer(user).data,
            message="Login successful",
            status_code=status.HTTP_200_OK,
        )
        response.set_cookie(
            "access_token",
            access_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            max_age=3600,
            path="/",
        )
        response.set_cookie(
            "refresh_token",
            refresh_token_str,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            max_age=86400 * 7,
            path="/",
        )

        token, _ = Token.objects.get_or_create(user=user)
        response.set_cookie(
            "auth_token",
            token.key,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            max_age=86400 * 7,
            path="/",
        )

        return response


class MFADisableView(APIView):
    """
    POST /api/auth/mfa/disable/
    Disables MFA after verifying OTP + account password for safety.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = MFADisableSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        user = request.user
        otp = serializer.validated_data["otp"]
        password = serializer.validated_data["password"]

        if not user.mfa_enabled:
            return error_response(
                message="MFA is not enabled on this account.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if not user.check_password(password):
            return unauthorized_response(message="Incorrect password.")

        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(otp, valid_window=1):
            AdminActionLog.log_action(
                user=user,
                action_type="mfa_failed",
                description=f"MFA disable failed (invalid OTP): {user.email}",
                entity_type="User",
                entity_id=str(user.id),
                request=request,
            )
            return error_response(
                message="Invalid OTP code.", status_code=status.HTTP_400_BAD_REQUEST
            )

        user.mfa_enabled = False
        user.mfa_secret = None
        user.save(update_fields=["mfa_enabled", "mfa_secret"])

        AdminActionLog.log_action(
            user=user,
            action_type="mfa_disabled",
            description=f"MFA disabled for user: {user.email}",
            entity_type="User",
            entity_id=str(user.id),
            request=request,
        )

        return success_response(
            data={"mfa_enabled": False},
            message="MFA has been disabled on your account.",
            status_code=status.HTTP_200_OK,
        )


class MFAStatusView(APIView):
    """GET /api/auth/mfa/status/ — returns whether MFA is enabled for the current user."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return success_response(
            data={"mfa_enabled": request.user.mfa_enabled},
            message="MFA status retrieved",
            status_code=status.HTTP_200_OK,
        )
