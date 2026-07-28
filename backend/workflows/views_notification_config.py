"""
API views for workflow step notification configuration.
Provides CRUD operations and helper endpoints.
"""

import logging

from rest_framework import viewsets

logger = logging.getLogger(__name__)
from accounts.models import Role, User
from notifications.models import NotificationTemplate
from notifications.views import CanManageNotifications
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import WorkflowStepNotificationConfig
from .serializers import (
    NotificationTemplateSimpleSerializer,
    RoleSimpleSerializer,
    UserSimpleSerializer,
    WorkflowStepNotificationConfigSerializer,
)


class WorkflowStepNotificationConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing workflow step notification configurations.

    Endpoints:
    - GET    /api/workflows/notification-configs/ - List all configs
    - POST   /api/workflows/notification-configs/ - Create new config
    - GET    /api/workflows/notification-configs/{id}/ - Get specific config
    - PUT    /api/workflows/notification-configs/{id}/ - Update config
    - PATCH  /api/workflows/notification-configs/{id}/ - Partial update
    - DELETE /api/workflows/notification-configs/{id}/ - Delete config

    Custom actions:
    - GET /api/workflows/notification-configs/by_step/{step_id}/ - Get configs for a step
    - GET /api/workflows/notification-configs/options/ - Get dropdown options
    """

    permission_classes = [IsAuthenticated, CanManageNotifications]
    serializer_class = WorkflowStepNotificationConfigSerializer

    def get_queryset(self):
        """Get notification configs with filters"""
        queryset = WorkflowStepNotificationConfig.objects.select_related(
            "workflow_step",
            "workflow_step__workflow_template",
            "notification_template",
        )

        # Filter by workflow step
        step_id = self.request.query_params.get("workflow_step")
        if step_id:
            queryset = queryset.filter(workflow_step_id=step_id)

        # Filter by event type
        event_type = self.request.query_params.get("event_type")
        if event_type:
            queryset = queryset.filter(event_type=event_type)

        # Filter by active status
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        # Filter by entity type (via workflow template)
        entity_type = self.request.query_params.get("entity_type")
        if entity_type:
            queryset = queryset.filter(
                workflow_step__workflow_template__entity_type=entity_type
            )

        return queryset.order_by("workflow_step", "event_type")

    def create(self, request, *args, **kwargs):
        """Override create to add better error logging"""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(" Validation failed")
            logger.error(f" Request data: {request.data}")
            logger.error(f" Errors: {serializer.errors}")
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="by_step/(?P<step_id>[^/.]+)")
    def by_step(self, request, step_id=None):
        """
        Get all notification configurations for a specific workflow step.

        GET /api/workflows/notification-configs/by_step/{step_id}/
        """
        configs = self.get_queryset().filter(workflow_step_id=step_id)
        serializer = self.get_serializer(configs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def options(self, request):
        """
        Get dropdown options for notification configuration form.

        GET /api/workflows/notification-configs/options/

        Returns:
        - event_types: List of available event types
        - recipient_types: List of available recipient types
        - priorities: List of priority levels
        - roles: List of active roles
        - templates: List of active notification templates
        """
        # Get model choices
        event_types = [
            {"value": choice[0], "display": choice[1]}
            for choice in WorkflowStepNotificationConfig.EVENT_TYPE_CHOICES
        ]

        recipient_types = [
            {"value": choice[0], "display": choice[1]}
            for choice in WorkflowStepNotificationConfig.RECIPIENT_TYPE_CHOICES
        ]

        priorities = [
            {"value": "low", "display": "Low"},
            {"value": "normal", "display": "Normal"},
            {"value": "high", "display": "High"},
            {"value": "urgent", "display": "Urgent"},
        ]

        # Get all roles (Role model has no is_active field)
        roles = Role.objects.all().order_by("name")
        roles_serializer = RoleSimpleSerializer(roles, many=True)

        # Get active users
        users = (
            User.objects.filter(is_active=True, status="Active")
            .select_related("role")
            .order_by("email")
        )
        users_serializer = UserSimpleSerializer(users, many=True)

        # Get active notification templates
        templates = NotificationTemplate.objects.filter(is_active=True).order_by("name")
        templates_serializer = NotificationTemplateSimpleSerializer(
            templates, many=True
        )

        return Response(
            {
                "event_types": event_types,
                "recipient_types": recipient_types,
                "priorities": priorities,
                "roles": roles_serializer.data,
                "users": users_serializer.data,
                "templates": templates_serializer.data,
            }
        )

    @action(detail=False, methods=["post"])
    def preview(self, request):
        """
        Preview who will receive notifications based on configuration.

        POST /api/workflows/notification-configs/preview/

        Body:
        {
            "workflow_step_id": "uuid",
            "recipient_types": ["current_approver", "requester"],
            "custom_recipients": ["someone@example.com"]
        }

        Returns:
        {
            "to": [{user details}],
            "cc": [],
            "bcc": []
        }

        Not implemented yet - resolving recipient_types against a real
        WorkflowStepExecution requires an actual in-progress instance
        (see WorkflowNotifications._resolve_recipients in notifications.py),
        which doesn't exist for a hypothetical preview. Returns a stub.
        """
        return Response(
            {
                "message": "Preview functionality - to be implemented",
                "to": [],
                "cc": [],
                "bcc": [],
            }
        )
