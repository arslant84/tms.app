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
from .views_notification_config import WorkflowStepNotificationConfigViewSet

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
router.register(
    r"notification-configs",
    WorkflowStepNotificationConfigViewSet,
    basename="workflow-step-notification-config",
)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "eligible-approvers/<str:entity_type>/",
        get_eligible_approvers,
        name="eligible-approvers",
    ),
]
