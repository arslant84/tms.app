from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TravelInsightViewSet, TravelAnalyticsViewSet

router = DefaultRouter()
router.register(r'insights', TravelInsightViewSet)
router.register(r'analytics', TravelAnalyticsViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
