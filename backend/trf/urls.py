from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TravelRequestFormViewSet

router = DefaultRouter()
router.register(r'trfs', TravelRequestFormViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
