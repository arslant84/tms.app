from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.contrib.auth import get_user_model
from datetime import datetime

from .models import ExpenseClaim, ExpenseItem, ClaimsApprovalStep, ExpenseStatus, ExpenseCategory
from .serializers import (
    ExpenseClaimSerializer,
    ExpenseClaimDetailSerializer,
    ExpenseClaimCreateSerializer,
    ExpenseClaimUpdateSerializer,
    ExpenseItemSerializer,
    ClaimsApprovalStepSerializer,
    ApprovalActionSerializer
)

User = get_user_model()


class ExpenseClaimViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Expense Claims

    Endpoints:
    - GET /api/expenses/claims/ - List all expense claims
    - POST /api/expenses/claims/ - Create a new expense claim
    - GET /api/expenses/claims/{id}/ - Retrieve expense claim details
    - PUT /api/expenses/claims/{id}/ - Update expense claim
    - PATCH /api/expenses/claims/{id}/ - Partial update
    - DELETE /api/expenses/claims/{id}/ - Delete expense claim
    - POST /api/expenses/claims/{id}/submit/ - Submit for approval
    - POST /api/expenses/claims/{id}/approve/ - Approve claim
    - POST /api/expenses/claims/{id}/reject/ - Reject claim
    - POST /api/expenses/claims/{id}/mark_as_paid/ - Mark as paid
    """
    queryset = ExpenseClaim.objects.all()
    serializer_class = ExpenseClaimSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use appropriate serializer based on action"""
        if self.action == 'retrieve':
            return ExpenseClaimDetailSerializer
        elif self.action == 'create':
            return ExpenseClaimCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ExpenseClaimUpdateSerializer
        return ExpenseClaimSerializer

    def get_queryset(self):
        """Filter expense claims based on query parameters and user role"""
        queryset = self.queryset.select_related('user', 'trf').prefetch_related('items')
        user = self.request.user

        # Regular users can only see their own expense claims
        # Admins and managers can see all
        if not (user.is_staff or user.is_superuser):
            # Check if user has approval role
            user_role = getattr(user, 'role', None)
            if user_role not in ['focal', 'hod', 'finance']:
                queryset = queryset.filter(user=user)

        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)

        # Filter by user
        user_id = self.request.query_params.get('user', None)
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Filter by TRF
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            queryset = queryset.filter(trf_id=trf_id)

        # Search across multiple fields
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(user__email__icontains=search)
            )

        return queryset.order_by('-created_at')

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit an expense claim for approval"""
        expense = self.get_object()

        # Check if the expense claim is in draft status
        if expense.status != ExpenseStatus.DRAFT:
            return Response(
                {'error': 'Only draft expense claims can be submitted'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if the user is the owner
        if expense.user != request.user:
            return Response(
                {'error': 'You can only submit your own expense claims'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate that expense has items
        if not expense.items.exists():
            return Response(
                {'error': 'Expense claim must have at least one item'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status
        expense.status = ExpenseStatus.SUBMITTED
        expense.save()

        # Create initial approval step
        ClaimsApprovalStep.objects.create(
            claim=expense,
            step_role='HOD',
            step_name='HOD Approval',
            status='Pending'
        )

        serializer = self.get_serializer(expense)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve an expense claim at current approval step"""
        expense = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        step_role = serializer.validated_data['step_role']
        comments = serializer.validated_data.get('comments', '')

        # Find or create approval step for this role
        approval_step, created = ClaimsApprovalStep.objects.get_or_create(
            claim=expense,
            step_role=step_role,
            defaults={
                'step_name': f'{step_role} Approval',
                'status': 'Pending'
            }
        )

        # Update approval step
        approval_step.status = 'Approved'
        approval_step.comments = comments
        approval_step.step_date = datetime.now()
        approval_step.save()

        # Update expense claim status based on approval workflow
        status_progression = {
            'HOD': 'UNDER_REVIEW',
            'Finance': 'APPROVED'
        }

        if step_role in status_progression:
            expense.status = status_progression[step_role]
            expense.save()

            # Create next approval step if not final
            if expense.status != ExpenseStatus.APPROVED:
                next_role = 'Finance' if step_role == 'HOD' else None
                if next_role:
                    ClaimsApprovalStep.objects.get_or_create(
                        claim=expense,
                        step_role=next_role,
                        defaults={
                            'step_name': f'{next_role} Approval',
                            'status': 'Pending'
                        }
                    )

        expense_serializer = ExpenseClaimDetailSerializer(expense)
        return Response(expense_serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject an expense claim"""
        expense = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        step_role = serializer.validated_data['step_role']
        comments = serializer.validated_data.get('comments', '')

        # Find or create approval step for this role
        approval_step, created = ClaimsApprovalStep.objects.get_or_create(
            claim=expense,
            step_role=step_role,
            defaults={
                'step_name': f'{step_role} Approval',
                'status': 'Pending'
            }
        )

        # Update approval step
        approval_step.status = 'Rejected'
        approval_step.comments = comments
        approval_step.step_date = datetime.now()
        approval_step.save()

        # Update expense claim status
        expense.status = ExpenseStatus.REJECTED
        expense.save()

        expense_serializer = ExpenseClaimDetailSerializer(expense)
        return Response(expense_serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an expense claim"""
        expense = self.get_object()

        # Check if the user is the owner
        if expense.user != request.user:
            return Response(
                {'error': 'You can only cancel your own expense claims'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if the expense claim can be cancelled
        if expense.status in [ExpenseStatus.APPROVED, ExpenseStatus.PAID]:
            return Response(
                {'error': 'Cannot cancel approved or paid expense claims'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status to CANCELLED (need to add this to ExpenseStatus enum)
        # For now, use REJECTED as a placeholder
        expense.status = ExpenseStatus.REJECTED
        expense.save()

        # Optionally create an approval step to track cancellation
        comments = request.data.get('comments', 'Cancelled by user')
        ClaimsApprovalStep.objects.create(
            claim=expense,
            step_role='User',
            step_name='Cancellation',
            status='Cancelled',
            comments=comments,
            step_date=datetime.now()
        )

        serializer = self.get_serializer(expense)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_as_paid(self, request, pk=None):
        """Mark an expense claim as paid (Finance role only)"""
        expense = self.get_object()

        # Only finance roles can mark as paid
        user_role = getattr(request.user, 'role', None)
        if not (request.user.is_staff or user_role == 'finance'):
            return Response(
                {'error': 'Only finance staff can mark expense claims as paid'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if the expense claim is approved
        if expense.status != ExpenseStatus.APPROVED:
            return Response(
                {'error': 'Only approved expense claims can be marked as paid'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status
        expense.status = ExpenseStatus.PAID
        expense.save()

        serializer = self.get_serializer(expense)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='pending-approvals')
    def pending_approvals(self, request):
        """Get expense claims pending approval"""
        queryset = ExpenseClaim.objects.filter(
            status__in=[ExpenseStatus.SUBMITTED, ExpenseStatus.UNDER_REVIEW]
        ).order_by('-created_at')

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ExpenseItemViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Expense Items"""
    queryset = ExpenseItem.objects.all()
    serializer_class = ExpenseItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter expense items by query parameters"""
        queryset = self.queryset

        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)

        date_from = self.request.query_params.get('date_from', None)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)

        date_to = self.request.query_params.get('date_to', None)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        return queryset.order_by('-date')


class ClaimsApprovalStepViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Claims Approval Steps"""
    queryset = ClaimsApprovalStep.objects.all()
    serializer_class = ClaimsApprovalStepSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter approval steps by claim"""
        queryset = self.queryset

        claim_id = self.request.query_params.get('claim', None)
        if claim_id:
            queryset = queryset.filter(claim_id=claim_id)

        return queryset.order_by('-created_at')
