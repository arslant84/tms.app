from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import FlightBookingViewSet, HotelBookingViewSet

router = DefaultRouter()
router.register(r'flights', FlightBookingViewSet)
router.register(r'hotels', HotelBookingViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
