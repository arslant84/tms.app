import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.utils import timezone
from datetime import datetime

logger = logging.getLogger(__name__)
from workflows.router import WorkflowRouter
from utils.request_id_generator import generate_request_id, extract_context_from_itinerary
from utils.api_response import (
    success_response, error_response, validation_error_response,
    paginated_response, created_response, unauthorized_response,
    forbidden_response, not_found_response, server_error_response,
    get_pagination_params
)

from .models import (
    TravelRequest,
    TrfAdvanceAmountRequestedItem,
    TrfAdvanceBankDetail,
    TrfApprovalStep,
    TrfDailyMealSelection,
    TrfFlightBooking,
    TrfItinerarySegment,
    TrfMealProvision,
    TrfPassportDetail
)
from .serializers import (
    TravelRequestSerializer,
    TravelRequestDetailSerializer,
    TravelRequestCreateSerializer,
    TravelRequestUpdateSerializer,
    ApprovalActionSerializer,
    TrfAdvanceAmountRequestedItemSerializer,
    TrfAdvanceBankDetailSerializer,
    TrfApprovalStepSerializer,
    TrfDailyMealSelectionSerializer,
    TrfFlightBookingSerializer,
    TrfItinerarySegmentSerializer,
    TrfMealProvisionSerializer,
    TrfPassportDetailSerializer
)


class TravelRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Travel Requests (TRF)

    Endpoints:
    - GET /api/trf/travel-requests/ - List all TRFs
    - POST /api/trf/travel-requests/ - Create a new TRF
    - GET /api/trf/travel-requests/{id_or_request_number}/ - Retrieve TRF details (supports both numeric ID and request_number)
    - PUT /api/trf/travel-requests/{id_or_request_number}/ - Update TRF
    - PATCH /api/trf/travel-requests/{id_or_request_number}/ - Partial update
    - DELETE /api/trf/travel-requests/{id_or_request_number}/ - Delete TRF
    - POST /api/trf/travel-requests/{id_or_request_number}/submit/ - Submit TRF for approval
    - POST /api/trf/travel-requests/{id_or_request_number}/approve/ - Approve TRF
    - POST /api/trf/travel-requests/{id_or_request_number}/reject/ - Reject TRF
    - POST /api/trf/travel-requests/{id_or_request_number}/cancel/ - Cancel TRF

    Filtering & Search:
    - ?search=query - Search across requestor_name, department, purpose, staff_id, request_number
    - ?ordering=field - Order by: created_at, submitted_at, departure_date, requestor_name, status
    - ?status=Draft - Filter by status (supports startswith matching)
    - ?travel_type=type - Filter by travel type
    - ?department=dept - Filter by department (contains)
    - ?requestor_name=name - Filter by requestor name (contains)
    - ?sortBy=field&sortOrder=ascending|descending - Custom sorting (frontend compatibility)
    """
    queryset = TravelRequest.objects.all()
    serializer_class = TravelRequestSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    # Search across key fields
    search_fields = ['requestor_name', 'department', 'purpose', 'staff_id', 'request_number']

    # Allow ordering by these fields
    ordering_fields = ['created_at', 'submitted_at', 'departure_date', 'requestor_name', 'status', 'request_number']
    ordering = ['-created_at']  # Default ordering: newest first

    def get_object(self):
        """
        Override to support lookup by both numeric ID and request_number
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field or 'pk'
        lookup_value = self.kwargs[lookup_url_kwarg]

        # Try to determine if it's a numeric ID or request_number
        if isinstance(lookup_value, int) or (isinstance(lookup_value, str) and lookup_value.isdigit()):
            # Numeric ID lookup
            filter_kwargs = {'pk': int(lookup_value)}
        else:
            # Request number lookup (contains letters/dashes)
            filter_kwargs = {'request_number': lookup_value}

        queryset = self.filter_queryset(self.get_queryset())

        try:
            obj = queryset.get(**filter_kwargs)
        except TravelRequest.DoesNotExist:
            from rest_framework.exceptions import NotFound

            # Try to fetch from full queryset to get request_number for better error message
            try:
                obj = TravelRequest.objects.get(**filter_kwargs)
                request_identifier = obj.request_number or f"ID #{obj.id}"
                raise NotFound(f'Travel request {request_identifier} not found or you do not have permission to access it')
            except TravelRequest.DoesNotExist:
                raise NotFound(f'Travel request not found with identifier: {lookup_value}')

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def get_serializer_class(self):
        """Use appropriate serializer based on action"""
        if self.action == 'retrieve':
            return TravelRequestDetailSerializer
        elif self.action == 'create':
            return TravelRequestCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TravelRequestUpdateSerializer
        return TravelRequestSerializer

    def create(self, request, *args, **kwargs):
        """Create a new TRF with logging"""
        logger.debug(f"\n=== TravelRequest CREATE ===")
        logger.debug(f"Request data: {request.data}")
        response = super().create(request, *args, **kwargs)
        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response data: {response.data}")
        logger.debug(f"Response data keys: {list(response.data.keys()) if hasattr(response.data, 'keys') else 'N/A'}")
        return response

    def perform_create(self, serializer):
        """Set creator and auto-populate requestor info, start workflow if submitted"""
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
        if status_value not in ['Draft']:
            extra_kwargs['submitted_at'] = timezone.now()

        # Save the travel request
        trf = serializer.save(created_by=user, **extra_kwargs)

        # Start workflow if status is submitted (not Draft)
        if status_value not in ['Draft']:
            # Extract selected approvers from request data (optional)
            selected_approvers = self.request.data.get('selected_approvers', None)
            if selected_approvers:
                selected_approvers = {int(k): v for k, v in selected_approvers.items()}

            # Extract skipped steps from request data (optional)
            skipped_steps = self.request.data.get('skipped_steps', None)
            if skipped_steps:
                skipped_steps = {int(k): v for k, v in skipped_steps.items()}

            try:
                workflow_instance = WorkflowRouter.start_workflow_for_request(
                    entity=trf,
                    entity_type='travelrequest',
                    initiated_by=user,
                    selected_approvers=selected_approvers,
                    skipped_steps=skipped_steps
                )

                if workflow_instance:
                    # Reload the TRF to get the updated status from workflow
                    trf.refresh_from_db()
                    logger.info(f" Workflow started for TRF #{trf.id}: Workflow Instance #{workflow_instance.id}")
                    logger.info(f" Status updated to: {trf.status}")
                else:
                    logger.warning(f" No active workflow configured for travelrequest - using legacy approval system")
            except Exception as e:
                logger.error(f" Error starting workflow for TRF #{trf.id}: {str(e)}")
                # Don't fail the request creation if workflow fails
                pass

    def get_queryset(self):
        """
        Filter TRFs based on query parameters and user permissions

        Context-aware filtering:
        - admin_view=true: Show all/department TRFs if user has appropriate permissions (Admin Module)
        - Approval actions (approve/reject/retrieve): Allow access to TRFs pending user's approval
        - Otherwise: Show only user's own TRFs (Personal Requests view)
        """
        from workflows.services import WorkflowApprovalHelper

        user = self.request.user
        queryset = self.queryset

        logger.debug(f"\n=== TravelRequest GET_QUERYSET ===")
        logger.debug(f"Total TRFs in database: {TravelRequest.objects.count()}")
        logger.debug(f"Query params: {dict(self.request.query_params)}")
        logger.debug(f"Action: {self.action}")
        logger.debug(f"User: {user}")
        logger.debug(f"User role: {user.role.name if user.role else 'No role'}")

        # For approval actions, allow access to TRFs pending the user's approval
        if self.action in ['approve', 'reject']:
            logger.info(f" Approval action: Allowing access to all TRFs (authorization checked in WorkflowEngine)")
            return queryset  # No filtering - authorization handled by WorkflowEngine

        # For admin booking actions (book_flight, book_hotel), allow access if user has booking permissions
        if self.action in ['book_flight', 'book_hotel']:
            logger.info(f" Booking action detected: {self.action} by user {user.email}")
            # Statuses that allow booking operations
            bookable_statuses = ['Approved', 'Flight Booked', 'Hotel Booked', 'Processing', 'Ready for Booking']

            # Check if user has ticketing/booking permissions
            if user.role and user.role.permissions.filter(name__in=['book_flights', 'manage_bookings', 'view_all_trf']).exists():
                logger.info(f" Booking action: User has booking permissions - allowing access to bookable TRFs")
                return queryset.filter(status__in=bookable_statuses)
            # Also allow staff users
            if user.is_staff:
                logger.info(f" Booking action: Staff user - allowing access to bookable TRFs")
                return queryset.filter(status__in=bookable_statuses)
            # Allow users with ticketing-related roles (Travel Desk, Ticketing, etc.)
            if user.role and any(keyword in user.role.name.lower() for keyword in ['ticket', 'travel desk', 'booking', 'admin']):
                logger.info(f" Booking action: User role '{user.role.name}' indicates booking capability - allowing access")
                return queryset.filter(status__in=bookable_statuses)

        # For retrieve (viewing details), include TRFs pending user's approval via workflow
        if self.action == 'retrieve':
            # Get IDs of TRFs pending this user's approval
            pending_approval_ids = WorkflowApprovalHelper.get_pending_entity_ids_for_user(user, TravelRequest)
            if pending_approval_ids:
                # Include both user's own TRFs and TRFs pending their approval
                from django.db.models import Q
                queryset = queryset.filter(Q(created_by=user) | Q(id__in=pending_approval_ids))
                logger.info(f" Retrieve action: Including user's TRFs and {len(pending_approval_ids)} TRFs pending approval")
                return queryset

        # Check if this is an admin view (Admin module for TRF/Ticketing)
        admin_view = self.request.query_params.get('admin_view', 'false').lower() == 'true'

        # Permission-based filtering
        if admin_view and user.role:
            # Admin module context - check permissions
            can_view_all = user.role.permissions.filter(name='view_all_trf').exists()

            if can_view_all:
                logger.info(f" Admin view: User (role: {user.role.name}) has 'view_all_trf' permission - showing all TRFs")
                pass  # No filtering - show all

            # Department-level approvers see TRFs from their department
            elif user.role.permissions.filter(name__in=['approve_trf', 'view_pending_approvals']).exists():
                if user.department:
                    logger.info(f" Admin view: Approver role ({user.role.name}) - showing TRFs from department: {user.department}")
                    queryset = queryset.filter(department=user.department)
                else:
                    logger.warning(f" Admin view: Approver role ({user.role.name}) but no department set - showing only own TRFs")
                    queryset = queryset.filter(created_by=user)
            else:
                # No admin permissions - show only own TRFs plus those pending approval
                pending_approval_ids = WorkflowApprovalHelper.get_pending_entity_ids_for_user(user, TravelRequest)
                if pending_approval_ids:
                    from django.db.models import Q
                    queryset = queryset.filter(Q(created_by=user) | Q(id__in=pending_approval_ids))
                    logger.info(f" Admin view: User lacks permission - showing own TRFs plus {len(pending_approval_ids)} pending approval")
                else:
                    queryset = queryset.filter(created_by=user)
                    logger.warning(f" Admin view: User lacks permission - showing only own TRFs")
        else:
            # Personal requests view - show only user's own TRFs
            queryset = queryset.filter(created_by=user)
            logger.info(f" Personal view: User {user.username} - showing only own TRFs (created_by={user.id})")

        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            # Use startswith to match workflow statuses like "Pending Line Manager"
            # when filter is "Pending"
            queryset = queryset.filter(status__istartswith=status_filter)

        # Filter by travel type
        travel_type = self.request.query_params.get('travel_type', None)
        if travel_type:
            queryset = queryset.filter(travel_type=travel_type)

        # Filter by department
        department = self.request.query_params.get('department', None)
        if department:
            queryset = queryset.filter(department__icontains=department)

        # Filter by requestor name
        requestor_name = self.request.query_params.get('requestor_name', None)
        if requestor_name:
            queryset = queryset.filter(requestor_name__icontains=requestor_name)

        # Search across multiple fields
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(requestor_name__icontains=search) |
                Q(department__icontains=search) |
                Q(purpose__icontains=search) |
                Q(staff_id__icontains=search) |
                Q(request_number__icontains=search)
            )

        # Handle custom sortBy and sortOrder parameters from frontend
        sort_by = self.request.query_params.get('sortBy', None)
        sort_order = self.request.query_params.get('sortOrder', 'descending')

        if sort_by and sort_by in self.ordering_fields:
            # Apply sorting: prefix with - for descending
            order_field = f"-{sort_by}" if sort_order == 'descending' else sort_by
            result = queryset.order_by(order_field)
        else:
            # Default ordering
            result = queryset.order_by('-created_at')

        logger.debug(f"Filtered queryset count: {result.count()}")
        logger.debug(f"=== END GET_QUERYSET ===\n")
        return result

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """
        Submit a TRF for approval
        Changes status from Draft to Pending and starts workflow
        """
        trf = self.get_object()

        if trf.status != 'Draft':
            return error_response(
                message='Only draft TRFs can be submitted',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Generate request number if it doesn't exist
        if not trf.request_number:
            try:
                # Get itinerary segments to extract context
                itinerary_segments = list(trf.trfitinerarysegment_set.all().values(
                    'to_location', 'from_location', 'departure_time', 'arrival_time'
                ))

                logger.debug(f" Itinerary segments for TRF #{trf.id}: {itinerary_segments}")

                # Extract context from itinerary (first destination)
                context = extract_context_from_itinerary(itinerary_segments) if itinerary_segments else 'TRF'
                logger.debug(f" Extracted context: {context}")

                # Generate unique request number
                request_number = generate_request_id('TSR', context)
                trf.request_number = request_number
                logger.info(f" Generated request number: {request_number}")
            except Exception as e:
                logger.error(f" Error generating request number: {str(e)}")
                import traceback
                traceback.print_exc()
                # Fallback to simple format
                from datetime import datetime
                trf.request_number = f"TSR-{datetime.now().strftime('%Y%m%d-%H%M')}-TRF-{trf.id}"
                logger.warning(f" Using fallback request number: {trf.request_number}")

        # Update status and submitted_at
        trf.status = 'Pending'
        trf.submitted_at = timezone.now()
        trf.save()

        # Extract selected approvers from request data (optional)
        selected_approvers = request.data.get('selected_approvers', None)
        if selected_approvers:
            # Convert string keys to integers for consistency
            selected_approvers = {int(k): v for k, v in selected_approvers.items()}

        # Extract skipped steps from request data (optional)
        # Skipped steps are for approvers that are not available or not designated
        skipped_steps = request.data.get('skipped_steps', None)
        if skipped_steps:
            # Convert string keys to integers for consistency
            skipped_steps = {int(k): v for k, v in skipped_steps.items()}

        # Start workflow using WorkflowRouter
        try:
            workflow_instance = WorkflowRouter.start_workflow_for_request(
                entity=trf,
                entity_type='travelrequest',
                initiated_by=request.user,
                selected_approvers=selected_approvers,
                skipped_steps=skipped_steps
            )

            if workflow_instance:
                # Reload the TRF to get the updated status from workflow
                trf.refresh_from_db()
                logger.info(f" Workflow started for TRF #{trf.id}: Workflow Instance #{workflow_instance.id}")
                logger.info(f" Status updated to: {trf.status}")
            else:
                # Fallback to legacy approval system if no workflow configured
                logger.warning(f" No active workflow configured - creating legacy approval step")
                TrfApprovalStep.objects.create(
                    trf=trf,
                    step_role='Department Focal',
                    step_name='Department Focal Review',
                    status='Pending'
                )
                trf.status = 'Pending Department Focal'
                trf.save()
        except Exception as e:
            logger.error(f" Error starting workflow: {str(e)}")
            # Fallback to legacy system on error
            TrfApprovalStep.objects.create(
                trf=trf,
                step_role='Department Focal',
                step_name='Department Focal Review',
                status='Pending'
            )
            trf.status = 'Pending Department Focal'
            trf.save()

        # Ensure we have the latest status before serializing
        trf.refresh_from_db()
        serializer = TravelRequestDetailSerializer(trf)
        return success_response(
            data=serializer.data,
            message='Travel request submitted successfully',
            status_code=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a TRF at current approval step using WorkflowEngine"""
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType

        trf = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)

        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors,
                message='Invalid approval data'
            )

        step_role = serializer.validated_data['step_role']
        comments = serializer.validated_data.get('comments', '')

        try:
            # Get the workflow instance for this TRF
            content_type = ContentType.objects.get_for_model(trf)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=trf.id,
                status='in_progress'
            ).first()

            logger.debug(f" Approving TRF #{trf.id}")
            logger.debug(f" User: {request.user.email}, is_staff={request.user.is_staff}, is_superuser={request.user.is_superuser}")
            logger.debug(f" Workflow instance found: {workflow_instance is not None}")

            if workflow_instance:
                # Find the current pending step (by order)
                # The WorkflowEngine will validate if the user is authorized
                current_step = workflow_instance.step_executions.filter(
                    status='pending'
                ).order_by('workflow_step__step_order').first()

                logger.debug(f" Pending step found: {current_step is not None}")
                if current_step:
                    logger.debug(f" Step: {current_step.workflow_step.step_name}, assigned_to: {current_step.assigned_to}")

                if current_step:
                    # Use workflow engine to process approval
                    result = WorkflowEngine.process_action(
                        step_execution_id=current_step.id,
                        action='approve',
                        actioned_by=request.user,
                        comments=comments
                    )

                    # Reload TRF to get updated status
                    trf.refresh_from_db()

                    # Also update legacy approval step for backward compatibility
                    approval_step, created = TrfApprovalStep.objects.get_or_create(
                        trf=trf,
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

                    trf_serializer = TravelRequestDetailSerializer(trf)
                    return success_response(
                        data=trf_serializer.data,
                        message='Travel request approved successfully',
                        status_code=status.HTTP_200_OK
                    )
                else:
                    return error_response(
                        message='No pending approval step found for this role',
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Fallback to legacy manual approval if no workflow found
                logger.warning(f" No workflow instance found for TRF #{trf.id}, using legacy approval")

                # Find or create approval step for this role
                approval_step, created = TrfApprovalStep.objects.get_or_create(
                    trf=trf,
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

                # Update TRF status based on approval workflow
                status_progression = {
                    'Department Focal': 'Pending HOD',
                    'HOD': 'Pending Travel Desk',
                    'Travel Desk': 'Pending Finance',
                    'Finance': 'Approved'
                }

                if step_role in status_progression:
                    trf.status = status_progression[step_role]
                    trf.save()

                    # Create next approval step if not final
                    if trf.status != 'Approved':
                        next_role = trf.status.replace('Pending ', '')
                        TrfApprovalStep.objects.get_or_create(
                            trf=trf,
                            step_role=next_role,
                            defaults={
                                'step_name': f'{next_role} Review',
                                'status': 'Pending'
                            }
                        )

                trf_serializer = TravelRequestDetailSerializer(trf)
                return success_response(
                    data=trf_serializer.data,
                    message='Travel request approved successfully',
                    status_code=status.HTTP_200_OK
                )

        except ValueError as e:
            # ValueError is raised by WorkflowEngine for authorization failures
            logger.error(f" ValueError in approve workflow: {str(e)}")
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f" Error in approve workflow: {str(e)}")
            import traceback
            traceback.print_exc()
            return server_error_response(
                message='Failed to process approval',
                error_details=str(e)
            )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a TRF using WorkflowEngine"""
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType

        trf = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)

        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors,
                message='Invalid rejection data'
            )

        step_role = serializer.validated_data['step_role']
        comments = serializer.validated_data.get('comments', '')

        try:
            # Get the workflow instance for this TRF
            content_type = ContentType.objects.get_for_model(trf)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=trf.id,
                status='in_progress'
            ).first()

            if workflow_instance:
                # Find the current step execution for the given role
                current_step = workflow_instance.step_executions.filter(
                    status='pending'
                ).order_by('workflow_step__step_order').first()

                if current_step:
                    # Use workflow engine to process rejection
                    result = WorkflowEngine.process_action(
                        step_execution_id=current_step.id,
                        action='reject',
                        actioned_by=request.user,
                        comments=comments
                    )

                    # Reload TRF to get updated status
                    trf.refresh_from_db()

                    # Also update legacy approval step for backward compatibility
                    approval_step, created = TrfApprovalStep.objects.get_or_create(
                        trf=trf,
                        step_role=step_role,
                        defaults={
                            'step_name': f'{step_role} Approval',
                            'status': 'Pending'
                        }
                    )
                    approval_step.status = 'Rejected'
                    approval_step.comments = comments
                    approval_step.step_date = datetime.now()
                    approval_step.save()

                    trf_serializer = TravelRequestDetailSerializer(trf)
                    return success_response(
                        data=trf_serializer.data,
                        message='Travel request rejected successfully',
                        status_code=status.HTTP_200_OK
                    )
                else:
                    return error_response(
                        message='No pending approval step found',
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Fallback to legacy manual rejection if no workflow found
                logger.warning(f" No workflow instance found for TRF #{trf.id}, using legacy rejection")

                # Find or create approval step for this role
                approval_step, created = TrfApprovalStep.objects.get_or_create(
                    trf=trf,
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

                # Update TRF status
                trf.status = 'Rejected'
                trf.save()

                trf_serializer = TravelRequestDetailSerializer(trf)
                return success_response(
                    data=trf_serializer.data,
                    message='Travel request rejected successfully',
                    status_code=status.HTTP_200_OK
                )

        except Exception as e:
            logger.error(f" Error in reject workflow: {str(e)}")
            import traceback
            traceback.print_exc()
            return server_error_response(
                message='Failed to process rejection',
                error_details=str(e)
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a TRF"""
        trf = self.get_object()

        if trf.status in ['Approved', 'Completed']:
            return error_response(
                message='Approved or completed TRFs cannot be cancelled',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        trf.status = 'Cancelled'
        trf.save()

        serializer = self.get_serializer(trf)
        return success_response(
            data=serializer.data,
            message='Travel request cancelled successfully',
            status_code=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'], url_path='check-accommodation-availability')
    def check_accommodation_availability(self, request, pk=None):
        """
        Check if this TSR is available for accommodation booking
        Returns:
        - is_available: boolean
        - date_range: {start_date, end_date} from itinerary
        - existing_accommodation: accommodation request details if already linked
        """
        trf = self.get_object()

        # Check if TSR is already linked to an accommodation request
        from accommodation.models import AccommodationRequest
        existing_accommodation = AccommodationRequest.objects.filter(trf=trf).first()

        # Get TSR date range from itinerary
        itinerary_segments = TrfItinerarySegment.objects.filter(
            trf=trf
        ).exclude(segment_date__isnull=True).order_by('segment_date')

        date_range = None
        if itinerary_segments.exists():
            first_segment = itinerary_segments.first()
            last_segment = itinerary_segments.last()
            date_range = {
                'start_date': first_segment.segment_date.strftime('%Y-%m-%d'),
                'end_date': last_segment.segment_date.strftime('%Y-%m-%d')
            }

        response_data = {
            'is_available': existing_accommodation is None,
            'date_range': date_range,
            'tsr_id': trf.id,
            'tsr_request_number': trf.request_number
        }

        if existing_accommodation:
            response_data['existing_accommodation'] = {
                'id': existing_accommodation.id,
                'request_number': existing_accommodation.request_number,
                'status': existing_accommodation.status,
                'requestor_name': existing_accommodation.requestor_name
            }

        return success_response(
            data=response_data,
            message='Accommodation availability checked',
            status_code=status.HTTP_200_OK
        )

    @action(detail=True, methods=['delete'], url_path='delete-itinerary')
    def delete_itinerary(self, request, pk=None):
        """Delete all itinerary segments for a TRF"""
        trf = self.get_object()
        count = TrfItinerarySegment.objects.filter(trf=trf).delete()[0]
        return success_response(
            data={'deleted': count},
            message=f'Deleted {count} itinerary segment(s)',
            status_code=status.HTTP_200_OK
        )

    @action(detail=True, methods=['delete'], url_path='delete-meals')
    def delete_meals(self, request, pk=None):
        """Delete all meal selections for a TRF"""
        trf = self.get_object()
        count = TrfDailyMealSelection.objects.filter(trf=trf).delete()[0]
        return success_response(
            data={'deleted': count},
            message=f'Deleted {count} meal selection(s)',
            status_code=status.HTTP_200_OK
        )

    @action(detail=True, methods=['delete'], url_path='delete-passport')
    def delete_passport(self, request, pk=None):
        """Delete all passport details for a TRF"""
        trf = self.get_object()
        count = TrfPassportDetail.objects.filter(trf=trf).delete()[0]
        return success_response(
            data={'deleted': count},
            message=f'Deleted {count} passport detail(s)',
            status_code=status.HTTP_200_OK
        )

    @action(detail=True, methods=['delete'], url_path='delete-bank')
    def delete_bank(self, request, pk=None):
        """Delete bank details for a TRF"""
        trf = self.get_object()
        count = TrfAdvanceBankDetail.objects.filter(trf=trf).delete()[0]
        return success_response(
            data={'deleted': count},
            message=f'Deleted {count} bank detail(s)',
            status_code=status.HTTP_200_OK
        )

    @action(detail=True, methods=['delete'], url_path='delete-advance-amounts')
    def delete_advance_amounts(self, request, pk=None):
        """Delete all advance amount items for a TRF"""
        trf = self.get_object()
        count = TrfAdvanceAmountRequestedItem.objects.filter(trf=trf).delete()[0]
        return success_response(
            data={'deleted': count},
            message=f'Deleted {count} advance amount(s)',
            status_code=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='pending-approvals')
    def pending_approvals(self, request):
        """Get TRFs pending approval for the current user based on workflow step assignments"""
        from accounts.utils import is_module_admin
        from workflows.services import WorkflowApprovalHelper

        user = request.user

        # Admins and superusers see all pending requests
        # Use startswith to match any workflow-generated 'Pending *' status
        if user.is_superuser or is_module_admin(user, 'trf'):
            queryset = TravelRequest.objects.filter(
                Q(status__startswith='Pending') |
                Q(status='Submitted') |
                Q(status='Under Review')
            ).order_by('-submitted_at')
        else:
            # Use workflow-based filtering: get entities where user's role matches current step
            pending_ids = WorkflowApprovalHelper.get_pending_entity_ids_for_user(user, TravelRequest)
            queryset = TravelRequest.objects.filter(id__in=pending_ids).order_by('-submitted_at')

        # Use detail serializer to include nested data (itinerary, accommodation, etc.)
        serializer = TravelRequestDetailSerializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message=f'Retrieved {queryset.count()} pending approval(s)',
            status_code=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='admin/book-flight')
    def book_flight(self, request, pk=None):
        """
        Book a flight for an approved TRF
        Creates a FlightBooking record and links it to the TRF

        Expected payload:
        {
            "pnr": "ABC123",
            "airline": "MH",
            "flightNumber": "MH123",
            "departureAirport": "KUL",
            "arrivalAirport": "LHR",
            "departureDateTime": "2025-12-01T10:00:00",
            "arrivalDateTime": "2025-12-01T18:00:00",
            "flightNotes": "Optional notes"
        }
        """
        from bookings.models import FlightBooking
        from datetime import datetime
        import traceback

        trf = self.get_object()

        logger.debug(f"\n=== BOOK FLIGHT DEBUG ===")
        logger.debug(f"TRF ID: {trf.id}")
        logger.debug(f"TRF Status: [{trf.status}]")
        logger.debug(f"TRF Travel Type: {trf.travel_type}")
        logger.debug(f"Request Data: {request.data}")
        logger.debug(f"========================\n")

        # Validate TRF status - allow booking for approved TRFs or updating existing bookings
        allowed_statuses = ['Approved', 'Flight Booked', 'Hotel Booked', 'Processing', 'Ready for Booking']
        if trf.status not in allowed_statuses:
            error_msg = f'Flights can only be booked for approved TRFs. Current status: {trf.status}'
            logger.error(f" Status validation failed: {error_msg}")
            return error_response(
                message=error_msg,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Extract booking data from request
        pnr = request.data.get('pnr', '')
        airline = request.data.get('airline', '')
        flight_number = request.data.get('flightNumber', '')
        departure_airport = request.data.get('departureAirport', '')
        arrival_airport = request.data.get('arrivalAirport', '')
        departure_datetime_str = request.data.get('departureDateTime')
        arrival_datetime_str = request.data.get('arrivalDateTime')
        flight_notes = request.data.get('flightNotes', '')

        logger.debug(f"Extracted data:")
        logger.debug(f"  PNR: {pnr}")
        logger.debug(f"  Airline: {airline}")
        logger.debug(f"  Flight Number: {flight_number}")
        logger.debug(f"  Departure Airport: {departure_airport}")
        logger.debug(f"  Arrival Airport: {arrival_airport}")
        logger.debug(f"  Departure DateTime: {departure_datetime_str}")
        logger.debug(f"  Arrival DateTime: {arrival_datetime_str}")

        # Validate required fields
        if not all([pnr, airline, flight_number, departure_airport, arrival_airport]):
            missing = []
            if not pnr: missing.append('pnr')
            if not airline: missing.append('airline')
            if not flight_number: missing.append('flightNumber')
            if not departure_airport: missing.append('departureAirport')
            if not arrival_airport: missing.append('arrivalAirport')
            error_msg = f'Missing required fields: {", ".join(missing)}'
            logger.error(f" Field validation failed: {error_msg}")
            return error_response(
                message=error_msg,
                errors={'missing_fields': missing},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Parse datetime strings
        try:
            if departure_datetime_str:
                # Handle both with and without timezone
                departure_time = datetime.fromisoformat(departure_datetime_str.replace('Z', '+00:00'))
                if departure_time.tzinfo is None:
                    from django.utils import timezone as django_tz
                    departure_time = django_tz.make_aware(departure_time)
            else:
                departure_time = timezone.now()

            if arrival_datetime_str:
                arrival_time = datetime.fromisoformat(arrival_datetime_str.replace('Z', '+00:00'))
                if arrival_time.tzinfo is None:
                    from django.utils import timezone as django_tz
                    arrival_time = django_tz.make_aware(arrival_time)
            else:
                arrival_time = timezone.now()

            logger.debug(f"Parsed datetimes:")
            logger.debug(f"  Departure: {departure_time}")
            logger.debug(f"  Arrival: {arrival_time}")
        except (ValueError, TypeError) as e:
            error_msg = f'Invalid datetime format: {str(e)}'
            logger.error(f" DateTime parsing failed: {error_msg}")
            traceback.print_exc()
            return error_response(
                message=error_msg,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Check if a flight booking already exists for this TRF
        existing_booking = FlightBooking.objects.filter(trf=trf).first()
        if existing_booking:
            # Check if the new PNR is used by a different booking
            if existing_booking.booking_reference != pnr:
                if FlightBooking.objects.filter(booking_reference=pnr).exclude(id=existing_booking.id).exists():
                    return error_response(
                        message=f'Booking reference "{pnr}" is already in use by another booking. Please use a unique PNR.',
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            # Update existing booking instead of creating a new one
            existing_booking.airline = airline
            existing_booking.flight_number = flight_number
            existing_booking.departure_airport = departure_airport
            existing_booking.arrival_airport = arrival_airport
            existing_booking.departure_time = departure_time
            existing_booking.arrival_time = arrival_time
            existing_booking.booking_reference = pnr
            existing_booking.status = 'CONFIRMED'
            existing_booking.booked_by = request.user
            existing_booking.confirmation_date = timezone.now()
            existing_booking.notes = flight_notes
            existing_booking.save()
            flight_booking = existing_booking
            logger.info(f" Updated existing flight booking {flight_booking.id} for TRF {trf.id}")
        else:
            # Check if PNR is already used by another booking
            if FlightBooking.objects.filter(booking_reference=pnr).exists():
                return error_response(
                    message=f'Booking reference "{pnr}" is already in use. Please use a unique PNR.',
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Create FlightBooking
            flight_booking = FlightBooking.objects.create(
                trf=trf,
                user=trf.created_by if trf.created_by else request.user,
                airline=airline,
                flight_number=flight_number,
                departure_airport=departure_airport,
                arrival_airport=arrival_airport,
                departure_time=departure_time,
                arrival_time=arrival_time,
                booking_reference=pnr,
                status='CONFIRMED',
                cost=0,  # Can be added later
                booked_by=request.user,
                booking_date=timezone.now(),
                confirmation_date=timezone.now(),
                notes=flight_notes
            )
            logger.info(f" Created new flight booking {flight_booking.id} for TRF {trf.id}")

        # Update TRF status to indicate flight is booked
        trf.status = 'Flight Booked'
        trf.save()

        # Return updated TRF data
        serializer = TravelRequestDetailSerializer(trf)
        return created_response(
            data={
                'trf': serializer.data,
                'flight_booking': {
                    'id': flight_booking.id,
                    'booking_reference': flight_booking.booking_reference,
                    'status': flight_booking.status
                }
            },
            message='Flight booking created successfully'
        )

    @action(detail=True, methods=['get'], url_path='export-pdf')
    def export_pdf(self, request, pk=None):
        """
        Export Travel Request to PDF

        Returns a PDF document containing all TRF details including:
        - Requestor information
        - Travel itinerary
        - Meal provisions
        - Passport details
        - Bank details for advance payments
        - Approval history
        """
        import io
        from django.http import HttpResponse
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

        try:
            trf = TravelRequest.objects.get(pk=pk)
        except TravelRequest.DoesNotExist:
            return not_found_response(message='Travel Request not found')

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
        title = f"Travel Service Request - {trf.request_number or f'TSR-{trf.id}'}"
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 12))

        # Status badge
        status_text = f"<b>Status:</b> {trf.status}"
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
            ['Name', trf.requestor_name or '-'],
            ['Staff ID', trf.staff_id or '-'],
            ['Department', trf.department or '-'],
            ['Position', trf.position or '-'],
            ['Cost Center', trf.cost_center or '-'],
            ['Email', trf.email or '-'],
            ['Phone/Email', trf.tel_email or '-'],
        ]
        requestor_table = Table(requestor_data, colWidths=[2*inch, 5*inch])
        requestor_table.setStyle(table_style)
        elements.append(requestor_table)

        # Travel Details
        elements.append(Paragraph("Travel Details", heading_style))
        travel_data = [
            ['Field', 'Value'],
            ['Travel Type', trf.travel_type or '-'],
            ['Purpose', (trf.purpose or '-')[:100]],
            ['Estimated Cost', f"${trf.estimated_cost:,.2f}" if trf.estimated_cost else '-'],
            ['Submitted At', trf.submitted_at.strftime('%Y-%m-%d %H:%M') if trf.submitted_at else '-'],
            ['Created At', trf.created_at.strftime('%Y-%m-%d %H:%M') if trf.created_at else '-'],
        ]
        travel_table = Table(travel_data, colWidths=[2*inch, 5*inch])
        travel_table.setStyle(table_style)
        elements.append(travel_table)

        # Itinerary Segments
        itinerary_segments = TrfItinerarySegment.objects.filter(trf=trf).order_by('segment_date')
        if itinerary_segments.exists():
            elements.append(Paragraph("Itinerary", heading_style))
            itinerary_data = [['Date', 'From', 'To', 'Departure', 'Arrival', 'Purpose']]
            for seg in itinerary_segments:
                itinerary_data.append([
                    seg.segment_date.strftime('%Y-%m-%d') if seg.segment_date else '-',
                    seg.from_location or '-',
                    seg.to_location or '-',
                    seg.departure_time or '-',
                    seg.arrival_time or '-',
                    (seg.purpose or '-')[:30]
                ])
            itinerary_table = Table(itinerary_data, colWidths=[1*inch, 1.2*inch, 1.2*inch, 0.9*inch, 0.9*inch, 1.8*inch])
            itinerary_table.setStyle(table_style)
            elements.append(itinerary_table)

        # Passport Details
        passport_details = TrfPassportDetail.objects.filter(trf=trf)
        if passport_details.exists():
            elements.append(Paragraph("Passport Details", heading_style))
            passport_data = [['Name', 'Passport No.', 'Nationality', 'Date of Birth', 'Expiry']]
            for passport in passport_details:
                passport_data.append([
                    passport.full_name or '-',
                    passport.passport_number or '-',
                    passport.nationality or '-',
                    passport.date_of_birth.strftime('%Y-%m-%d') if passport.date_of_birth else '-',
                    passport.expiry_date.strftime('%Y-%m-%d') if hasattr(passport, 'expiry_date') and passport.expiry_date else '-'
                ])
            passport_table = Table(passport_data, colWidths=[1.5*inch, 1.3*inch, 1.2*inch, 1.2*inch, 1*inch])
            passport_table.setStyle(table_style)
            elements.append(passport_table)

        # Bank Details
        try:
            bank_detail = TrfAdvanceBankDetail.objects.get(trf=trf)
            elements.append(Paragraph("Bank Details for Advance", heading_style))
            bank_data = [
                ['Field', 'Value'],
                ['Bank Name', bank_detail.bank_name or '-'],
                ['Account Name', bank_detail.account_name or '-'],
                ['Account Number', bank_detail.account_number or '-'],
                ['Currency', bank_detail.currency or '-'],
                ['Amount', f"{bank_detail.amount:,.2f}" if bank_detail.amount else '-'],
            ]
            bank_table = Table(bank_data, colWidths=[2*inch, 5*inch])
            bank_table.setStyle(table_style)
            elements.append(bank_table)
        except TrfAdvanceBankDetail.DoesNotExist:
            pass

        # Approval History
        approval_steps = TrfApprovalStep.objects.filter(trf=trf).order_by('created_at')
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
        filename = f"TSR-{trf.request_number or trf.id}.pdf"
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


# =============== NESTED RESOURCE VIEWSETS ===============

class TrfAdvanceAmountRequestedItemViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Advance Amount Requested Items"""
    queryset = TrfAdvanceAmountRequestedItem.objects.all()
    serializer_class = TrfAdvanceAmountRequestedItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by('-created_at')


class TrfAdvanceBankDetailViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Advance Bank Details"""
    queryset = TrfAdvanceBankDetail.objects.all()
    serializer_class = TrfAdvanceBankDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by('-created_at')


class TrfApprovalStepViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Approval Steps"""
    queryset = TrfApprovalStep.objects.all()
    serializer_class = TrfApprovalStepSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by('-created_at')


class TrfDailyMealSelectionViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Daily Meal Selections"""
    queryset = TrfDailyMealSelection.objects.all()
    serializer_class = TrfDailyMealSelectionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        logger.debug(f"\n=== TrfDailyMealSelection CREATE ===")
        logger.debug(f"Request data: {request.data}")
        logger.debug(f"TRF field value: {request.data.get('trf')}")
        logger.debug(f"Meal date value: {request.data.get('meal_date')}")
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by('meal_date')


class TrfFlightBookingViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Flight Bookings"""
    queryset = TrfFlightBooking.objects.all()
    serializer_class = TrfFlightBookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by('departure_date', 'departure_time')


class TrfItinerarySegmentViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Itinerary Segments"""
    queryset = TrfItinerarySegment.objects.all()
    serializer_class = TrfItinerarySegmentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        logger.debug(f"\n=== TrfItinerarySegment CREATE ===")
        logger.debug(f"Request data: {request.data}")
        logger.debug(f"TRF field value: {request.data.get('trf')}")
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by('segment_date')


class TrfMealProvisionViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Meal Provisions"""
    queryset = TrfMealProvision.objects.all()
    serializer_class = TrfMealProvisionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by('-created_at')


class TrfPassportDetailViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Passport Details with file upload support"""
    queryset = TrfPassportDetail.objects.all()
    serializer_class = TrfPassportDetailSerializer
    permission_classes = [IsAuthenticated]
    # Support both JSON and multipart for file uploads
    parser_classes = None  # Will use default parsers including MultiPartParser

    def get_serializer_context(self):
        """Include request in serializer context for building absolute URLs"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_queryset(self):
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by('-created_at')

    @action(detail=True, methods=['post'], url_path='upload-passport')
    def upload_passport(self, request, pk=None):
        """
        Upload or update passport file for an existing passport detail record.
        Accepts multipart/form-data with 'passport_file' field.
        """
        passport_detail = self.get_object()

        if 'passport_file' not in request.FILES:
            return error_response(
                message='No passport file provided',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        passport_file = request.FILES['passport_file']

        # Validate file type
        allowed_types = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']
        if passport_file.content_type not in allowed_types:
            return error_response(
                message='Passport file must be PDF, JPG, or PNG format',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024
        if passport_file.size > max_size:
            return error_response(
                message='Passport file size must not exceed 10MB',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Delete old file if exists
        if passport_detail.passport_file:
            passport_detail.passport_file.delete(save=False)

        # Save new file
        passport_detail.passport_file = passport_file
        passport_detail.save()

        serializer = self.get_serializer(passport_detail)
        return success_response(
            data=serializer.data,
            message='Passport file uploaded successfully',
            status_code=status.HTTP_200_OK
        )

    @action(detail=True, methods=['delete'], url_path='delete-passport-file')
    def delete_passport_file(self, request, pk=None):
        """Delete the passport file from an existing passport detail record."""
        passport_detail = self.get_object()

        if not passport_detail.passport_file:
            return error_response(
                message='No passport file to delete',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Delete the file
        passport_detail.passport_file.delete(save=True)

        serializer = self.get_serializer(passport_detail)
        return success_response(
            data=serializer.data,
            message='Passport file deleted successfully',
            status_code=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'], url_path='upload-for-trf')
    def upload_for_trf(self, request):
        """
        Upload passport file for a TRF. Creates passport detail if it doesn't exist.
        Expects: trf (TRF ID) and passport_file in multipart/form-data
        """
        trf_id = request.data.get('trf')
        if not trf_id:
            return error_response(
                message='TRF ID is required',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if 'passport_file' not in request.FILES:
            return error_response(
                message='No passport file provided',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        passport_file = request.FILES['passport_file']

        # Validate file type
        allowed_types = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']
        if passport_file.content_type not in allowed_types:
            return error_response(
                message='Passport file must be PDF, JPG, or PNG format',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024
        if passport_file.size > max_size:
            return error_response(
                message='Passport file size must not exceed 10MB',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Verify TRF exists
        try:
            trf = TravelRequest.objects.get(pk=trf_id)
        except TravelRequest.DoesNotExist:
            return not_found_response(message='TRF not found')

        # Get or create passport detail for this TRF
        passport_detail, created = TrfPassportDetail.objects.get_or_create(
            trf=trf,
            defaults={}
        )

        # Delete old file if exists
        if passport_detail.passport_file:
            passport_detail.passport_file.delete(save=False)

        # Save new file
        passport_detail.passport_file = passport_file
        passport_detail.save()

        serializer = self.get_serializer(passport_detail)
        return success_response(
            data=serializer.data,
            message='Passport file uploaded successfully',
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
