"""
VisaApprovalStepViewSet and VisaDocumentViewSet - small, trivial viewsets
split out of visa/views.py (see docs/CODEBASE_REFACTOR_ROADMAP.md item 8)
alongside the dominant VisaApplicationViewSet. Pure file move, no logic
changed.
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import VisaApprovalStep, VisaDocument
from .serializers import VisaApprovalStepSerializer, VisaDocumentSerializer


class VisaApprovalStepViewSet(viewsets.ModelViewSet):
    """ViewSet for visa approval steps"""

    queryset = VisaApprovalStep.objects.all().order_by("step_date")
    serializer_class = VisaApprovalStepSerializer
    permission_classes = [IsAuthenticated]


class VisaDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for visa documents"""

    queryset = VisaDocument.objects.all().order_by("-uploaded_at")
    serializer_class = VisaDocumentSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="by-visa/(?P<visa_id>[^/.]+)")
    def by_visa(self, request, visa_id=None):
        """Get all documents for a specific visa application"""
        documents = self.queryset.filter(visa_id=visa_id)
        serializer = self.get_serializer(documents, many=True)
        return Response(serializer.data)
