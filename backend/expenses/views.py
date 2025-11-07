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
from utils.request_id_generator import generate_request_id
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

        # Generate request number if it doesn't exist
        if not expense.request_number:
            try:
                # CLM uses special format with two unique IDs (no context needed)
                request_number = generate_request_id('CLM', '')
                expense.request_number = request_number
                print(f"✅ Generated request number for Expense Claim #{expense.id}: {request_number}")
            except Exception as e:
                print(f"❌ Error generating request number: {str(e)}")
                import traceback
                traceback.print_exc()
                # Fallback to simple format
                expense.request_number = f"CLM-{datetime.now().strftime('%Y%m%d-%H%M')}-CLM-{expense.id}"
                print(f"⚠️ Using fallback request number: {expense.request_number}")

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
        """Approve an expense claim using WorkflowEngine"""
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType

        expense = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        step_role = serializer.validated_data['step_role']
        comments = serializer.validated_data.get('comments', '')

        try:
            # Get the workflow instance for this expense claim
            content_type = ContentType.objects.get_for_model(expense)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=expense.id,
                status='in_progress'
            ).first()

            print(f"[DEBUG] Approving Claim #{expense.id}")
            print(f"[DEBUG] User: {request.user.email}, is_staff={request.user.is_staff}, is_superuser={request.user.is_superuser}")
            print(f"[DEBUG] Workflow instance found: {workflow_instance is not None}")

            if workflow_instance:
                # Find the current pending step
                current_step = workflow_instance.step_executions.filter(
                    status='pending'
                ).order_by('workflow_step__step_order').first()

                print(f"[DEBUG] Pending step found: {current_step is not None}")
                if current_step:
                    print(f"[DEBUG] Step: {current_step.workflow_step.step_name}, assigned_to: {current_step.assigned_to}")

                if current_step:
                    # Use workflow engine to process approval
                    result = WorkflowEngine.process_action(
                        step_execution_id=current_step.id,
                        action='approve',
                        actioned_by=request.user,
                        comments=comments
                    )

                    # Reload to get updated status
                    expense.refresh_from_db()

                    # Update legacy approval step for backward compatibility
                    approval_step, created = ClaimsApprovalStep.objects.get_or_create(
                        claim=expense,
                        step_role=step_role,
                        defaults={
                            'step_name': f'{step_role} Approval',
                            'status': 'Pending'
                        }
                    )
                    approval_step.status = 'Approved'
                    approval_step.comments = comments
                    approval_step.step_date = timezone.now()
                    approval_step.save()

                    expense_serializer = ExpenseClaimDetailSerializer(expense)
                    return Response(expense_serializer.data)
                else:
                    return Response(
                        {'error': 'No pending approval step found'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Fallback to legacy approval logic
                print(f"⚠️ No workflow instance found for Expense Claim #{expense.id}, using legacy approval")

                approval_step, created = ClaimsApprovalStep.objects.get_or_create(
                    claim=expense,
                    step_role=step_role,
                    defaults={
                        'step_name': f'{step_role} Approval',
                        'status': 'Pending'
                    }
                )

                approval_step.status = 'Approved'
                approval_step.comments = comments
                approval_step.step_date = timezone.now()
                approval_step.save()

                status_progression = {
                    'Department Focal': 'Pending HOD',
                    'HOD': 'Approved'
                }

                if step_role in status_progression:
                    expense.status = status_progression[step_role]
                    expense.save()

                expense_serializer = ExpenseClaimDetailSerializer(expense)
                return Response(expense_serializer.data)

        except ValueError as e:
            # ValueError is raised by WorkflowEngine for authorization failures
            print(f"❌ ValueError in approve workflow: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print(f"❌ Error in approve workflow: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Failed to process approval: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject an expense claim using WorkflowEngine"""
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType

        expense = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        step_role = serializer.validated_data['step_role']
        comments = serializer.validated_data.get('comments', '')

        try:
            content_type = ContentType.objects.get_for_model(expense)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=expense.id,
                status='in_progress'
            ).first()

            if workflow_instance:
                current_step = workflow_instance.step_executions.filter(
                    status='pending'
                ).order_by('workflow_step__step_order').first()

                if current_step:
                    result = WorkflowEngine.process_action(
                        step_execution_id=current_step.id,
                        action='reject',
                        actioned_by=request.user,
                        comments=comments
                    )

                    expense.refresh_from_db()

                    approval_step, created = ClaimsApprovalStep.objects.get_or_create(
                        claim=expense,
                        step_role=step_role,
                        defaults={
                            'step_name': f'{step_role} Approval',
                            'status': 'Pending'
                        }
                    )
                    approval_step.status = 'Rejected'
                    approval_step.comments = comments
                    approval_step.step_date = timezone.now()
                    approval_step.save()

                    expense_serializer = ExpenseClaimDetailSerializer(expense)
                    return Response(expense_serializer.data)
            else:
                # Fallback to legacy rejection
                approval_step, created = ClaimsApprovalStep.objects.get_or_create(
                    claim=expense,
                    step_role=step_role,
                    defaults={
                        'step_name': f'{step_role} Approval',
                        'status': 'Pending'
                    }
                )

                approval_step.status = 'Rejected'
                approval_step.comments = comments
                approval_step.step_date = timezone.now()
                approval_step.save()

                expense.status = 'Rejected'
                expense.save()

                expense_serializer = ExpenseClaimDetailSerializer(expense)
                return Response(expense_serializer.data)

        except Exception as e:
            print(f"❌ Error in reject workflow: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Failed to process rejection: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
            step_date=timezone.now()
        )

        serializer = self.get_serializer(expense)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='mark-as-paid')
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

        # Update status and payment details
        expense.status = 'Paid'
        expense.payment_method = request.data.get('payment_method', 'BANK_TRANSFER')
        expense.cheque_receipt_no = request.data.get('cheque_receipt_no')
        expense.payment_date = request.data.get('payment_date')
        expense.save()

        # Create approval step for payment record
        comments = request.data.get('comments', 'Payment processed')
        ClaimsApprovalStep.objects.create(
            claim=expense,
            step_role='Finance',
            step_name='Payment Processing',
            status='Paid',
            comments=comments,
            step_date=timezone.now()
        )

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
