import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
from .models import (
    AccommodationStaffHouse,
    AccommodationRoom,
    AccommodationRequest,
    AccommodationBooking
)
from .serializers import (
    AccommodationStaffHouseSerializer,
    AccommodationRoomSerializer,
    AccommodationRequestSerializer,
    AccommodationBookingSerializer,
    AccommodationBookingDetailSerializer,
    RoomAvailabilitySerializer
)
from workflows.router import WorkflowRouter
from utils.request_id_generator import generate_request_id


class AccommodationStaffHouseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Staff Houses

    Endpoints:
    - GET /api/accommodation/staff-houses/ - List all staff houses
    - POST /api/accommodation/staff-houses/ - Create a new staff house
    - GET /api/accommodation/staff-houses/{id}/ - Retrieve staff house details
    - PUT /api/accommodation/staff-houses/{id}/ - Update staff house
    - PATCH /api/accommodation/staff-houses/{id}/ - Partial update
    - DELETE /api/accommodation/staff-houses/{id}/ - Delete staff house
    """
    queryset = AccommodationStaffHouse.objects.all()
    serializer_class = AccommodationStaffHouseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter staff houses by location if provided"""
        queryset = self.queryset
        location = self.request.query_params.get('location', None)
        search = self.request.query_params.get('search', None)

        if location:
            queryset = queryset.filter(location__icontains=location)

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(location__icontains=search) |
                Q(description__icontains=search)
            )

        return queryset.order_by('-created_at')

    @action(detail=True, methods=['get'])
    def rooms(self, request, pk=None):
        """Get all rooms for a specific staff house"""
        staff_house = self.get_object()
        rooms = AccommodationRoom.objects.filter(staff_house=staff_house)
        serializer = AccommodationRoomSerializer(rooms, many=True)
        return Response(serializer.data)


class AccommodationRoomViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Rooms

    Endpoints:
    - GET /api/accommodation/rooms/ - List all rooms
    - POST /api/accommodation/rooms/ - Create a new room
    - GET /api/accommodation/rooms/{id}/ - Retrieve room details
    - PUT /api/accommodation/rooms/{id}/ - Update room
    - PATCH /api/accommodation/rooms/{id}/ - Partial update
    - DELETE /api/accommodation/rooms/{id}/ - Delete room
    - GET /api/accommodation/rooms/available/ - List available rooms
    """
    queryset = AccommodationRoom.objects.all()
    serializer_class = AccommodationRoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter rooms by staff_house, status, or availability"""
        queryset = self.queryset.select_related('staff_house')

        staff_house = self.request.query_params.get('staff_house', None)
        status = self.request.query_params.get('status', None)
        room_type = self.request.query_params.get('room_type', None)

        if staff_house:
            queryset = queryset.filter(staff_house_id=staff_house)

        if status:
            queryset = queryset.filter(status=status)

        if room_type:
            queryset = queryset.filter(room_type__icontains=room_type)

        return queryset.order_by('staff_house', 'name')

    @action(detail=False, methods=['get'])
    def available(self, request):
        """List all available rooms"""
        available_rooms = self.queryset.filter(status='Available')
        serializer = self.get_serializer(available_rooms, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def bookings(self, request, pk=None):
        """Get all bookings for a specific room"""
        room = self.get_object()
        date_from = request.query_params.get('date_from', None)
        date_to = request.query_params.get('date_to', None)

        bookings = AccommodationBooking.objects.filter(room=room)

        if date_from:
            bookings = bookings.filter(date__gte=date_from)
        if date_to:
            bookings = bookings.filter(date__lte=date_to)

        serializer = AccommodationBookingSerializer(bookings, many=True)
        return Response(serializer.data)


class AccommodationRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Accommodation Requests

    Endpoints:
    - GET /api/accommodation/requests/ - List all requests
    - POST /api/accommodation/requests/ - Create a new request
    - GET /api/accommodation/requests/{id}/ - Retrieve request details
    - PUT /api/accommodation/requests/{id}/ - Update request
    - PATCH /api/accommodation/requests/{id}/ - Partial update
    - DELETE /api/accommodation/requests/{id}/ - Delete request
    - POST /api/accommodation/requests/{id}/submit/ - Submit request
    - POST /api/accommodation/requests/{id}/approve/ - Approve request
    - POST /api/accommodation/requests/{id}/reject/ - Reject request
    - POST /api/accommodation/requests/{id}/cancel/ - Cancel request
    """
    queryset = AccommodationRequest.objects.all()
    serializer_class = AccommodationRequestSerializer
    permission_classes = [IsAuthenticated]

    # Search across key fields
    search_fields = ['requestor_name', 'staff_id', 'department', 'request_number']

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
        if lookup_value.isdigit():
            filter_kwargs = {'pk': int(lookup_value)}
        else:
            filter_kwargs = {'request_number': lookup_value}

        queryset = self.filter_queryset(self.get_queryset())

        try:
            obj = queryset.get(**filter_kwargs)
        except AccommodationRequest.DoesNotExist:
            from rest_framework.exceptions import NotFound

            # Try to fetch from full queryset to get request_number for better error message
            try:
                obj = AccommodationRequest.objects.get(**filter_kwargs)
                request_identifier = obj.request_number or f"ID #{obj.id}"
                raise NotFound(f'Accommodation request {request_identifier} not found or you do not have permission to access it')
            except AccommodationRequest.DoesNotExist:
                raise NotFound(f'Accommodation request not found with identifier: {lookup_value}')

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def get_serializer_class(self):
        """Use detailed serializer for retrieve action"""
        if self.action == 'retrieve':
            from .serializers import AccommodationRequestDetailSerializer
            return AccommodationRequestDetailSerializer
        return AccommodationRequestSerializer

    def get_queryset(self):
        """
        Filter requests by status, department, and user permissions

        Context-aware filtering:
        - Approval actions (approve/reject): Allow access to all requests (authorization checked in WorkflowEngine)
        - admin_view=true: Show all accommodation requests if user has permission (Admin Module)
        - Otherwise: Show only user's own requests (Personal Requests view)
        """
        user = self.request.user
        queryset = self.queryset

        # Optimize for detail view - prefetch bookings with related staff_house and room
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                'bookings',
                'bookings__staff_house',
                'bookings__room',
                'trf__trfitinerarysegment_set'  # Prefetch TRF itinerary segments for TSR dates
            )

        # Optimize for list view - prefetch TRF itinerary segments for TSR dates
        if self.action == 'list':
            queryset = queryset.prefetch_related('trf__trfitinerarysegment_set')

        # For approval actions, allow access to requests pending the user's approval
        if self.action in ['approve', 'reject']:
            logger.info(f" Approval action: Allowing access to all accommodation requests (authorization checked in WorkflowEngine)")
            return queryset  # No filtering - authorization handled by WorkflowEngine

        # For retrieve action, check permissions and workflow assignment
        if self.action == 'retrieve':
            from workflows.services import WorkflowApprovalHelper

            # Check if user has admin permissions to view all
            if user.role:
                can_view_all = user.role.permissions.filter(
                    name__in=['view_all_accommodation', 'approve_accommodation', 'process_accommodation']
                ).exists()

                if can_view_all or user.is_admin:
                    logger.info(f" Retrieve action: User {user.username} has admin permissions - allowing access to all requests")
                    return queryset  # No filtering for admins

            # Include requests pending user's approval via workflow
            pending_approval_ids = WorkflowApprovalHelper.get_pending_entity_ids_for_user(user, AccommodationRequest)
            if pending_approval_ids:
                queryset = queryset.filter(
                    Q(requestor_name=user.get_full_name()) |
                    Q(staff_id=user.staff_id) |
                    Q(id__in=pending_approval_ids)
                )
                logger.info(f" Retrieve action: User {user.username} - showing own requests plus {len(pending_approval_ids)} pending approval")
            else:
                # Regular users can view their own requests only
                logger.info(f" Retrieve action: User {user.username} - filtering by requestor")
                # Filter by requestor_name or staff_id to handle different data entry methods
                queryset = queryset.filter(
                    Q(requestor_name=user.get_full_name()) |
                    Q(staff_id=user.staff_id)
                )
            return queryset

        # For assign action, check if user has admin permissions
        if self.action == 'assign' and user.role:
            can_view_all = user.role.permissions.filter(
                name__in=['view_all_accommodation', 'approve_accommodation', 'process_accommodation']
            ).exists()

            if can_view_all or user.is_admin:
                logger.info(f" Assign action: User {user.username} has admin permissions - allowing access to all requests")
                return queryset  # No filtering for admins

        # Check if this is an admin view (Accommodation Admin module)
        admin_view = self.request.query_params.get('admin_view', 'false').lower() == 'true'

        # Permission-based filtering
        if admin_view and user.role:
            # Admin module context - check permissions
            can_view_all = user.role.permissions.filter(name='view_all_accommodation').exists()

            if can_view_all:
                logger.info(f" Admin view: User {user.username} (role: {user.role.name}) has 'view_all_accommodation' permission - showing all accommodation requests")
                pass  # No filtering - show all
            elif user.role.permissions.filter(name__in=['approve_accommodation', 'view_pending_approvals']).exists():
                # Department-level approvers - could be extended to filter by department if needed
                queryset = queryset.filter(requestor_name=user.get_full_name())
                logger.info(f" Admin view: Approver - showing own accommodation requests")
            else:
                # No admin permissions - show only own
                queryset = queryset.filter(requestor_name=user.get_full_name())
                logger.warning(f" Admin view: User lacks permission - showing only own accommodation requests")
        else:
            # Personal requests view - always show only user's own requests
            queryset = queryset.filter(requestor_name=user.get_full_name())
            logger.info(f" Personal view: User {user.username} - showing only own accommodation requests")

        # Apply additional filters from query parameters
        status_filter = self.request.query_params.get('status', None)
        department = self.request.query_params.get('department', None)
        requestor_name = self.request.query_params.get('requestor_name', None)

        if status_filter:
            # Use startswith to match workflow statuses like "Pending Line Manager"
            # when filter is "Pending"
            queryset = queryset.filter(status__istartswith=status_filter)

        if department:
            queryset = queryset.filter(department__icontains=department)

        if requestor_name:
            queryset = queryset.filter(requestor_name__icontains=requestor_name)

        # Apply search filter
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(requestor_name__icontains=search) |
                Q(staff_id__icontains=search) |
                Q(request_number__icontains=search) |
                Q(department__icontains=search) |
                Q(email__icontains=search)
            )
            logger.debug(f"Searching accommodation for: {search}")

        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        """Create accommodation request and optionally start workflow if submitted"""
        # Get status from request data, default to 'Draft' if not provided
        status_value = serializer.validated_data.get('status', 'Draft')

        # Set submitted_at timestamp if status is being submitted (not Draft)
        extra_kwargs = {}
        if status_value in ['Pending', 'Submitted']:
            extra_kwargs['submitted_at'] = timezone.now()

            # Generate request number if submitting directly (not Draft)
            if not serializer.validated_data.get('request_number'):
                try:
                    from utils.request_id_generator import generate_request_id, extract_context_from_location

                    # Extract context from additional_data location
                    additional_data = serializer.validated_data.get('additional_data', {})
                    location = additional_data.get('location', '') if isinstance(additional_data, dict) else ''
                    context = extract_context_from_location(location) if location else 'ACCOM'

                    # Generate unique request number
                    request_number = generate_request_id('ACCOM', context)
                    extra_kwargs['request_number'] = request_number
                    logger.info(f" Generated request number during creation: {request_number}")
                except Exception as e:
                    logger.error(f" Error generating request number: {str(e)}")
                    # Will be generated later if needed

        # Save the accommodation request
        accommodation_request = serializer.save(**extra_kwargs)

        # Start workflow if status is submitted (not Draft)
        if status_value in ['Pending', 'Submitted']:
            # Extract selected approvers from request data (optional)
            selected_approvers = self.request.data.get('selected_approvers', None)
            if selected_approvers:
                selected_approvers = {int(k): v for k, v in selected_approvers.items()}

            try:
                workflow_instance = WorkflowRouter.start_workflow_for_request(
                    entity=accommodation_request,
                    entity_type='accommodation',
                    initiated_by=self.request.user,
                    selected_approvers=selected_approvers
                )

                if workflow_instance:
                    # Reload the accommodation request to get the updated status from workflow
                    accommodation_request.refresh_from_db()
                    logger.info(f" Workflow started for Accommodation Request #{accommodation_request.id}: Workflow Instance #{workflow_instance.id}")
                    logger.info(f" Status updated to: {accommodation_request.status}")
                else:
                    logger.warning(f" No active workflow configured for accommodation - using legacy approval system")
            except Exception as e:
                logger.error(f" Error starting workflow for Accommodation Request #{accommodation_request.id}: {str(e)}")
                # Don't fail the request creation if workflow fails
                pass

    def perform_update(self, serializer):
        """Update accommodation request and start workflow if status changes to Pending/Submitted"""
        old_status = self.get_object().status
        new_status = serializer.validated_data.get('status', old_status)

        # Set submitted_at timestamp if status is changing to submitted (not Draft)
        extra_kwargs = {}
        if new_status in ['Pending', 'Submitted'] and old_status == 'Draft':
            extra_kwargs['submitted_at'] = timezone.now()

            # Generate request number if submitting (changing from Draft to Pending/Submitted)
            accommodation_request = self.get_object()
            if not accommodation_request.request_number:
                try:
                    from utils.request_id_generator import generate_request_id, extract_context_from_location

                    # Extract context from additional_data location
                    additional_data = serializer.validated_data.get('additional_data', {})
                    location = additional_data.get('location', '') if isinstance(additional_data, dict) else ''
                    context = extract_context_from_location(location) if location else 'ACCOM'

                    # Generate unique request number
                    request_number = generate_request_id('ACCOM', context)
                    extra_kwargs['request_number'] = request_number
                    logger.info(f" Generated request number during update: {request_number}")
                except Exception as e:
                    logger.error(f" Error generating request number: {str(e)}")

        # Save the accommodation request
        accommodation_request = serializer.save(**extra_kwargs)

        # Start workflow if status changed from Draft to Pending/Submitted
        if new_status in ['Pending', 'Submitted'] and old_status == 'Draft':
            # Extract selected approvers from request data (optional)
            selected_approvers = self.request.data.get('selected_approvers', None)
            if selected_approvers:
                selected_approvers = {int(k): v for k, v in selected_approvers.items()}

            try:
                workflow_instance = WorkflowRouter.start_workflow_for_request(
                    entity=accommodation_request,
                    entity_type='accommodation',
                    initiated_by=self.request.user,
                    selected_approvers=selected_approvers
                )

                if workflow_instance:
                    # Reload the accommodation request to get the updated status from workflow
                    accommodation_request.refresh_from_db()
                    logger.info(f" Workflow started for Accommodation Request #{accommodation_request.id}: Workflow Instance #{workflow_instance.id}")
                    logger.info(f" Status updated to: {accommodation_request.status}")
                else:
                    logger.warning(f" No active workflow configured for accommodation - using legacy approval system")
            except Exception as e:
                logger.error(f" Error starting workflow for Accommodation Request #{accommodation_request.id}: {str(e)}")
                # Don't fail the request update if workflow fails
                pass

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """
        Submit an accommodation request for approval
        Changes status from Draft to Pending and starts workflow
        """
        accommodation_request = self.get_object()

        # Validate status
        if accommodation_request.status != 'Draft':
            return Response(
                {'error': f'Cannot submit accommodation request with status {accommodation_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate request number if it doesn't exist
        if not accommodation_request.request_number:
            try:
                # Extract context from additional_data location or use generic context
                context = 'ACCOM'
                if accommodation_request.additional_data and isinstance(accommodation_request.additional_data, dict):
                    location = accommodation_request.additional_data.get('location', '')
                    if location:
                        context = location  # Let generate_request_id handle validation and length

                logger.debug(f" Extracted context for Accommodation Request #{accommodation_request.id}: {context}")

                # Generate unique request number (will auto-validate and limit context to 5 chars)
                request_number = generate_request_id('ACCOM', context)
                accommodation_request.request_number = request_number
                logger.info(f" Generated request number: {request_number}")
            except Exception as e:
                logger.error(f" Error generating request number: {str(e)}")
                import traceback
                traceback.print_exc()
                # Fallback to simple format
                accommodation_request.request_number = f"ACCOM-{datetime.now().strftime('%Y%m%d-%H%M')}-ACCOM-{accommodation_request.id}"
                logger.warning(f" Using fallback request number: {accommodation_request.request_number}")

        # Update status and submitted_at
        accommodation_request.status = 'Pending'
        accommodation_request.submitted_at = timezone.now()
        accommodation_request.save()

        # Extract selected approvers from request data (optional)
        selected_approvers = request.data.get('selected_approvers', None)
        if selected_approvers:
            selected_approvers = {int(k): v for k, v in selected_approvers.items()}

        # Start workflow using WorkflowRouter
        try:
            workflow_instance = WorkflowRouter.start_workflow_for_request(
                entity=accommodation_request,
                entity_type='accommodation',
                initiated_by=request.user,
                selected_approvers=selected_approvers
            )

            if workflow_instance:
                # Reload the accommodation request to get the updated status from workflow
                accommodation_request.refresh_from_db()
                logger.info(f" Workflow started for Accommodation Request #{accommodation_request.id}: Workflow Instance #{workflow_instance.id}")
                logger.info(f" Status updated to: {accommodation_request.status}")
            else:
                # Fallback to legacy approval system if no workflow configured
                logger.warning(f" No active workflow configured - keeping status as Pending")
        except Exception as e:
            logger.error(f" Error starting workflow: {str(e)}")
            # Fallback to legacy system on error - status remains 'Pending'
            pass

        # Ensure we have the latest status before serializing
        accommodation_request.refresh_from_db()
        serializer = self.get_serializer(accommodation_request)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve an accommodation request using WorkflowEngine"""
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType

        accommodation_request = self.get_object()
        comments = request.data.get('comments', '')

        try:
            # Get the workflow instance for this accommodation request
            content_type = ContentType.objects.get_for_model(accommodation_request)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=accommodation_request.id,
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
                    accommodation_request.refresh_from_db()

                    serializer = self.get_serializer(accommodation_request)
                    return Response(serializer.data)
                else:
                    return Response(
                        {'error': 'No pending approval step found'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Fallback to legacy approval logic
                logger.warning(f" No workflow instance found for Accommodation #{accommodation_request.id}, using legacy approval")

                if accommodation_request.status not in ['Pending', 'Pending Department Focal', 'Pending HOD']:
                    return Response(
                        {'error': 'Cannot approve request with current status'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                accommodation_request.status = 'Approved'
                accommodation_request.save()

                serializer = self.get_serializer(accommodation_request)
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
        """Reject an accommodation request using WorkflowEngine"""
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType

        accommodation_request = self.get_object()
        comments = request.data.get('comments', '')

        try:
            content_type = ContentType.objects.get_for_model(accommodation_request)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=accommodation_request.id,
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

                    accommodation_request.refresh_from_db()

                    serializer = self.get_serializer(accommodation_request)
                    return Response(serializer.data)
            else:
                # Fallback to legacy rejection
                if accommodation_request.status not in ['Pending', 'Pending Department Focal', 'Pending HOD']:
                    return Response(
                        {'error': 'Cannot reject request with current status'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                accommodation_request.status = 'Rejected'
                accommodation_request.save()

                serializer = self.get_serializer(accommodation_request)
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
    def cancel(self, request, pk=None):
        """Cancel an accommodation request"""
        accommodation_request = self.get_object()

        if accommodation_request.status in ['Approved', 'Completed']:
            return Response(
                {'error': 'Approved or completed accommodation requests cannot be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        accommodation_request.status = 'Cancelled'
        accommodation_request.save()

        serializer = self.get_serializer(accommodation_request)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='pending-approvals')
    def pending_approvals(self, request):
        """Get accommodation requests pending approval for the current user based on workflow step assignments"""
        from accounts.utils import is_module_admin
        from workflows.services import WorkflowApprovalHelper

        user = request.user

        # Admins and superusers see all pending requests
        # Use startswith to match any workflow-generated 'Pending *' status
        if user.is_superuser or is_module_admin(user, 'accommodation'):
            from django.db.models import Q
            queryset = AccommodationRequest.objects.filter(
                Q(status__startswith='Pending') |
                Q(status='Submitted') |
                Q(status='Under Review')
            ).prefetch_related('trf__trfitinerarysegment_set').order_by('-submitted_at')
        else:
            # Use workflow-based filtering: get entities where user's role matches current step
            pending_ids = WorkflowApprovalHelper.get_pending_entity_ids_for_user(user, AccommodationRequest)
            queryset = AccommodationRequest.objects.filter(
                id__in=pending_ids
            ).prefetch_related('trf__trfitinerarysegment_set').order_by('-submitted_at')

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='export-pdf')
    def export_pdf(self, request, pk=None):
        """
        Export Accommodation Request to PDF

        Returns a PDF document containing all accommodation request details including:
        - Requestor information
        - Status & Tracking
        - Booking details
        - Approval history and workflow status
        """
        import io
        from django.http import HttpResponse
        from django.contrib.contenttypes.models import ContentType
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from workflows.models import WorkflowInstance

        accommodation_request = self.get_object()

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
        title = f"Accommodation Request - {accommodation_request.request_number or f'ACC-{accommodation_request.id}'}"
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 12))

        # Status badge - prominent display
        status_text = f"<b>Current Status:</b> <font color='#0d9488'><b>{accommodation_request.status}</b></font>"
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
            ['Name', accommodation_request.requestor_name or 'Not provided'],
            ['Staff ID', accommodation_request.staff_id or 'Not provided'],
            ['Department', accommodation_request.department or 'Not provided'],
            ['Position', accommodation_request.position or 'Not provided'],
            ['Cost Center', accommodation_request.cost_center or 'Not provided'],
            ['Tel/Email', accommodation_request.tel_email or 'Not provided'],
            ['Email', accommodation_request.email or 'Not provided'],
        ]
        requestor_table = Table(requestor_data, colWidths=[2*inch, 5*inch])
        requestor_table.setStyle(table_style)
        elements.append(requestor_table)

        # Status & Tracking
        elements.append(Paragraph("Status &amp; Tracking", heading_style))
        trf = accommodation_request.trf
        tsr_reference = 'Not linked'
        if trf:
            tsr_reference = trf.request_number or f'TSR-{trf.id}'

        tracking_data = [
            ['Field', 'Value'],
            ['Request Number', accommodation_request.request_number or f'ACC-{accommodation_request.id}'],
            ['Current Status', accommodation_request.status],
            ['TSR Reference', tsr_reference],
            ['Created', accommodation_request.created_at.strftime('%Y-%m-%d %H:%M') if accommodation_request.created_at else 'Not available'],
            ['Submitted', accommodation_request.submitted_at.strftime('%Y-%m-%d %H:%M') if accommodation_request.submitted_at else 'Not submitted'],
            ['Last Updated', accommodation_request.updated_at.strftime('%Y-%m-%d %H:%M') if accommodation_request.updated_at else 'Not available'],
        ]
        tracking_table = Table(tracking_data, colWidths=[2*inch, 5*inch])
        tracking_table.setStyle(table_style)
        elements.append(tracking_table)

        # Booking Details
        bookings = accommodation_request.bookings.all().select_related('staff_house', 'room').order_by('date')
        elements.append(Paragraph("Booking Details", heading_style))

        if bookings.exists():
            # Get unique staff house and room info
            first_booking = bookings.first()
            last_booking = bookings.last()

            # Booking summary info
            booking_summary = [
                ['Field', 'Value'],
                ['Staff House', first_booking.staff_house.name if first_booking.staff_house else 'Not assigned'],
                ['Location', first_booking.staff_house.location if first_booking.staff_house else 'Not available'],
                ['Room', first_booking.room.name if first_booking.room else 'Not assigned'],
                ['Room Type', first_booking.room.room_type if first_booking.room and first_booking.room.room_type else 'Standard'],
                ['Room Capacity', str(first_booking.room.capacity) if first_booking.room else 'Not available'],
                ['Check-in Date', first_booking.date.strftime('%Y-%m-%d') if first_booking.date else 'Not set'],
                ['Check-out Date', last_booking.date.strftime('%Y-%m-%d') if last_booking.date else 'Not set'],
                ['Total Nights', str(bookings.count())],
                ['Booking Status', first_booking.status or 'Pending'],
            ]
            booking_summary_table = Table(booking_summary, colWidths=[2*inch, 5*inch])
            booking_summary_table.setStyle(table_style)
            elements.append(booking_summary_table)

            # Daily booking breakdown if multiple nights
            if bookings.count() > 1:
                elements.append(Spacer(1, 10))
                elements.append(Paragraph("Daily Breakdown", heading_style))
                daily_data = [['Date', 'Staff House', 'Room', 'Status']]
                for booking in bookings:
                    daily_data.append([
                        booking.date.strftime('%Y-%m-%d') if booking.date else '-',
                        booking.staff_house.name if booking.staff_house else '-',
                        booking.room.name if booking.room else '-',
                        booking.status or '-',
                    ])
                daily_table = Table(daily_data, colWidths=[1.5*inch, 2*inch, 2*inch, 1.5*inch])
                daily_table.setStyle(table_style)
                elements.append(daily_table)
        else:
            # No bookings yet
            no_booking_data = [
                ['Field', 'Value'],
                ['Status', 'No accommodation assigned yet'],
                ['Note', 'Booking will be assigned after approval'],
            ]
            no_booking_table = Table(no_booking_data, colWidths=[2*inch, 5*inch])
            no_booking_table.setStyle(table_style)
            elements.append(no_booking_table)

        # Approval History from Workflow
        try:
            content_type = ContentType.objects.get_for_model(accommodation_request)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=accommodation_request.id
            ).first()

            if workflow_instance and workflow_instance.step_executions.exists():
                # Build table first, then add heading only if we have data
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
                # Only add if we have actual data rows (more than just header)
                if len(approval_data) > 1:
                    elements.append(Paragraph("Approval History", heading_style))
                    approval_table = Table(approval_data, colWidths=[0.4*inch, 1.2*inch, 0.9*inch, 1.2*inch, 1.3*inch, 2*inch])
                    approval_table.setStyle(table_style)
                    elements.append(approval_table)
        except Exception:
            pass  # No workflow found, skip approval history

        # Additional Comments
        if accommodation_request.additional_comments:
            elements.append(Paragraph("Additional Comments", heading_style))
            elements.append(Paragraph(accommodation_request.additional_comments, normal_style))

        # Additional Data (Request Details) - format as table if available
        if accommodation_request.additional_data and isinstance(accommodation_request.additional_data, dict):
            elements.append(Paragraph("Request Details", heading_style))
            request_details_data = [['Field', 'Value']]
            # Map field names to readable labels
            field_labels = {
                'location': 'Location',
                'requestor_gender': 'Gender',
                'special_requests': 'Special Requests',
                'flight_arrival_time': 'Flight Arrival Time',
                'flight_departure_time': 'Flight Departure Time',
                'requested_room_type': 'Requested Room Type',
                'requested_check_in_date': 'Requested Check-in',
                'requested_check_out_date': 'Requested Check-out',
                'number_of_guests': 'Number of Guests',
                'purpose': 'Purpose',
            }
            for key, value in accommodation_request.additional_data.items():
                label = field_labels.get(key, key.replace('_', ' ').title())
                # Format boolean values
                if isinstance(value, bool):
                    value = 'Yes' if value else 'No'
                if value:  # Only show non-empty values
                    request_details_data.append([label, str(value)[:80]])
            # Only add if we have data rows
            if len(request_details_data) > 1:
                request_details_table = Table(request_details_data, colWidths=[2*inch, 5*inch])
                request_details_table.setStyle(table_style)
                elements.append(request_details_table)

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
        filename = f"Accommodation-{accommodation_request.request_number or accommodation_request.id}.pdf"
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """
        Assign accommodation to a request and create daily booking records

        Expected payload:
        {
            "staff_house": 1,
            "room": 2,
            "start_date": "2025-11-24",
            "end_date": "2025-11-26",
            "notes": "Optional notes",
            "assigned_room_info": "Apartment - Room #1 (Nov 24 - Nov 26, 2025)"
        }
        """
        accommodation_request = self.get_object()

        # Extract data from request
        staff_house_id = request.data.get('staff_house')
        room_id = request.data.get('room')
        start_date_str = request.data.get('start_date')
        end_date_str = request.data.get('end_date')
        notes = request.data.get('notes', '')
        assigned_room_info = request.data.get('assigned_room_info', '')

        # Validate required fields
        if not all([staff_house_id, room_id, start_date_str, end_date_str]):
            return Response(
                {'error': 'staff_house, room, start_date, and end_date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError as e:
            return Response(
                {'error': f'Invalid date format. Use YYYY-MM-DD: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate date range
        if end_date < start_date:
            return Response(
                {'error': 'end_date must be greater than or equal to start_date'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify staff house and room exist
        try:
            staff_house = AccommodationStaffHouse.objects.get(id=staff_house_id)
            room = AccommodationRoom.objects.get(id=room_id, staff_house=staff_house)
        except AccommodationStaffHouse.DoesNotExist:
            return Response(
                {'error': f'Staff house with id {staff_house_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except AccommodationRoom.DoesNotExist:
            return Response(
                {'error': f'Room with id {room_id} not found in staff house {staff_house_id}'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check for existing bookings in the date range
        current_date = start_date
        conflicting_dates = []
        while current_date <= end_date:
            existing_booking = AccommodationBooking.objects.filter(
                room=room,
                date=current_date,
                status__in=['Confirmed', 'Pending']
            ).first()

            if existing_booking:
                conflicting_dates.append(current_date.strftime('%Y-%m-%d'))

            current_date += timedelta(days=1)

        if conflicting_dates:
            return Response(
                {
                    'error': 'Room is already booked for the following dates',
                    'conflicting_dates': conflicting_dates
                },
                status=status.HTTP_409_CONFLICT
            )

        # Delete any existing bookings for this request (in case of reassignment)
        AccommodationBooking.objects.filter(accommodation_request=accommodation_request).delete()

        # Create daily booking records
        created_bookings = []
        current_date = start_date

        try:
            while current_date <= end_date:
                booking = AccommodationBooking.objects.create(
                    staff_house=staff_house,
                    room=room,
                    accommodation_request=accommodation_request,
                    date=current_date,
                    trf=accommodation_request.trf,
                    status='Confirmed',
                    notes=notes or f'TRF Assignment: {assigned_room_info}'
                )
                created_bookings.append(booking)
                current_date += timedelta(days=1)

            # Update accommodation request status
            accommodation_request.status = 'Accommodation Assigned'

            # Update additional_comments with assignment info
            if accommodation_request.additional_comments:
                accommodation_request.additional_comments += f'\n\n{assigned_room_info}'
            else:
                accommodation_request.additional_comments = assigned_room_info

            accommodation_request.save()

            # Add workflow step execution if workflow is active
            try:
                from workflows.models import WorkflowInstance, StepExecution
                from django.contrib.contenttypes.models import ContentType

                content_type = ContentType.objects.get_for_model(accommodation_request)
                workflow_instance = WorkflowInstance.objects.filter(
                    content_type=content_type,
                    object_id=accommodation_request.id,
                    status='in_progress'
                ).first()

                if workflow_instance:
                    # Find or create accommodation admin step
                    from workflows.models import WorkflowStep

                    accommodation_step = WorkflowStep.objects.filter(
                        workflow_definition=workflow_instance.workflow_definition,
                        step_name='Accommodation Admin'
                    ).first()

                    if accommodation_step:
                        StepExecution.objects.create(
                            workflow_instance=workflow_instance,
                            workflow_step=accommodation_step,
                            assigned_role=request.user.role,
                            status='completed',
                            action_taken='assign',
                            actioned_by=request.user,
                            actioned_at=timezone.now(),
                            comments=f'Assigned: {assigned_room_info}'
                        )

                        # Mark workflow as completed
                        workflow_instance.status = 'completed'
                        workflow_instance.completed_at = timezone.now()
                        workflow_instance.save()
            except Exception as e:
                logger.warning(f" Could not add workflow step execution: {str(e)}")
                # Don't fail the assignment if workflow update fails
                pass

            # Prepare response
            serializer = self.get_serializer(accommodation_request)
            return Response({
                'message': f'Accommodation assigned successfully. Created {len(created_bookings)} booking records.',
                'bookings_created': len(created_bookings),
                'date_range': f'{start_date_str} to {end_date_str}',
                'accommodation_request': serializer.data
            })

        except Exception as e:
            # Rollback: delete any created bookings
            for booking in created_bookings:
                booking.delete()

            logger.error(f" Error creating booking records: {str(e)}")
            import traceback
            traceback.print_exc()

            return Response(
                {'error': f'Failed to create booking records: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AccommodationBookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Accommodation Bookings

    Endpoints:
    - GET /api/accommodation/bookings/ - List all bookings
    - POST /api/accommodation/bookings/ - Create a new booking
    - GET /api/accommodation/bookings/{id}/ - Retrieve booking details
    - PUT /api/accommodation/bookings/{id}/ - Update booking
    - PATCH /api/accommodation/bookings/{id}/ - Partial update
    - DELETE /api/accommodation/bookings/{id}/ - Delete booking
    - POST /api/accommodation/bookings/check-availability/ - Check room availability
    - POST /api/accommodation/bookings/{id}/cancel/ - Cancel booking
    """
    queryset = AccommodationBooking.objects.all()
    serializer_class = AccommodationBookingSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use detailed serializer for retrieve action"""
        if self.action == 'retrieve':
            return AccommodationBookingDetailSerializer
        return AccommodationBookingSerializer

    def get_queryset(self):
        """Filter bookings by various parameters"""
        queryset = self.queryset.select_related(
            'staff_house', 'room', 'staff', 'trf'
        )

        staff_house = self.request.query_params.get('staff_house', None)
        room = self.request.query_params.get('room', None)
        staff = self.request.query_params.get('staff', None)
        status = self.request.query_params.get('status', None)
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)

        if staff_house:
            queryset = queryset.filter(staff_house_id=staff_house)

        if room:
            queryset = queryset.filter(room_id=room)

        if staff:
            queryset = queryset.filter(staff_id=staff)

        if status:
            queryset = queryset.filter(status=status)

        if date_from:
            queryset = queryset.filter(date__gte=date_from)

        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        return queryset.order_by('-date', '-created_at')

    @action(detail=False, methods=['post'])
    def check_availability(self, request):
        """
        Check room availability for a given date range

        Expected payload:
        {
            "staff_house": 1,
            "start_date": "2025-10-15",
            "end_date": "2025-10-20"
        }
        """
        serializer = RoomAvailabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        staff_house_id = serializer.validated_data['staff_house']
        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']

        # Get all rooms in the staff house
        rooms = AccommodationRoom.objects.filter(
            staff_house_id=staff_house_id
        )

        # Get bookings for the date range
        bookings = AccommodationBooking.objects.filter(
            staff_house_id=staff_house_id,
            date__gte=start_date,
            date__lte=end_date,
            status__in=['Confirmed', 'Pending']
        )

        # Build availability response
        availability = []
        for room in rooms:
            room_bookings = bookings.filter(room=room)
            booked_dates = [booking.date.strftime('%Y-%m-%d') for booking in room_bookings]

            availability.append({
                'room_id': room.id,
                'room_name': room.name,
                'room_type': room.room_type,
                'capacity': room.capacity,
                'status': room.status,
                'booked_dates': booked_dates,
                'is_fully_booked': len(booked_dates) == (end_date - start_date).days + 1
            })

        return Response({
            'staff_house_id': staff_house_id,
            'start_date': start_date,
            'end_date': end_date,
            'rooms': availability
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking"""
        booking = self.get_object()

        if booking.status == 'Cancelled':
            return Response(
                {'error': 'Booking is already cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        booking.status = 'Cancelled'
        booking.save()

        serializer = self.get_serializer(booking)
        return Response(serializer.data)
