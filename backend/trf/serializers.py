from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import TravelRequestForm, ApprovalStep, TRFStatus, ApprovalStatus

User = get_user_model()


class ApprovalStepSerializer(serializers.ModelSerializer):
    approver_name = serializers.ReadOnlyField()
    approver_id = serializers.ReadOnlyField()
    
    class Meta:
        model = ApprovalStep
        fields = ['id', 'approver', 'approver_name', 'approver_id', 'status', 'comments', 'timestamp']
        read_only_fields = ['id', 'timestamp']


class TravelRequestFormSerializer(serializers.ModelSerializer):
    approval_chain = ApprovalStepSerializer(many=True, read_only=True)
    requester_name = serializers.ReadOnlyField()
    requester_id = serializers.ReadOnlyField()
    
    class Meta:
        model = TravelRequestForm
        fields = [
            'id', 'requester', 'requester_name', 'requester_id', 'purpose', 
            'destination', 'departure_date', 'return_date', 'travel_type', 
            'accommodation_required', 'estimated_cost', 'status', 'notes', 
            'created_at', 'updated_at', 'approval_chain'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TravelRequestFormCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelRequestForm
        fields = [
            'id', 'purpose', 'destination', 'departure_date', 'return_date', 
            'travel_type', 'accommodation_required', 'estimated_cost', 'notes'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        user = self.context['request'].user
        trf = TravelRequestForm.objects.create(requester=user, **validated_data)
        return trf


class TravelRequestFormUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelRequestForm
        fields = [
            'purpose', 'destination', 'departure_date', 'return_date', 
            'travel_type', 'accommodation_required', 'estimated_cost', 'notes'
        ]
    
    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        if instance and instance.status != TRFStatus.DRAFT:
            raise serializers.ValidationError("Only draft TRFs can be updated.")
        return attrs


class ApprovalActionSerializer(serializers.Serializer):
    comments = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        request = self.context.get('request')
        view = self.context.get('view')
        trf = view.get_object()
        
        # Check if the user is in the approval chain
        approval_step = trf.approval_chain.filter(approver=request.user).first()
        if not approval_step:
            raise serializers.ValidationError("You are not in the approval chain for this TRF.")
        
        # Check if the approval step is pending
        if approval_step.status != ApprovalStatus.PENDING:
            raise serializers.ValidationError("This TRF has already been processed by you.")
        
        return attrs
