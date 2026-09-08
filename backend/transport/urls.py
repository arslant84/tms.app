from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .transport_assignment_views import (
    TransportApprovalStepViewSet,
    VehicleAssignmentViewSet,
)
from .transport_request_views import TransportRequestViewSet

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
