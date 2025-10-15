from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WorkflowTemplateViewSet,
    WorkflowStepViewSet,
    WorkflowConditionViewSet,
    WorkflowInstanceViewSet,
    WorkflowStepExecutionViewSet,
    WorkflowDelegationViewSet,
    WorkflowAuditLogViewSet
)

router = DefaultRouter()
router.register(r'templates', WorkflowTemplateViewSet, basename='workflow-template')
router.register(r'steps', WorkflowStepViewSet, basename='workflow-step')
router.register(r'conditions', WorkflowConditionViewSet, basename='workflow-condition')
router.register(r'instances', WorkflowInstanceViewSet, basename='workflow-instance')
router.register(r'executions', WorkflowStepExecutionViewSet, basename='workflow-execution')
router.register(r'delegations', WorkflowDelegationViewSet, basename='workflow-delegation')
router.register(r'audit-logs', WorkflowAuditLogViewSet, basename='workflow-audit-log')

urlpatterns = [
    path('', include(router.urls)),
]
