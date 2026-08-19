from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    TravelRequestViewSet,
    TrfAdvanceAmountRequestedItemViewSet,
    TrfAdvanceBankDetailViewSet,
    TrfApprovalStepViewSet,
    TrfDailyMealSelectionViewSet,
    TrfItinerarySegmentViewSet,
    TrfMealProvisionViewSet,
    TrfPassportDetailViewSet,
)

# Create router and register all viewsets
router = DefaultRouter()
router.register(r"travel-requests", TravelRequestViewSet, basename="travel-request")
router.register(
    r"advance-amounts", TrfAdvanceAmountRequestedItemViewSet, basename="advance-amount"
)
router.register(r"bank-details", TrfAdvanceBankDetailViewSet, basename="bank-detail")
router.register(r"approval-steps", TrfApprovalStepViewSet, basename="approval-step")
router.register(r"daily-meals", TrfDailyMealSelectionViewSet, basename="daily-meal")
router.register(
    r"itinerary-segments", TrfItinerarySegmentViewSet, basename="itinerary-segment"
)
router.register(r"meal-provisions", TrfMealProvisionViewSet, basename="meal-provision")
router.register(
    r"passport-details", TrfPassportDetailViewSet, basename="passport-detail"
)

app_name = "trf"

urlpatterns = [
    path("", include(router.urls)),
]
