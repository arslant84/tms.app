"""
Application settings, admin action log, and privacy policy views.

Split out of accounts/views.py (see
docs/CODEBASE_REFACTOR_ROADMAP.md item 1) - a pure file move, no
logic changed. Auth/user-management/MFA views moved to their own
sibling modules in the same split.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

# Import standardized response utilities
from utils.api_response import error_response, forbidden_response, success_response

logger = logging.getLogger(__name__)

from .models import AdminActionLog, ApplicationSetting, Permission
from .serializers import (
    AdminActionLogSerializer,
    ApplicationSettingCreateSerializer,
    ApplicationSettingSerializer,
    ApplicationSettingUpdateSerializer,
)
from .utils import has_permission

User = get_user_model()


class ApplicationSettingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing application settings.
    Supports GET (list/retrieve), POST (create), PUT/PATCH (update), DELETE

    Query parameters:
    - public: bool - Filter by public settings only
    - key: str - Filter by setting key
    """

    queryset = ApplicationSetting.objects.all()
    serializer_class = ApplicationSettingSerializer
    lookup_field = "setting_key"
    lookup_value_regex = "[^/]+"  # Allow dots and other chars in setting_key
    pagination_class = None  # Disable pagination for settings

    def get_permissions(self):
        """
        Permission rules:
        - Public settings (?public=true): Anyone can access
        - List/retrieve: Any authenticated user can read
        - Create/update/delete: Admin only
        """
        if self.action == "list" and self.request.query_params.get("public") == "true":
            return [permissions.AllowAny()]
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = super().get_queryset()

        # Filter by public settings
        if self.request.query_params.get("public") == "true":
            queryset = queryset.filter(is_public=True)

        # Filter by key
        key = self.request.query_params.get("key")
        if key:
            queryset = queryset.filter(setting_key=key)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "create":
            return ApplicationSettingCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return ApplicationSettingUpdateSerializer
        return ApplicationSettingSerializer

    @action(detail=False, methods=["put"], permission_classes=[permissions.IsAdminUser])
    def bulk_update(self, request):
        """
        Bulk update multiple settings at once.

        Expected payload:
        {
            "settings": [
                {"setting_key": "app_name", "value": "My App"},
                {"setting_key": "support_email", "value": "support@example.com"}
            ]
        }
        """
        settings_data = request.data.get("settings", [])

        if not isinstance(settings_data, list):
            return error_response(
                message="settings must be a list",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        updated_settings = []
        errors = []

        for setting_data in settings_data:
            setting_key = setting_data.get("setting_key")
            if not setting_key:
                errors.append(
                    {"error": "setting_key is required", "data": setting_data}
                )
                continue

            try:
                setting = ApplicationSetting.objects.get(setting_key=setting_key)
                serializer = ApplicationSettingUpdateSerializer(
                    setting, data=setting_data, partial=True
                )

                if serializer.is_valid():
                    serializer.save()
                    updated_settings.append(ApplicationSettingSerializer(setting).data)
                else:
                    errors.append(
                        {"setting_key": setting_key, "errors": serializer.errors}
                    )

            except ApplicationSetting.DoesNotExist:
                # Create new setting if it doesn't exist
                serializer = ApplicationSettingCreateSerializer(data=setting_data)
                if serializer.is_valid():
                    new_setting = serializer.save()
                    updated_settings.append(
                        ApplicationSettingSerializer(new_setting).data
                    )
                else:
                    errors.append(
                        {"setting_key": setting_key, "errors": serializer.errors}
                    )

        message = f"Successfully updated {len(updated_settings)} settings"
        if errors:
            message += f", {len(errors)} failed"

        return success_response(
            data={"updated": updated_settings},
            message=message,
            status_code=status.HTTP_200_OK,
            meta={"errors": errors} if errors else None,
        )

    @action(
        detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated]
    )
    def as_object(self, request):
        """
        Return all settings as a simple key-value object.

        Query parameters:
        - public: bool - Return only public settings

        Returns: {"setting_key": value, ...}

        SECURITY: Only authenticated users can access settings.
        Non-admin users only get public settings.
        """
        queryset = self.get_queryset()

        # SECURITY: Non-admin users only get public settings
        has_settings_access = request.user.is_superuser or has_permission(
            request.user, "view_system_settings"
        )
        if not has_settings_access:
            queryset = queryset.filter(is_public=True)

        settings_obj = {}

        for setting in queryset:
            settings_obj[setting.setting_key] = setting.get_value()

        return Response(settings_obj)


class AdminActionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing audit logs (security trail).
    Read-only access for security monitoring and compliance.

    SECURITY: Access controlled by RBAC permissions.
    Users must have 'view_activity_logs' permission.
    """

    queryset = AdminActionLog.objects.all().select_related("user")
    serializer_class = AdminActionLogSerializer
    permission_classes = [
        permissions.IsAuthenticated
    ]  # Further restricted by RBAC in get_queryset

    filterset_fields = ["action_type", "entity_type", "user"]
    search_fields = [
        "description",
        "user__email",
        "entity_type",
        "entity_id",
        "ip_address",
    ]
    ordering_fields = ["created_at", "action_type"]
    ordering = ["-created_at"]  # Most recent first

    def get_queryset(self):
        """
        SECURITY: Filter audit logs based on user permissions.
        System administrators can see all logs.
        Other users can only see their own actions.
        """
        queryset = super().get_queryset()
        user = self.request.user

        # SECURITY: Admin users see all audit logs
        if user.is_admin or user.is_superuser:
            return queryset

        # SECURITY: Check if user has explicit permission to view audit logs
        # This should be controlled by RBAC permission 'view_activity_logs'
        from .models import Permission as AppPermission

        try:
            view_audit_perm = AppPermission.objects.get(name="view_activity_logs")
            user_permissions = []
            if user.role:
                user_permissions = user.role.permissions.all()

            if view_audit_perm in user_permissions:
                return queryset
        except AppPermission.DoesNotExist:
            pass

        # Regular users can only see their own audit logs
        return queryset.filter(user=user)

    @action(detail=False, methods=["get"])
    def my_logs(self, request):
        """
        Get audit logs for the current user only.
        Allows users to see their own activity history.
        """
        queryset = self.get_queryset().filter(user=request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(
        detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated]
    )
    def stats(self, request):
        """
        Get audit log statistics.
        SECURITY: Only available to admin users.
        """
        if not request.user.is_admin and not request.user.is_superuser:
            return forbidden_response(
                message="Only administrators can view audit log statistics"
            )

        from django.db.models import Count

        queryset = self.get_queryset()

        # Count by action type
        action_stats = (
            queryset.values("action_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Count by user
        user_stats = (
            queryset.values("user__email", "user__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # Recent activity (last 24 hours)
        recent_cutoff = timezone.now() - timedelta(hours=24)
        recent_count = queryset.filter(created_at__gte=recent_cutoff).count()

        stats_data = {
            "total_logs": queryset.count(),
            "recent_activity_24h": recent_count,
            "by_action_type": list(action_stats),
            "top_users": list(user_stats),
        }

        return success_response(
            data=stats_data,
            message="Audit log statistics retrieved successfully",
            status_code=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Privacy Policy View — CTRL-0000001000 / CTRL-0000001001 / CTRL-0000001003
# ---------------------------------------------------------------------------


class PrivacyPolicyView(APIView):
    """
    GET /api/auth/privacy-policy/
    Returns the current privacy policy text and version.
    Public endpoint — shown to users before/during registration.
    """

    permission_classes = [permissions.AllowAny]

    POLICY_TEXT = """
TMS APPLICATION PRIVACY NOTICE

1. PURPOSE: Your personal data (name, email, staff ID, phone, department, travel details,
   passport information, and bank details) is collected solely for the purpose of processing
   travel requests and related logistics within the organisation.

2. RETENTION: Personal data is retained for the period required by the organisation's
   data retention policy (default 7 years) and then securely disposed of.

3. PROTECTION: Your data is protected using industry-standard encryption (AES-256 at rest,
   TLS 1.2+ in transit) and access is restricted on a least-privilege basis.

4. ACCESS & CORRECTION: You may request a copy of your personal data or corrections
   by contacting the system administrator.

5. OPT-OUT / ERASURE: Contact the system administrator to request deletion of your
   account and associated personal data, subject to legal retention obligations.

6. THIRD PARTIES: Your data will not be sold or disclosed to third parties outside
   the organisation without your consent, except as required by law.
""".strip()

    def get(self, request):
        from django.conf import settings as django_settings

        version = getattr(django_settings, "PRIVACY_POLICY_VERSION", "1.0")
        return success_response(
            data={
                "version": version,
                "content": self.POLICY_TEXT,
                "effective_date": "2026-01-01",
            },
            message="Privacy policy retrieved",
            status_code=status.HTTP_200_OK,
        )
