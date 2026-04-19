"""
Combined Request URL Configuration

URL routing for the Combined Request API.
Provides endpoints for managing combined travel, transport, accommodation, and visa requests.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CombinedRequestViewSet

router = DefaultRouter()
router.register(r'combined-requests', CombinedRequestViewSet, basename='combined-request')

urlpatterns = [
    path('', include(router.urls)),
]
