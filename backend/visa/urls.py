from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .visa_application_views import VisaApplicationViewSet
from .visa_document_views import VisaApprovalStepViewSet, VisaDocumentViewSet

router = DefaultRouter()
router.register(r"applications", VisaApplicationViewSet)
router.register(r"approval-steps", VisaApprovalStepViewSet)
router.register(r"documents", VisaDocumentViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
