from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    TransportApprovalStepViewSet,
    TransportRequestViewSet,
    VehicleAssignmentViewSet,
)

router = DefaultRouter()
router.register(r"requests", TransportRequestViewSet, basename="transport-request")
router.register(
    r"approval-steps", TransportApprovalStepViewSet, basename="transport-approval-step"
)
router.register(
    r"vehicle-assignments", VehicleAssignmentViewSet, basename="vehicle-assignment"
)

urlpatterns = [
    path("", include(router.urls)),
]
