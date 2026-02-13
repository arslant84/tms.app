from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import VisaApplicationViewSet, VisaApprovalStepViewSet, VisaDocumentViewSet

router = DefaultRouter()
router.register(r'applications', VisaApplicationViewSet)
router.register(r'approval-steps', VisaApprovalStepViewSet)
router.register(r'documents', VisaDocumentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
