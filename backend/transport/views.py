from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from datetime import datetime

from .models import (
    TransportRequest, TransportSegment, TransportApprovalStep, VehicleAssignment
)
from .serializers import (
    TransportRequestSerializer, TransportRequestDetailSerializer,
    TransportRequestCreateSerializer, TransportRequestUpdateSerializer,
    TransportApprovalStepSerializer, VehicleAssignmentSerializer,
    ApprovalActionSerializer
)
from workflows.router import WorkflowRouter


class TransportRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing transport requests
    Supports CRUD operations and custom actions for workflow
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Get queryset based on user role and filters
        """
        user = self.request.user
        queryset = TransportRequest.objects.all()

        # Filter by user role
        if not user.is_staff:
            # Regular users see their own requests
            queryset = queryset.filter(requestor=user)

        # Query parameter filters
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            # Use startswith to match workflow statuses like "Pending Line Manager"
            # when filter is "Pending"
            queryset = queryset.filter(status__istartswith=status_filter)

        transport_type = self.request.query_params.get('transport_type', None)
        if transport_type:
            queryset = queryset.filter(transport_type=transport_type)

        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            queryset = queryset.filter(trf_id=trf_id)

        requestor_id = self.request.query_params.get('requestor', None)
        if requestor_id:
            queryset = queryset.filter(requestor_id=requestor_id)

        # Date range filters
        from_date = self.request.query_params.get('from_date', None)
        to_date = self.request.query_params.get('to_date', None)
        if from_date:
            queryset = queryset.filter(created_at__gte=from_date)
        if to_date:
            queryset = queryset.filter(created_at__lte=to_date)

        # Search filter
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(purpose__icontains=search) |
                Q(requestor__email__icontains=search) |
                Q(requestor__first_name__icontains=search) |
                Q(requestor__last_name__icontains=search)
            )

        return queryset.select_related('requestor', 'trf').prefetch_related(
            'segments', 'approval_steps', 'vehicle_assignments'
        )

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'retrieve':
            return TransportRequestDetailSerializer
        elif self.action == 'create':
            return TransportRequestCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TransportRequestUpdateSerializer
        return TransportRequestSerializer

    def perform_create(self, serializer):
        """Set requestor to current user and auto-populate requestor info"""
        user = self.request.user

        # Auto-populate requestor information if not provided
        validated_data = serializer.validated_data
        if not validated_data.get('requestor_name'):
            validated_data['requestor_name'] = user.get_full_name() or user.email
        if not validated_data.get('staff_id'):
            validated_data['staff_id'] = getattr(user, 'employee_id', '') or getattr(user, 'staff_id', '')
        if not validated_data.get('department'):
            validated_data['department'] = getattr(user, 'department', '')
        if not validated_data.get('position'):
            validated_data['position'] = getattr(user, 'position', '') or getattr(user, 'job_title', '')

        # Get status from request data, default to 'Draft' if not provided
        status_value = validated_data.get('status', 'Draft')

        # Set submitted_at timestamp if status is being submitted (not Draft)
        extra_kwargs = {}
        if status_value in ['Pending', 'Pending Department Focal', 'Pending Line Manager', 'Pending HOD', 'Submitted']:
            extra_kwargs['submitted_at'] = timezone.now()

        # Save the transport request
        transport_request = serializer.save(requestor=user, **extra_kwargs)

        # Start workflow if status is submitted (not Draft)
        if status_value in ['Pending', 'Pending Department Focal', 'Pending Line Manager', 'Pending HOD', 'Submitted']:
            try:
                workflow_instance = WorkflowRouter.start_workflow_for_request(
                    entity=transport_request,
                    entity_type='transportrequest',
                    initiated_by=user
                )

                if workflow_instance:
                    # Reload the transport request to get the updated status from workflow
                    transport_request.refresh_from_db()
                    print(f"✅ Workflow started for Transport Request #{transport_request.id}: Workflow Instance #{workflow_instance.id}")
                    print(f"✅ Status updated to: {transport_request.status}")
                else:
                    print(f"⚠️ No active workflow configured for transportrequest - using legacy approval system")
            except Exception as e:
                print(f"❌ Error starting workflow for Transport Request #{transport_request.id}: {str(e)}")
                # Don't fail the request creation if workflow fails
                pass

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """
        Submit a transport request for approval
        Changes status from Draft to Pending and starts workflow
        """
        transport_request = self.get_object()

        # Validate requestor
        if transport_request.requestor != request.user:
            return Response(
                {'error': 'Only the requestor can submit this transport request'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate status
        if transport_request.status != 'Draft':
            return Response(
                {'error': f'Cannot submit transport request with status {transport_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate has at least one transport detail
        if not transport_request.transport_details or len(transport_request.transport_details) == 0:
            return Response(
                {'error': 'Transport request must have at least one transport detail'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status and submitted_at
        transport_request.status = 'Pending'
        transport_request.submitted_at = timezone.now()
        transport_request.save()

        # Start workflow using WorkflowRouter
        try:
            workflow_instance = WorkflowRouter.start_workflow_for_request(
                entity=transport_request,
                entity_type='transportrequest',
                initiated_by=request.user
            )

            if workflow_instance:
                # Reload the transport request to get the updated status from workflow
                transport_request.refresh_from_db()
                print(f"✅ Workflow started for Transport Request #{transport_request.id}: Workflow Instance #{workflow_instance.id}")
                print(f"✅ Status updated to: {transport_request.status}")
            else:
                # Fallback to legacy approval system if no workflow configured
                print(f"⚠️ No active workflow configured - creating legacy approval step")
                TransportApprovalStep.objects.create(
                    transport_request=transport_request,
                    step_role='HOD',
                    step_name='HOD Approval',
                    status='Pending'
                )
                transport_request.status = 'Pending Department Focal'
                transport_request.save()
        except Exception as e:
            print(f"❌ Error starting workflow: {str(e)}")
            # Fallback to legacy system on error
            TransportApprovalStep.objects.create(
                transport_request=transport_request,
                step_role='HOD',
                step_name='HOD Approval',
                status='Pending'
            )
            transport_request.status = 'Pending Department Focal'
            transport_request.save()

        # Ensure we have the latest status before serializing
        transport_request.refresh_from_db()
        serializer = TransportRequestDetailSerializer(transport_request)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve a transport request at current approval step
        Progresses through workflow: HOD → Admin → Completed
        """
        transport_request = self.get_object()
        user = request.user

        # Get user role
        user_role = user.role.name if hasattr(user, 'role') and user.role else None

        # Validate status
        if transport_request.status not in ['Pending', 'Approved']:
            return Response(
                {'error': f'Cannot approve transport request with status {transport_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get current pending approval step
        current_step = transport_request.approval_steps.filter(status='Pending').first()

        if not current_step:
            return Response(
                {'error': 'No pending approval step found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate user has permission for this step
        if not user.is_staff and user_role != current_step.step_role:
            return Response(
                {'error': f'You do not have permission to approve at step {current_step.step_role}'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get approval action data
        action_serializer = ApprovalActionSerializer(
            data=request.data,
            context={'action_type': 'approve'}
        )
        action_serializer.is_valid(raise_exception=True)
        comments = action_serializer.validated_data.get('comments', '')

        # Update current step
        current_step.status = 'Approved'
        current_step.step_date = timezone.now()
        current_step.comments = comments
        current_step.save()

        # Determine next step or completion
        status_progression = {
            'HOD': 'Approved',  # After HOD approval, status becomes Approved (awaiting admin assignment)
            'Admin': 'Completed'  # After Admin processes, status becomes Completed
        }

        next_status = status_progression.get(current_step.step_role)

        if next_status:
            transport_request.status = next_status
            transport_request.save()

            # Create next approval step if needed
            if current_step.step_role == 'HOD':
                TransportApprovalStep.objects.create(
                    transport_request=transport_request,
                    step_role='Admin',
                    step_name='Admin Processing',
                    status='Pending'
                )

        serializer = TransportRequestDetailSerializer(transport_request)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject a transport request at current approval step
        """
        transport_request = self.get_object()
        user = request.user

        # Get user role
        user_role = user.role.name if hasattr(user, 'role') and user.role else None

        # Validate status
        if transport_request.status not in ['Pending', 'Approved']:
            return Response(
                {'error': f'Cannot reject transport request with status {transport_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get current pending approval step
        current_step = transport_request.approval_steps.filter(status='Pending').first()

        if not current_step:
            return Response(
                {'error': 'No pending approval step found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate user has permission for this step
        if not user.is_staff and user_role != current_step.step_role:
            return Response(
                {'error': f'You do not have permission to reject at step {current_step.step_role}'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get approval action data
        action_serializer = ApprovalActionSerializer(
            data=request.data,
            context={'action_type': 'reject'}
        )
        action_serializer.is_valid(raise_exception=True)
        comments = action_serializer.validated_data.get('comments', '')

        # Update current step
        current_step.status = 'Rejected'
        current_step.step_date = timezone.now()
        current_step.comments = comments
        current_step.save()

        # Update transport request status
        transport_request.status = 'Rejected'
        transport_request.save()

        serializer = TransportRequestDetailSerializer(transport_request)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel a transport request (by requestor only)
        """
        transport_request = self.get_object()

        # Validate requestor
        if transport_request.requestor != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Only the requestor or admin can cancel this transport request'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate status
        if transport_request.status in ['Completed', 'Cancelled']:
            return Response(
                {'error': f'Cannot cancel transport request with status {transport_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status
        transport_request.status = 'Cancelled'
        transport_request.save()

        serializer = TransportRequestDetailSerializer(transport_request)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """
        Get all transport requests for the current user
        """
        queryset = self.get_queryset().filter(requestor=request.user)
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='pending-approvals')
    def pending_approvals(self, request):
        """
        Get all transport requests pending approval by current user's role
        """
        user = request.user
        user_role = user.role.name if hasattr(user, 'role') and user.role else None

        if not user_role and not user.is_staff:
            return Response(
                {'error': 'User does not have an assigned role'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get transport requests with pending approval steps for user's role
        queryset = self.get_queryset().filter(
            approval_steps__step_role=user_role,
            approval_steps__status='Pending'
        ).distinct()

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# Deprecated - TransportSegment model replaced with JSON field transport_details
# class TransportSegmentViewSet(viewsets.ModelViewSet):
#     """
#     ViewSet for managing transport segments
#     """
#     queryset = TransportSegment.objects.all()
#     serializer_class = TransportSegmentSerializer
#     permission_classes = [IsAuthenticated]
#
#     def get_queryset(self):
#         """Filter segments by transport request if specified"""
#         queryset = super().get_queryset()
#         transport_request_id = self.request.query_params.get('transport_request', None)
#
#         if transport_request_id:
#             queryset = queryset.filter(transport_request_id=transport_request_id)
#
#         return queryset.select_related('transport_request', 'transport_request__requestor')
#
#     def perform_create(self, serializer):
#         """Validate transport request is in Draft status"""
#         transport_request = serializer.validated_data['transport_request']
#
#         if transport_request.status not in ['Draft', 'Rejected']:
#             raise serializers.ValidationError(
#                 f'Cannot add segments to transport request with status {transport_request.status}'
#             )
#
#         serializer.save()


class TransportApprovalStepViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for transport approval steps
    """
    queryset = TransportApprovalStep.objects.all()
    serializer_class = TransportApprovalStepSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter approval steps by transport request if specified"""
        queryset = super().get_queryset()
        transport_request_id = self.request.query_params.get('transport_request', None)

        if transport_request_id:
            queryset = queryset.filter(transport_request_id=transport_request_id)

        return queryset.select_related('transport_request')


class VehicleAssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing vehicle assignments (admin only)
    """
    queryset = VehicleAssignment.objects.all()
    serializer_class = VehicleAssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by transport request and status"""
        queryset = super().get_queryset()

        transport_request_id = self.request.query_params.get('transport_request', None)
        if transport_request_id:
            queryset = queryset.filter(transport_request_id=transport_request_id)

        assignment_status = self.request.query_params.get('status', None)
        if assignment_status:
            queryset = queryset.filter(status=assignment_status)

        vehicle_number = self.request.query_params.get('vehicle_number', None)
        if vehicle_number:
            queryset = queryset.filter(vehicle_number__icontains=vehicle_number)

        return queryset.select_related('transport_request', 'assigned_by')

    def perform_create(self, serializer):
        """
        Create vehicle assignment
        Only admin/staff can assign vehicles
        """
        if not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only admin can assign vehicles')

        serializer.save(assigned_by=self.request.user)

    @action(detail=True, methods=['post'])
    def start_journey(self, request, pk=None):
        """
        Mark vehicle assignment as In Progress and record starting odometer
        """
        assignment = self.get_object()

        if assignment.status != 'Assigned':
            return Response(
                {'error': f'Cannot start journey for assignment with status {assignment.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        odometer_start = request.data.get('odometer_start')
        if not odometer_start:
            return Response(
                {'error': 'Starting odometer reading is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        assignment.status = 'In Progress'
        assignment.odometer_start = odometer_start
        assignment.save()

        serializer = self.get_serializer(assignment)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def complete_journey(self, request, pk=None):
        """
        Mark vehicle assignment as Completed and record ending odometer and fuel used
        """
        assignment = self.get_object()

        if assignment.status != 'In Progress':
            return Response(
                {'error': f'Cannot complete journey for assignment with status {assignment.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        odometer_end = request.data.get('odometer_end')
        fuel_used = request.data.get('fuel_used_liters')

        if not odometer_end:
            return Response(
                {'error': 'Ending odometer reading is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if odometer_end < assignment.odometer_start:
            return Response(
                {'error': 'Ending odometer cannot be less than starting odometer'},
                status=status.HTTP_400_BAD_REQUEST
            )

        assignment.status = 'Completed'
        assignment.odometer_end = odometer_end
        assignment.fuel_used_liters = fuel_used
        assignment.completion_date = timezone.now()
        assignment.save()

        serializer = self.get_serializer(assignment)
        return Response(serializer.data)
