from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime

from .models import ExpenseClaim, ExpenseItem, ClaimsApprovalStep, ExpenseCategory
from workflows.router import WorkflowRouter
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

    def perform_create(self, serializer):
        """Create expense claim and start workflow if submitted"""
        user = self.request.user

        # Get status from request data, default to 'Draft' if not provided
        status_value = serializer.validated_data.get('status', 'Draft')

        # Save the expense claim
        expense_claim = serializer.save(user=user)

        # Start workflow if status is submitted (not Draft)
        if status_value in ['Pending', 'Pending Verification', 'Pending Line Manager', 'Pending HOD', 'Submitted']:
            try:
                workflow_instance = WorkflowRouter.start_workflow_for_request(
                    entity=expense_claim,
                    entity_type='expenseclaim',
                    initiated_by=user
                )

                if workflow_instance:
                    # Reload the expense claim to get the updated status from workflow
                    expense_claim.refresh_from_db()
                    print(f"✅ Workflow started for Expense Claim #{expense_claim.id}: Workflow Instance #{workflow_instance.id}")
                    print(f"✅ Status updated to: {expense_claim.status}")
                else:
                    print(f"⚠️ No active workflow configured for expenseclaim - using legacy approval system")
            except Exception as e:
                print(f"❌ Error starting workflow for Expense Claim #{expense_claim.id}: {str(e)}")
                # Don't fail the request creation if workflow fails
                pass

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
            # Use startswith to match workflow statuses like "Pending Line Manager"
            # when filter is "Pending"
            queryset = queryset.filter(status__istartswith=status_filter)

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
        if expense.status != 'Draft':
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

        # Update status to Pending
        expense.status = 'Pending'
        expense.save()

        # Start workflow using WorkflowRouter
        try:
            workflow_instance = WorkflowRouter.start_workflow_for_request(
                entity=expense,
                entity_type='expenseclaim',
                initiated_by=request.user
            )

            if workflow_instance:
                # Reload the expense claim to get the updated status from workflow
                expense.refresh_from_db()
                print(f"✅ Workflow started for Expense Claim #{expense.id}: Workflow Instance #{workflow_instance.id}")
                print(f"✅ Status updated to: {expense.status}")
            else:
                # Fallback to legacy approval system if no workflow configured
                print(f"⚠️ No active workflow configured - creating legacy approval step")
                ClaimsApprovalStep.objects.create(
                    claim=expense,
                    step_role='HOD',
                    step_name='HOD Approval',
                    status='Pending'
                )
                expense.status = 'Pending Verification'
                expense.save()
        except Exception as e:
            print(f"❌ Error starting workflow: {str(e)}")
            # Fallback to legacy system on error
            ClaimsApprovalStep.objects.create(
                claim=expense,
                step_role='HOD',
                step_name='HOD Approval',
                status='Pending'
            )
            expense.status = 'Pending Verification'
            expense.save()

        # Ensure we have the latest status before serializing
        expense.refresh_from_db()
        serializer = ExpenseClaimDetailSerializer(expense)
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
            'HOD': 'Under Review',
            'Finance': 'Approved'
        }

        if step_role in status_progression:
            expense.status = status_progression[step_role]
            expense.save()

            # Create next approval step if not final
            if expense.status != 'Approved':
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
        expense.status = 'Rejected'
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
        if expense.status in ['Approved', 'Paid']:
            return Response(
                {'error': 'Cannot cancel approved or paid expense claims'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status to Cancelled
        expense.status = 'Cancelled'
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
        if expense.status != 'Approved':
            return Response(
                {'error': 'Only approved expense claims can be marked as paid'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status
        expense.status = 'Paid'
        expense.save()

        serializer = self.get_serializer(expense)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='pending-approvals')
    def pending_approvals(self, request):
        """Get expense claims pending approval"""
        queryset = ExpenseClaim.objects.filter(
            status__in=['Submitted', 'Under Review', 'Pending', 'Pending Verification', 'Pending Line Manager', 'Pending HOD']
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
