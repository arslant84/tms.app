from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FlightBookingViewSet

router = DefaultRouter()
router.register(r"flights", FlightBookingViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
