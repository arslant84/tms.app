from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TransportRequestViewSet,
    # TransportSegmentViewSet,  # Deprecated - now using JSON field
    TransportApprovalStepViewSet,
    VehicleAssignmentViewSet
)

router = DefaultRouter()
router.register(r'requests', TransportRequestViewSet, basename='transport-request')
# router.register(r'segments', TransportSegmentViewSet, basename='transport-segment')  # Deprecated
router.register(r'approval-steps', TransportApprovalStepViewSet, basename='transport-approval-step')
router.register(r'vehicle-assignments', VehicleAssignmentViewSet, basename='vehicle-assignment')

urlpatterns = [
    path('', include(router.urls)),
]
