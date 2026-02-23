import logging
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from datetime import datetime

from accounts.utils import is_module_admin, can_approve

logger = logging.getLogger(__name__)

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
from utils.request_id_generator import generate_request_id


class TransportRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing transport requests
    Supports CRUD operations and custom actions for workflow
    """
    permission_classes = [IsAuthenticated]

    # Search across key fields
    search_fields = ['purpose', 'request_number', 'requestor_name', 'staff_id', 'department', 'requestor__email', 'requestor__name']

    # Allow ordering
    ordering_fields = ['created_at', 'submitted_at', 'status']
    ordering = ['-created_at']  # Default: newest first

    def get_object(self):
        """
        Override to show proper request_number in error messages
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field or 'pk'
        lookup_value = self.kwargs[lookup_url_kwarg]

        # Try to determine if it's a numeric ID or request_number
        if str(lookup_value).isdigit():
            filter_kwargs = {'pk': int(lookup_value)}
        else:
            filter_kwargs = {'request_number': lookup_value}

        queryset = self.filter_queryset(self.get_queryset())

        try:
            obj = queryset.get(**filter_kwargs)
        except TransportRequest.DoesNotExist:
            from rest_framework.exceptions import NotFound

            # Try to fetch from full queryset to get request_number for better error message
            try:
                obj = TransportRequest.objects.get(**filter_kwargs)
                request_identifier = obj.request_number or f"ID #{obj.id}"
                raise NotFound(f'Transport request {request_identifier} not found or you do not have permission to access it')
            except TransportRequest.DoesNotExist:
                raise NotFound(f'Transport request not found with identifier: {lookup_value}')

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def get_queryset(self):
        """
        Get queryset based on user permissions and filters

        Context-aware filtering:
        - Approval actions (approve/reject): Allow access to all requests (authorization checked in WorkflowEngine)
        - admin_view=true: Show all requests if user has view_all_transport permission (Admin Module)
        - Otherwise: Show only user's own requests (Personal Requests view)
        """
        user = self.request.user
        queryset = TransportRequest.objects.all()

        # For approval actions, allow access to requests pending the user's approval
        if self.action in ['approve', 'reject']:
            logger.info(f" Approval action: Allowing access to all transport requests (authorization checked in WorkflowEngine)")
            return queryset  # No filtering - authorization handled by WorkflowEngine

        # Check if this is an admin view (Transport Admin module)
        admin_view = self.request.query_params.get('admin_view', 'false').lower() == 'true'

        # Permission-based filtering
        if admin_view and user.role:
            # Admin module context - check if user has permission to view all
            can_view_all = user.role.permissions.filter(name='view_all_transport').exists()

            if can_view_all:
                logger.info(f" Admin view: User {user.username} (role: {user.role.name}) has 'view_all_transport' permission - showing all transport requests")
                pass  # No filtering - show all transport requests
            else:
                # User doesn't have permission - show only their own
                queryset = queryset.filter(requestor=user)
                logger.warning(f" Admin view: User {user.username} lacks permission - showing only own transport requests")
        else:
            # Personal requests view - always show only user's own requests
            queryset = queryset.filter(requestor=user)
            logger.info(f" Personal view: User {user.username} - showing only own transport requests")

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
                Q(purpose__icontains=search) |
                Q(request_number__icontains=search) |
                Q(requestor_name__icontains=search) |
                Q(staff_id__icontains=search) |
                Q(department__icontains=search) |
                Q(requestor__email__icontains=search) |
                Q(requestor__name__icontains=search)
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

            # Generate request number if submitting directly (not Draft)
            if not validated_data.get('request_number'):
                try:
                    from utils.request_id_generator import generate_request_id, extract_context_from_transport

                    # Extract context from transport_details
                    transport_details = validated_data.get('transport_details', [])
                    context = extract_context_from_transport(transport_details) if transport_details else 'TRN'

                    # Generate unique request number
                    request_number = generate_request_id('TRN', context)
                    extra_kwargs['request_number'] = request_number
                    logger.info(f" Generated request number during creation: {request_number}")
                except Exception as e:
                    logger.error(f" Error generating request number: {str(e)}")
                    # Will be generated later if needed

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
                    logger.info(f" Workflow started for Transport Request #{transport_request.id}: Workflow Instance #{workflow_instance.id}")
                    logger.info(f" Status updated to: {transport_request.status}")
                else:
                    logger.warning(f" No active workflow configured for transportrequest - using legacy approval system")
            except Exception as e:
                logger.error(f" Error starting workflow for Transport Request #{transport_request.id}: {str(e)}")
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

        # Generate request number if it doesn't exist
        if not transport_request.request_number:
            try:
                # Extract context from transport_details JSON (first destination)
                from utils.request_id_generator import extract_context_from_transport

                # transport_details is a JSON array, convert to list format for extraction
                transport_details = transport_request.transport_details or []

                logger.debug(f" Transport details for TRN #{transport_request.id}: {transport_details}")

                # Extract context (first destination from transport_details)
                context = extract_context_from_transport(transport_details) if transport_details else 'TRN'
                logger.debug(f" Extracted context: {context}")

                # Generate unique request number
                request_number = generate_request_id('TRN', context)
                transport_request.request_number = request_number
                logger.info(f" Generated request number: {request_number}")
            except Exception as e:
                logger.error(f" Error generating request number: {str(e)}")
                import traceback
                traceback.print_exc()
                # Fallback to simple format
                transport_request.request_number = f"TRN-{datetime.now().strftime('%Y%m%d-%H%M')}-TRN-{transport_request.id}"
                logger.warning(f" Using fallback request number: {transport_request.request_number}")

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
                logger.info(f" Workflow started for Transport Request #{transport_request.id}: Workflow Instance #{workflow_instance.id}")
                logger.info(f" Status updated to: {transport_request.status}")
            else:
                # Fallback to legacy approval system if no workflow configured
                logger.warning(f" No active workflow configured - creating legacy approval step")
                TransportApprovalStep.objects.create(
                    transport_request=transport_request,
                    step_role='HOD',
                    step_name='HOD Approval',
                    status='Pending'
                )
                transport_request.status = 'Pending Department Focal'
                transport_request.save()
        except Exception as e:
            logger.error(f" Error starting workflow: {str(e)}")
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
        Approve a transport request using WorkflowEngine
        """
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType

        transport_request = self.get_object()

        # Get approval action data
        action_serializer = ApprovalActionSerializer(
            data=request.data,
            context={'action_type': 'approve'}
        )
        action_serializer.is_valid(raise_exception=True)
        comments = action_serializer.validated_data.get('comments', '')

        try:
            # Get the workflow instance for this transport request
            content_type = ContentType.objects.get_for_model(transport_request)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=transport_request.id,
                status='in_progress'
            ).first()

            if workflow_instance:
                # Find the current pending step
                current_step = workflow_instance.step_executions.filter(
                    status='pending'
                ).order_by('workflow_step__step_order').first()

                if current_step:
                    # Use workflow engine to process approval
                    result = WorkflowEngine.process_action(
                        step_execution_id=current_step.id,
                        action='approve',
                        actioned_by=request.user,
                        comments=comments
                    )

                    # Reload to get updated status
                    transport_request.refresh_from_db()

                    # Update legacy approval step for backward compatibility
                    legacy_step = transport_request.approval_steps.filter(status='Pending').first()
                    if legacy_step:
                        legacy_step.status = 'Approved'
                        legacy_step.step_date = timezone.now()
                        legacy_step.comments = comments
                        legacy_step.save()

                    serializer = TransportRequestDetailSerializer(transport_request)
                    return Response(serializer.data)
                else:
                    return Response(
                        {'error': 'No pending approval step found'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Fallback to legacy approval logic
                logger.warning(f" No workflow instance found for Transport #{transport_request.id}, using legacy approval")

                current_step = transport_request.approval_steps.filter(status='Pending').first()
                if not current_step:
                    return Response(
                        {'error': 'No pending approval step found'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Update current step
                current_step.status = 'Approved'
                current_step.step_date = timezone.now()
                current_step.comments = comments
                current_step.save()

                # Determine next step or completion
                status_progression = {
                    'Department Focal': 'Pending HOD',
                    'HOD': 'Approved'
                }

                next_status = status_progression.get(current_step.step_role)
                if next_status:
                    transport_request.status = next_status
                    transport_request.save()

                serializer = TransportRequestDetailSerializer(transport_request)
                return Response(serializer.data)

        except Exception as e:
            logger.error(f" Error in approve workflow: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Failed to process approval: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a transport request using WorkflowEngine"""
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType

        transport_request = self.get_object()

        action_serializer = ApprovalActionSerializer(
            data=request.data,
            context={'action_type': 'reject'}
        )
        action_serializer.is_valid(raise_exception=True)
        comments = action_serializer.validated_data.get('comments', '')

        try:
            content_type = ContentType.objects.get_for_model(transport_request)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=transport_request.id,
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

                    transport_request.refresh_from_db()

                    legacy_step = transport_request.approval_steps.filter(status='Pending').first()
                    if legacy_step:
                        legacy_step.status = 'Rejected'
                        legacy_step.step_date = timezone.now()
                        legacy_step.comments = comments
                        legacy_step.save()

                    serializer = TransportRequestDetailSerializer(transport_request)
                    return Response(serializer.data)
            else:
                # Fallback to legacy rejection
                current_step = transport_request.approval_steps.filter(status='Pending').first()
                if current_step:
                    current_step.status = 'Rejected'
                    current_step.step_date = timezone.now()
                    current_step.comments = comments
                    current_step.save()

                transport_request.status = 'Rejected'
                transport_request.save()

                serializer = TransportRequestDetailSerializer(transport_request)
                return Response(serializer.data)

        except Exception as e:
            logger.error(f" Error in reject workflow: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Failed to process rejection: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def reject_old(self, request, pk=None):
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
        is_admin = user.is_superuser or is_module_admin(user, 'transport')
        if not is_admin and user_role != current_step.step_role:
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
        Cancel a transport request (by requestor or admin)
        """
        transport_request = self.get_object()

        # Validate requestor or admin
        is_admin = request.user.is_superuser or is_module_admin(request.user, 'transport')
        if transport_request.requestor != request.user and not is_admin:
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

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Mark a transport request as completed (by transport admin only)
        """
        transport_request = self.get_object()

        # Validate user has transport admin permission
        if not request.user.is_superuser and not is_module_admin(request.user, 'transport'):
            return Response(
                {'error': 'Only transport admin can mark requests as completed'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate status - can only complete approved or processing requests
        if transport_request.status not in ['Approved', 'Processing with Transport Admin']:
            return Response(
                {'error': f'Cannot complete transport request with status {transport_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate that vehicle has been assigned
        if not transport_request.vehicle_assignments.exists():
            return Response(
                {'error': 'Cannot complete request without vehicle assignment'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status
        transport_request.status = 'Completed'
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
        Get all transport requests pending approval for the current user based on workflow step assignments
        """
        from workflows.services import WorkflowApprovalHelper

        user = request.user

        # Admins and superusers see all pending requests
        if user.is_superuser or is_module_admin(user, 'transport'):
            queryset = self.get_queryset().filter(
                status__in=[
                    'Pending',
                    'Pending Department Focal',
                    'Pending Line Manager',
                    'Pending HOD',
                    'Submitted',
                    'Under Review'
                ]
            ).order_by('-submitted_at')
        else:
            # Use workflow-based filtering: get entities where user's role matches current step
            pending_ids = WorkflowApprovalHelper.get_pending_entity_ids_for_user(user, TransportRequest)
            queryset = self.get_queryset().filter(id__in=pending_ids).order_by('-submitted_at')

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='export-pdf')
    def export_pdf(self, request, pk=None):
        """
        Export Transport Request to PDF

        Returns a PDF document containing all transport request details including:
        - Requestor information
        - Transport details (pickup, dropoff, vehicle type)
        - Journey segments
        - Vehicle assignment details
        - Approval history and workflow status
        """
        import io
        from django.http import HttpResponse
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

        transport_request = self.get_object()

        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            textColor=colors.HexColor('#0d9488')
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            spaceBefore=15,
            spaceAfter=10,
            textColor=colors.HexColor('#0d9488')
        )
        normal_style = styles['Normal']

        elements = []

        # Title
        title = f"Transport Request - {transport_request.request_number or f'TR-{transport_request.id}'}"
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 12))

        # Status badge
        status_text = f"<b>Status:</b> {transport_request.status}"
        elements.append(Paragraph(status_text, normal_style))
        elements.append(Spacer(1, 12))

        # Table style
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d9488')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ])

        # Requestor Information
        elements.append(Paragraph("Requestor Information", heading_style))
        requestor_data = [
            ['Field', 'Value'],
            ['Name', transport_request.requestor_name or 'Not provided'],
            ['Staff ID', transport_request.staff_id or 'Not provided'],
            ['Department', transport_request.department or 'Not provided'],
            ['Position', transport_request.position or 'Not provided'],
            ['Email', transport_request.requestor.email if transport_request.requestor else 'Not provided'],
        ]
        requestor_table = Table(requestor_data, colWidths=[2*inch, 5*inch])
        requestor_table.setStyle(table_style)
        elements.append(requestor_table)

        # Status & Tracking
        elements.append(Paragraph("Status &amp; Tracking", heading_style))
        tracking_data = [
            ['Field', 'Value'],
            ['Request Number', transport_request.request_number or f'TR-{transport_request.id}'],
            ['Current Status', transport_request.status],
            ['TSR Reference', transport_request.tsr_reference or 'Not linked'],
            ['Created', transport_request.created_at.strftime('%Y-%m-%d %H:%M') if transport_request.created_at else 'Not available'],
            ['Submitted', transport_request.submitted_at.strftime('%Y-%m-%d %H:%M') if transport_request.submitted_at else 'Not submitted'],
            ['Last Updated', transport_request.updated_at.strftime('%Y-%m-%d %H:%M') if transport_request.updated_at else 'Not available'],
        ]
        tracking_table = Table(tracking_data, colWidths=[2*inch, 5*inch])
        tracking_table.setStyle(table_style)
        elements.append(tracking_table)

        # Transport Details
        elements.append(Paragraph("Transport Details", heading_style))
        transport_data = [
            ['Field', 'Value'],
            ['Purpose', (transport_request.purpose or 'Not provided')[:100]],
            ['Additional Comments', (transport_request.additional_comments or 'None')[:100]],
        ]
        transport_table = Table(transport_data, colWidths=[2*inch, 5*inch])
        transport_table.setStyle(table_style)
        elements.append(transport_table)

        # Journey Details from transport_details JSON field
        if transport_request.transport_details:
            # transport_details is a list of journey objects
            journeys = transport_request.transport_details if isinstance(transport_request.transport_details, list) else []
            if journeys:
                elements.append(Paragraph("Journey Details", heading_style))
                journey_data = [['#', 'Date', 'From', 'To', 'Time', 'Type', 'Passengers']]
                for i, journey in enumerate(journeys, 1):
                    journey_data.append([
                        str(i),
                        str(journey.get('date', '-'))[:10],
                        str(journey.get('from', journey.get('from_location', '-')))[:20],
                        str(journey.get('to', journey.get('to_location', '-')))[:20],
                        str(journey.get('departureTime', journey.get('departure_time', '-')))[:8],
                        str(journey.get('transportType', journey.get('transport_type', '-')))[:15],
                        str(journey.get('numberOfPassengers', journey.get('number_of_passengers', '-')))
                    ])
                journey_table = Table(journey_data, colWidths=[0.3*inch, 0.9*inch, 1.3*inch, 1.3*inch, 0.7*inch, 1*inch, 0.8*inch])
                journey_table.setStyle(table_style)
                elements.append(journey_table)

        # Vehicle Assignment
        vehicle_assignments = transport_request.vehicle_assignments.all()
        if vehicle_assignments.exists():
            elements.append(Paragraph("Vehicle Assignment", heading_style))
            for assignment in vehicle_assignments:
                assignment_data = [
                    ['Field', 'Value'],
                    ['Vehicle Number', assignment.vehicle_number or '-'],
                    ['Vehicle Type', assignment.vehicle_type or '-'],
                    ['Vehicle Capacity', str(assignment.vehicle_capacity) if assignment.vehicle_capacity else '-'],
                    ['Driver Name', assignment.driver_name or '-'],
                    ['Driver Contact', assignment.driver_contact or '-'],
                    ['Driver License', assignment.driver_license or '-'],
                    ['Assignment Status', assignment.status or '-'],
                    ['Assigned Date', assignment.assignment_date.strftime('%Y-%m-%d %H:%M') if assignment.assignment_date else '-'],
                ]
                assignment_table = Table(assignment_data, colWidths=[2*inch, 5*inch])
                assignment_table.setStyle(table_style)
                elements.append(assignment_table)

        # Approval History - try workflow first, then fall back to legacy approval steps
        from django.contrib.contenttypes.models import ContentType
        from workflows.models import WorkflowInstance

        approval_found = False
        try:
            content_type = ContentType.objects.get_for_model(transport_request)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=transport_request.id
            ).first()

            if workflow_instance and workflow_instance.step_executions.exists():
                elements.append(Paragraph("Approval History", heading_style))
                approval_data = [['Step', 'Role', 'Status', 'Actioned By', 'Date', 'Comments']]
                for step in workflow_instance.step_executions.all().order_by('step_order'):
                    approval_data.append([
                        str(step.step_order),
                        step.step_name or step.role_required or '-',
                        step.status or '-',
                        step.actioned_by.name if step.actioned_by else '-',
                        step.actioned_at.strftime('%Y-%m-%d %H:%M') if step.actioned_at else '-',
                        (step.comments or '-')[:30]
                    ])
                approval_table = Table(approval_data, colWidths=[0.4*inch, 1.2*inch, 0.9*inch, 1.2*inch, 1.3*inch, 2*inch])
                approval_table.setStyle(table_style)
                elements.append(approval_table)
                approval_found = True
        except Exception:
            pass

        # Fall back to legacy approval steps if no workflow found
        if not approval_found:
            approval_steps = transport_request.approval_steps.all().order_by('created_at')
            if approval_steps.exists():
                elements.append(Paragraph("Approval History", heading_style))
                approval_data = [['Role', 'Status', 'Date', 'Comments']]
                for step in approval_steps:
                    approval_data.append([
                        step.step_role or '-',
                        step.status or '-',
                        step.step_date.strftime('%Y-%m-%d %H:%M') if step.step_date else '-',
                        (step.comments or '-')[:50]
                    ])
                approval_table = Table(approval_data, colWidths=[1.5*inch, 1.2*inch, 1.5*inch, 3*inch])
                approval_table.setStyle(table_style)
                elements.append(approval_table)

        # Footer
        elements.append(Spacer(1, 20))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey
        )
        footer_text = f"Generated on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')} | Travel Management System"
        elements.append(Paragraph(footer_text, footer_style))

        # Build PDF
        doc.build(elements)
        buffer.seek(0)

        # Create response
        filename = f"Transport-{transport_request.request_number or transport_request.id}.pdf"
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


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
        Only transport admin can assign vehicles
        """
        user = self.request.user
        if not user.is_superuser and not is_module_admin(user, 'transport'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only transport admin can assign vehicles')

        serializer.save(assigned_by=user)

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
