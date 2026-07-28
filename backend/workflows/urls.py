from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    WorkflowAuditLogViewSet,
    WorkflowConditionViewSet,
    WorkflowDelegationViewSet,
    WorkflowInstanceViewSet,
    WorkflowStepExecutionViewSet,
    WorkflowStepViewSet,
    WorkflowTemplateViewSet,
    get_eligible_approvers,
)

# NOTE: WorkflowStepNotificationConfigViewSet (views_notification_config.py) is
# NOT registered here - it has 4 missing serializer imports
# (WorkflowStepNotificationConfigListSerializer, RoleSimpleSerializer,
# UserSimpleSerializer, NotificationTemplateSimpleSerializer don't exist in
# serializers.py) and would crash the app at import time if wired in as-is.
# See docs/APP_WIDE_GAPS_FIX_ROADMAP.md for the finding - needs a real
# implementation decision before registering, not a mechanical fix.

router = DefaultRouter()
router.register(r"templates", WorkflowTemplateViewSet, basename="workflow-template")
router.register(r"steps", WorkflowStepViewSet, basename="workflow-step")
router.register(r"conditions", WorkflowConditionViewSet, basename="workflow-condition")
router.register(r"instances", WorkflowInstanceViewSet, basename="workflow-instance")
router.register(
    r"executions", WorkflowStepExecutionViewSet, basename="workflow-execution"
)
router.register(
    r"delegations", WorkflowDelegationViewSet, basename="workflow-delegation"
)
router.register(r"audit-logs", WorkflowAuditLogViewSet, basename="workflow-audit-log")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "eligible-approvers/<str:entity_type>/",
        get_eligible_approvers,
        name="eligible-approvers",
    ),
]
