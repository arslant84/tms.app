from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.contrib.auth import get_user_model

from .models import ExpenseClaim, ExpenseItem, ExpenseApproval, ExpenseStatus, ExpenseCategory
from .serializers import (
    ExpenseClaimSerializer, 
    ExpenseClaimCreateSerializer,
    ExpenseClaimUpdateSerializer,
    ExpenseApprovalActionSerializer
)
from trf.models import ApprovalStatus

User = get_user_model()


class ExpenseClaimViewSet(viewsets.ModelViewSet):
    queryset = ExpenseClaim.objects.all()
    serializer_class = ExpenseClaimSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'user__name']
    ordering_fields = ['created_at', 'expense_date', 'total_amount', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        
        # Admin and managers can see all expense claims
        if user.is_admin or user.role in ['focal', 'hod']:
            return ExpenseClaim.objects.all()
        
        # Regular users can only see their own expense claims
        return ExpenseClaim.objects.filter(user=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ExpenseClaimCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return ExpenseClaimUpdateSerializer
        return ExpenseClaimSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status=ExpenseStatus.DRAFT)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        expense = self.get_object()
        
        # Check if the expense claim is in draft status
        if expense.status != ExpenseStatus.DRAFT:
            return Response(
                {'error': 'Only draft expense claims can be submitted'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if the user is the owner of the expense claim
        if expense.user != request.user:
            return Response(
                {'error': 'You can only submit your own expense claims'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update the expense claim status
        expense.status = ExpenseStatus.UNDER_REVIEW
        expense.save()
        
        # Create approval steps based on the department hierarchy
        # This is a simplified version - in a real app, you'd have a more complex approval chain
        # For now, we'll just add the HOD as the approver
        hod_users = User.objects.filter(role='hod')
        for hod in hod_users:
            ExpenseApproval.objects.create(
                expense=expense,
                approver=hod,
                status=ApprovalStatus.PENDING
            )
        
        serializer = self.get_serializer(expense)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        expense = self.get_object()
        serializer = ExpenseApprovalActionSerializer(data=request.data, context={'request': request, 'view': self})
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the approval step for the current user
        approval_step = expense.approval_chain.filter(approver=request.user).first()
        
        # Update the approval step
        approval_step.status = ApprovalStatus.APPROVED
        approval_step.comments = serializer.validated_data.get('comments', '')
        approval_step.save()
        
        # Check if all approval steps are completed
        all_approved = all(step.status == ApprovalStatus.APPROVED for step in expense.approval_chain.all())
        any_rejected = any(step.status == ApprovalStatus.REJECTED for step in expense.approval_chain.all())
        
        if all_approved:
            expense.status = ExpenseStatus.APPROVED
            expense.save()
        elif any_rejected:
            expense.status = ExpenseStatus.REJECTED
            expense.save()
        
        expense_serializer = self.get_serializer(expense)
        return Response(expense_serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        expense = self.get_object()
        serializer = ExpenseApprovalActionSerializer(data=request.data, context={'request': request, 'view': self})
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the approval step for the current user
        approval_step = expense.approval_chain.filter(approver=request.user).first()
        
        # Update the approval step
        approval_step.status = ApprovalStatus.REJECTED
        approval_step.comments = serializer.validated_data.get('comments', '')
        approval_step.save()
        
        # Update the expense claim status
        expense.status = ExpenseStatus.REJECTED
        expense.save()
        
        expense_serializer = self.get_serializer(expense)
        return Response(expense_serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_as_paid(self, request, pk=None):
        expense = self.get_object()
        
        # Only admins and finance roles can mark as paid
        if not (request.user.is_admin or request.user.role in ['focal']):
            return Response(
                {'error': 'Only admins and finance roles can mark expense claims as paid'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if the expense claim is approved
        if expense.status != ExpenseStatus.APPROVED:
            return Response(
                {'error': 'Only approved expense claims can be marked as paid'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update the expense claim status
        expense.status = ExpenseStatus.PAID
        expense.save()
        
        serializer = self.get_serializer(expense)
        return Response(serializer.data)
