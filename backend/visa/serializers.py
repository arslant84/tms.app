from rest_framework import serializers
from .models import VisaApplication, VisaApprovalStep, VisaDocument


class VisaApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisaApplication
        fields = '__all__'


class VisaApprovalStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisaApprovalStep
        fields = '__all__'


class VisaDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisaDocument
        fields = '__all__'
