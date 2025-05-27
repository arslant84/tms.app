from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.contrib.auth import get_user_model

from .models import TravelRequestForm, ApprovalStep, TRFStatus, ApprovalStatus
from .serializers import (
    TravelRequestFormSerializer, 
    TravelRequestFormCreateSerializer,
    TravelRequestFormUpdateSerializer,
    ApprovalActionSerializer
)

User = get_user_model()


class TravelRequestFormViewSet(viewsets.ModelViewSet):
    queryset = TravelRequestForm.objects.all()
    serializer_class = TravelRequestFormSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['purpose', 'destination', 'requester__name']
    ordering_fields = ['created_at', 'departure_date', 'return_date', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        
        # Admin and managers can see all TRFs
        if user.is_admin or user.role in ['focal', 'hod', 'ticketing_clerk']:
            return TravelRequestForm.objects.all()
        
        # Regular users can only see their own TRFs
        return TravelRequestForm.objects.filter(requester=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TravelRequestFormCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return TravelRequestFormUpdateSerializer
        return TravelRequestFormSerializer
    
    def perform_create(self, serializer):
        serializer.save(requester=self.request.user, status=TRFStatus.DRAFT)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        trf = self.get_object()
        
        # Check if the TRF is in draft status
        if trf.status != TRFStatus.DRAFT:
            return Response(
                {'error': 'Only draft TRFs can be submitted'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if the requester is the current user
        if trf.requester != request.user:
            return Response(
                {'error': 'You can only submit your own TRFs'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update the TRF status
        trf.status = TRFStatus.PENDING_APPROVAL
        trf.save()
        
        # Create approval steps based on the department hierarchy
        # This is a simplified version - in a real app, you'd have a more complex approval chain
        # For now, we'll just add the HOD as the approver
        hod_users = User.objects.filter(role='hod')
        for hod in hod_users:
            ApprovalStep.objects.create(
                trf=trf,
                approver=hod,
                status=ApprovalStatus.PENDING
            )
        
        serializer = self.get_serializer(trf)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        trf = self.get_object()
        
        # Check if the TRF can be cancelled
        if trf.status in [TRFStatus.APPROVED, TRFStatus.REJECTED, TRFStatus.CANCELLED]:
            return Response(
                {'error': f'TRFs with status {trf.status} cannot be cancelled'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if the requester is the current user
        if trf.requester != request.user and not request.user.is_admin:
            return Response(
                {'error': 'You can only cancel your own TRFs'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update the TRF status
        trf.status = TRFStatus.CANCELLED
        trf.save()
        
        serializer = self.get_serializer(trf)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        trf = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data, context={'request': request, 'view': self})
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the approval step for the current user
        approval_step = trf.approval_chain.filter(approver=request.user).first()
        
        # Update the approval step
        approval_step.status = ApprovalStatus.APPROVED
        approval_step.comments = serializer.validated_data.get('comments', '')
        approval_step.save()
        
        # Check if all approval steps are completed
        all_approved = all(step.status == ApprovalStatus.APPROVED for step in trf.approval_chain.all())
        any_rejected = any(step.status == ApprovalStatus.REJECTED for step in trf.approval_chain.all())
        
        if all_approved:
            trf.status = TRFStatus.APPROVED
            trf.save()
        elif any_rejected:
            trf.status = TRFStatus.REJECTED
            trf.save()
        
        trf_serializer = self.get_serializer(trf)
        return Response(trf_serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        trf = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data, context={'request': request, 'view': self})
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the approval step for the current user
        approval_step = trf.approval_chain.filter(approver=request.user).first()
        
        # Update the approval step
        approval_step.status = ApprovalStatus.REJECTED
        approval_step.comments = serializer.validated_data.get('comments', '')
        approval_step.save()
        
        # Update the TRF status
        trf.status = TRFStatus.REJECTED
        trf.save()
        
        trf_serializer = self.get_serializer(trf)
        return Response(trf_serializer.data)
