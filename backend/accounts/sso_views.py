"""
Microsoft Entra ID (Azure AD) SSO: an alternative to the existing
email/password + MFA login, not a replacement. A user must already have a
TMS account matching the Entra ID email - this does not auto-provision
new accounts.

MFA is intentionally not re-challenged here: Entra ID's own conditional
access/MFA policy is what PETRONAS asked this integration to enforce
(see the onboarding email thread), so gating an already-MFA'd Microsoft
sign-in behind this app's own TOTP MFA would be redundant.
"""

import logging

import msal
from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit
from rest_framework import permissions
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AdminActionLog, User

logger = logging.getLogger(__name__)

_SESSION_FLOW_KEY = "azure_ad_flow"


def _msal_app():
    return msal.ConfidentialClientApplication(
        settings.AZURE_AD_CLIENT_ID,
        authority=settings.AZURE_AD_AUTHORITY,
        client_credential=settings.AZURE_AD_CLIENT_SECRET,
    )


def _login_redirect(reason=None):
    url = f"{settings.FRONTEND_URL}/auth/login"
    if reason:
        url += f"?sso_error={reason}"
    return HttpResponseRedirect(url)


class AzureADLoginView(APIView):
    """Starts the Microsoft sign-in flow: redirects the browser to Entra ID."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @method_decorator(ratelimit(key="ip", rate="30/m", method="GET", block=True))
    def get(self, request):
        if not settings.AZURE_AD_ENABLED:
            return _login_redirect("not_configured")

        try:
            flow = _msal_app().initiate_auth_code_flow(
                scopes=["User.Read"],
                redirect_uri=settings.AZURE_AD_REDIRECT_URI,
            )
        except Exception:
            # ConfidentialClientApplication() does live OIDC discovery
            # against Microsoft at construction time - a bad tenant ID or
            # transient network issue must not surface as a raw 500 on a
            # user-facing login button.
            logger.exception("Failed to start Azure AD SSO flow")
            return _login_redirect("unavailable")

        request.session[_SESSION_FLOW_KEY] = flow
        return HttpResponseRedirect(flow["auth_uri"])


@method_decorator(csrf_exempt, name="dispatch")
class AzureADCallbackView(APIView):
    """
    Handles Microsoft's redirect back after sign-in: exchanges the auth
    code, maps the Entra ID email to an existing TMS user, and issues the
    same JWT cookies LoginView does.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @method_decorator(ratelimit(key="ip", rate="30/m", method="GET", block=True))
    def get(self, request):
        if not settings.AZURE_AD_ENABLED:
            return _login_redirect("not_configured")

        flow = request.session.pop(_SESSION_FLOW_KEY, None)
        if not flow:
            return _login_redirect("session_expired")

        try:
            result = _msal_app().acquire_token_by_auth_code_flow(flow, request.GET)
        except Exception:
            logger.exception("Failed to complete Azure AD SSO flow")
            return _login_redirect("unavailable")

        if "error" in result:
            logger.warning(
                "Azure AD SSO error: %s",
                result.get("error_description", result.get("error")),
            )
            AdminActionLog.log_action(
                user=None,
                action_type="login_failed",
                description=(
                    f"Azure AD SSO failed: "
                    f"{result.get('error_description', result.get('error'))}"
                ),
                entity_type="User",
                request=request,
            )
            return _login_redirect("auth_failed")

        claims = result.get("id_token_claims") or {}
        email = (
            (claims.get("preferred_username") or claims.get("email") or "")
            .strip()
            .lower()
        )

        if not email:
            return _login_redirect("no_email")

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            AdminActionLog.log_action(
                user=None,
                action_type="login_failed",
                description=f"Azure AD SSO: no matching TMS account for {email}",
                entity_type="User",
                request=request,
            )
            return _login_redirect("no_account")

        if not user.is_active:
            AdminActionLog.log_action(
                user=user,
                action_type="login_failed",
                description=f"Azure AD SSO: account inactive for {email}",
                entity_type="User",
                entity_id=str(user.id),
                request=request,
            )
            return _login_redirect("inactive_account")

        AdminActionLog.log_action(
            user=user,
            action_type="login_success",
            description=f"User logged in via Azure AD SSO: {user.email}",
            entity_type="User",
            entity_id=str(user.id),
            request=request,
        )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = HttpResponseRedirect(settings.FRONTEND_URL)

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            max_age=3600,
            path="/",
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            max_age=86400 * 7,
            path="/",
        )

        # Keep legacy token for backward compatibility during migration,
        # same as LoginView.
        token, _created = Token.objects.get_or_create(user=user)
        response.set_cookie(
            key="auth_token",
            value=token.key,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            max_age=86400 * 7,
            path="/",
        )

        return response
