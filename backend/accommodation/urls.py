from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .accommodation_booking_views import AccommodationBookingViewSet
from .accommodation_request_views import AccommodationRequestViewSet
from .accommodation_room_views import (
    AccommodationRoomViewSet,
    AccommodationStaffHouseViewSet,
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r"staff-houses", AccommodationStaffHouseViewSet, basename="staff-house")
router.register(r"rooms", AccommodationRoomViewSet, basename="room")
router.register(r"requests", AccommodationRequestViewSet, basename="request")
router.register(r"bookings", AccommodationBookingViewSet, basename="booking")

app_name = "accommodation"

urlpatterns = [
    path("", include(router.urls)),
]
