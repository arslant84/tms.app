from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import VisaApplication, VisaApprovalStep, VisaDocument
from .serializers import VisaApplicationSerializer, VisaApprovalStepSerializer, VisaDocumentSerializer


class VisaApplicationViewSet(viewsets.ModelViewSet):
    queryset = VisaApplication.objects.all()
    serializer_class = VisaApplicationSerializer

    @action(detail=False, methods=['get'], url_path='pending-approvals')
    def pending_approvals(self, request):
        """Get visa applications pending approval"""
        queryset = VisaApplication.objects.filter(
            status='Pending'
        ).order_by('-created_at')

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class VisaApprovalStepViewSet(viewsets.ModelViewSet):
    queryset = VisaApprovalStep.objects.all()
    serializer_class = VisaApprovalStepSerializer


class VisaDocumentViewSet(viewsets.ModelViewSet):
    queryset = VisaDocument.objects.all()
    serializer_class = VisaDocumentSerializer
