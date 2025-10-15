from rest_framework import viewsets
from .models import VisaApplication, VisaApprovalStep, VisaDocument
from .serializers import VisaApplicationSerializer, VisaApprovalStepSerializer, VisaDocumentSerializer


class VisaApplicationViewSet(viewsets.ModelViewSet):
    queryset = VisaApplication.objects.all()
    serializer_class = VisaApplicationSerializer


class VisaApprovalStepViewSet(viewsets.ModelViewSet):
    queryset = VisaApprovalStep.objects.all()
    serializer_class = VisaApprovalStepSerializer


class VisaDocumentViewSet(viewsets.ModelViewSet):
    queryset = VisaDocument.objects.all()
    serializer_class = VisaDocumentSerializer
