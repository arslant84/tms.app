import logging
from datetime import datetime

from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from utils.viewset_mixins import StandardResultsPagination

logger = logging.getLogger(__name__)
from accounts.models import AdminActionLog
from accounts.utils import can_approve, can_manage, can_view_all, has_permission
from utils.api_response import (
    created_response,
    error_response,
    forbidden_response,
    get_pagination_params,
    not_found_response,
    paginated_response,
    server_error_response,
    success_response,
    unauthorized_response,
    validation_error_response,
)
from utils.constants import BOOKABLE_STATUSES
from utils.request_id_generator import (
    extract_context_from_itinerary,
    generate_request_id,
)
from workflows.router import WorkflowRouter

from .models import (
    TravelRequest,
    TrfAdvanceAmountRequestedItem,
    TrfAdvanceBankDetail,
    TrfApprovalStep,
    TrfDailyMealSelection,
    TrfItinerarySegment,
    TrfMealProvision,
    TrfPassportDetail,
)
from .serializers import (
    ApprovalActionSerializer,
    TravelRequestCreateSerializer,
    TravelRequestDetailSerializer,
    TravelRequestSerializer,
    TravelRequestUpdateSerializer,
    TrfAdvanceAmountRequestedItemSerializer,
    TrfAdvanceBankDetailSerializer,
    TrfApprovalStepSerializer,
    TrfDailyMealSelectionSerializer,
    TrfItinerarySegmentSerializer,
    TrfMealProvisionSerializer,
    TrfPassportDetailSerializer,
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
    pagination_class = StandardResultsPagination

    # Search across key fields
    search_fields = [
        "requestor_name",
        "department",
        "purpose",
        "staff_id",
        "request_number",
    ]

    # Allow ordering by these fields
    ordering_fields = [
        "created_at",
        "submitted_at",
        "departure_date",
        "requestor_name",
        "status",
        "request_number",
    ]
    ordering = ["-created_at"]  # Default ordering: newest first

    def get_object(self):
        """
        Override to support lookup by both numeric ID and request_number
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field or "pk"
        lookup_value = self.kwargs[lookup_url_kwarg]

        # Try to determine if it's a numeric ID or request_number
        if isinstance(lookup_value, int) or (
            isinstance(lookup_value, str) and lookup_value.isdigit()
        ):
            # Numeric ID lookup
            filter_kwargs = {"pk": int(lookup_value)}
        else:
            # Request number lookup (contains letters/dashes)
            filter_kwargs = {"request_number": lookup_value}

        queryset = self.filter_queryset(self.get_queryset())

        try:
            obj = queryset.get(**filter_kwargs)
        except TravelRequest.DoesNotExist:
            from rest_framework.exceptions import NotFound

            # Try to fetch from full queryset to get request_number for better error message
            try:
                obj = TravelRequest.objects.get(**filter_kwargs)
                request_identifier = obj.request_number or f"ID #{obj.id}"
                raise NotFound(
                    f"Travel request {request_identifier} not found or you do not have permission to access it"
                )
            except TravelRequest.DoesNotExist:
                raise NotFound(
                    f"Travel request not found with identifier: {lookup_value}"
                )

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def get_serializer_class(self):
        """Use appropriate serializer based on action"""
        if self.action == "retrieve":
            return TravelRequestDetailSerializer
        elif self.action == "create":
            return TravelRequestCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return TravelRequestUpdateSerializer
        return TravelRequestSerializer

    def create(self, request, *args, **kwargs):
        """Create a new TRF with logging"""
        if not request.user.is_superuser and not has_permission(
            request.user, "create_trf"
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not have permission to create TRFs.")
        logger.debug("\n=== TravelRequest CREATE ===")
        logger.debug(f"Request data: {request.data}")
        response = super().create(request, *args, **kwargs)
        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response data: {response.data}")
        logger.debug(
            f"Response data keys: {list(response.data.keys()) if hasattr(response.data, 'keys') else 'N/A'}"
        )
        return response

    def perform_create(self, serializer):
        """Set creator and auto-populate requestor info, start workflow if submitted"""
        user = self.request.user

        # Auto-populate requestor information if not provided
        validated_data = serializer.validated_data
        if not validated_data.get("requestor_name"):
            validated_data["requestor_name"] = user.get_full_name() or user.email
        if not validated_data.get("staff_id"):
            validated_data["staff_id"] = getattr(user, "employee_id", "") or getattr(
                user, "staff_id", ""
            )
        if not validated_data.get("department"):
            validated_data["department"] = getattr(user, "department", "")
        if not validated_data.get("position"):
            validated_data["position"] = getattr(user, "position", "") or getattr(
                user, "job_title", ""
            )

        # Get status from request data, default to 'Draft' if not provided
        status_value = validated_data.get("status", "Draft")

        # Set submitted_at timestamp if status is being submitted (not Draft)
        extra_kwargs = {}
        if status_value not in ["Draft"]:
            extra_kwargs["submitted_at"] = timezone.now()

        # Save the travel request
        trf = serializer.save(created_by=user, **extra_kwargs)

        # Start workflow if status is submitted (not Draft)
        if status_value not in ["Draft"]:
            # Extract selected approvers from request data (optional)
            selected_approvers = self.request.data.get("selected_approvers", None)
            if selected_approvers:
                selected_approvers = {int(k): v for k, v in selected_approvers.items()}

            # Extract skipped steps from request data (optional)
            skipped_steps = self.request.data.get("skipped_steps", None)
            if skipped_steps:
                skipped_steps = {int(k): v for k, v in skipped_steps.items()}

            try:
                workflow_instance = WorkflowRouter.start_workflow_for_request(
                    entity=trf,
                    entity_type=trf.workflow_entity_type,
                    initiated_by=user,
                    selected_approvers=selected_approvers,
                    skipped_steps=skipped_steps,
                    fallback_entity_type="travelrequest",
                )

                if workflow_instance:
                    # Reload the TRF to get the updated status from workflow
                    trf.refresh_from_db()
                    logger.info(
                        f" Workflow started for TRF #{trf.id}: Workflow Instance #{workflow_instance.id}"
                    )
                    logger.info(f" Status updated to: {trf.status}")
                else:
                    logger.warning(
                        " No active workflow configured for travelrequest - using legacy approval system"
                    )
            except Exception as e:
                logger.error(f" Error starting workflow for TRF #{trf.id}: {str(e)}")
                # Don't fail the request creation if workflow fails
                pass

    def perform_destroy(self, instance):
        """Log deletion before removing the record, since nothing else audits this."""
        AdminActionLog.log_action(
            user=self.request.user,
            action_type="entity_deleted",
            description=f"Deleted TRF #{instance.id} ({instance.request_number or 'no request number'})",
            entity_type="travelrequest",
            entity_id=str(instance.id),
            request=self.request,
        )
        super().perform_destroy(instance)

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

        logger.debug("\n=== TravelRequest GET_QUERYSET ===")
        logger.debug(f"Total TRFs in database: {TravelRequest.objects.count()}")
        logger.debug(f"Query params: {dict(self.request.query_params)}")
        logger.debug(f"Action: {self.action}")
        logger.debug(f"User: {user}")
        logger.debug(f"User role: {user.role.name if user.role else 'No role'}")

        # For approval actions, allow access to TRFs pending the user's approval
        if self.action in ["approve", "reject"]:
            logger.info(
                " Approval action: Allowing access to all TRFs (authorization checked in WorkflowEngine)"
            )
            return queryset  # No filtering - authorization handled by WorkflowEngine

        # For the admin book_flight action, allow access if user has booking permissions
        if self.action == "book_flight":
            logger.info(f" Booking action detected: {self.action} by user {user.email}")
            # Statuses that allow booking operations
            bookable_statuses = [
                "Approved",
                "Flight Booked",
                "Processing",
                "Ready for Booking",
            ]

            # Check if user has ticketing/booking permissions
            if (
                user.role
                and user.role.permissions.filter(
                    name__in=["manage_bookings", "view_all_trf"]
                ).exists()
            ):
                logger.info(
                    " Booking action: User has booking permissions - allowing access to bookable TRFs"
                )
                return queryset.filter(status__in=bookable_statuses)
            # Allow users with ticketing-related roles (Travel Desk, Ticketing, etc.)
            if user.role and any(
                keyword in user.role.name.lower()
                for keyword in ["ticket", "travel desk", "booking", "admin"]
            ):
                logger.info(
                    f" Booking action: User role '{user.role.name}' indicates booking capability - allowing access"
                )
                return queryset.filter(status__in=bookable_statuses)

        # Meal Admin queue and status updates: not gated by ownership, only by
        # the meal-admin permission (mirrors the "retrieve" special-case below)
        meal_queue = (
            self.request.query_params.get("meal_queue", "false").lower() == "true"
        )
        if meal_queue or self.action == "update_meal_status":
            if not (
                user.is_superuser
                or can_manage(user, "meal")
                or can_view_all(user, "meal")
            ):
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied(
                    "You do not have permission to view the meal admin queue."
                )
            if self.action == "update_meal_status" and not meal_queue:
                return queryset
            queryset = (
                queryset.filter(trfdailymealselection__isnull=False)
                .exclude(status="Draft")
                .distinct()
                .order_by("-created_at")
            )
            meal_status_filter = self.request.query_params.get("status")
            if meal_status_filter:
                queryset = queryset.filter(meal_processing_status=meal_status_filter)
            return queryset

        # For retrieve (viewing details), check view_all permission first, then pending approvals
        if self.action == "retrieve":
            # Users with view_all_trf permission can access any TRF detail (e.g. from Recent Activity)
            if user.is_superuser or can_view_all(user, "trf"):
                logger.info(
                    " Retrieve action: User has view_all_trf - allowing full access"
                )
                return queryset
            # Get IDs of TRFs pending this user's approval
            pending_approval_ids = (
                WorkflowApprovalHelper.get_pending_entity_ids_for_user(
                    user, TravelRequest
                )
            )
            queryset = queryset.filter(
                Q(created_by=user) | Q(id__in=pending_approval_ids)
            )
            logger.info(
                f" Retrieve action: Filtering to own TRFs and {len(pending_approval_ids)} pending approval"
            )
            return queryset

        # Check if this is an admin view (Admin module for TRF/Ticketing)
        admin_view = (
            self.request.query_params.get("admin_view", "false").lower() == "true"
        )

        # Permission-based filtering
        if admin_view and (user.is_superuser or user.role):
            # Admin module context - check permissions
            if user.is_superuser or can_view_all(user, "trf"):
                logger.info(
                    f" Admin view: User (role: {user.role.name if user.role else None}) has 'view_all_trf' permission - showing all TRFs"
                )
                pass  # No filtering - show all

            # Department-level approvers see TRFs from their department
            elif user.role.permissions.filter(
                name__in=["approve_trf", "view_pending_approvals"]
            ).exists():
                if user.department:
                    logger.info(
                        f" Admin view: Approver role ({user.role.name}) - showing TRFs from department: {user.department}"
                    )
                    queryset = queryset.filter(department=user.department)
                else:
                    logger.warning(
                        f" Admin view: Approver role ({user.role.name}) but no department set - showing only own TRFs"
                    )
                    queryset = queryset.filter(created_by=user)
            else:
                # No admin permissions - show only own TRFs plus those pending approval
                pending_approval_ids = (
                    WorkflowApprovalHelper.get_pending_entity_ids_for_user(
                        user, TravelRequest
                    )
                )
                if pending_approval_ids:
                    queryset = queryset.filter(
                        Q(created_by=user) | Q(id__in=pending_approval_ids)
                    )
                    logger.info(
                        f" Admin view: User lacks permission - showing own TRFs plus {len(pending_approval_ids)} pending approval"
                    )
                else:
                    queryset = queryset.filter(created_by=user)
                    logger.warning(
                        " Admin view: User lacks permission - showing only own TRFs"
                    )
        else:
            # Personal requests view - show only user's own TRFs
            queryset = queryset.filter(created_by=user)
            logger.info(
                f" Personal view: User {user.email or user.username} - showing only own TRFs (created_by={user.id})"
            )

        # Filter by status
        status_filter = self.request.query_params.get("status", None)
        if status_filter:
            # Use startswith to match workflow statuses like "Pending Line Manager"
            # when filter is "Pending"
            queryset = queryset.filter(status__istartswith=status_filter)

        # Filter by travel type
        travel_type = self.request.query_params.get("travel_type", None)
        if travel_type:
            queryset = queryset.filter(travel_type=travel_type)

        # Filter by department
        department = self.request.query_params.get("department", None)
        if department:
            queryset = queryset.filter(department__icontains=department)

        # Filter by requestor name
        requestor_name = self.request.query_params.get("requestor_name", None)
        if requestor_name:
            queryset = queryset.filter(requestor_name__icontains=requestor_name)

        # Search across multiple fields
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                Q(requestor_name__icontains=search)
                | Q(department__icontains=search)
                | Q(purpose__icontains=search)
                | Q(staff_id__icontains=search)
                | Q(request_number__icontains=search)
            )

        # Handle custom sortBy and sortOrder parameters from frontend
        sort_by = self.request.query_params.get("sortBy", None)
        sort_order = self.request.query_params.get("sortOrder", "descending")

        if sort_by and sort_by in self.ordering_fields:
            # Apply sorting: prefix with - for descending
            order_field = f"-{sort_by}" if sort_order == "descending" else sort_by
            result = queryset.order_by(order_field)
        else:
            # Default ordering
            result = queryset.order_by("-created_at")

        logger.debug(f"Filtered queryset count: {result.count()}")
        logger.debug("=== END GET_QUERYSET ===\n")
        return result

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """
        Submit a TRF for approval
        Changes status from Draft to Pending and starts workflow
        """
        trf = self.get_object()

        if trf.status != "Draft":
            return error_response(
                message="Only draft TRFs can be submitted",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Generate request number if it doesn't exist
        if not trf.request_number:
            try:
                # Get itinerary segments to extract context
                itinerary_segments = list(
                    trf.trfitinerarysegment_set.all().values(
                        "to_location", "from_location", "departure_time", "arrival_time"
                    )
                )

                logger.debug(
                    f" Itinerary segments for TRF #{trf.id}: {itinerary_segments}"
                )

                # Extract context from itinerary (first destination)
                context = (
                    extract_context_from_itinerary(itinerary_segments)
                    if itinerary_segments
                    else "TRF"
                )
                logger.debug(f" Extracted context: {context}")

                # Generate unique request number
                request_number = generate_request_id("TSR", context)
                trf.request_number = request_number
                logger.info(f" Generated request number: {request_number}")
            except Exception as e:
                logger.error(f" Error generating request number: {str(e)}")
                import traceback

                traceback.print_exc()
                # Fallback to simple format
                from datetime import datetime

                trf.request_number = (
                    f"TSR-{datetime.now().strftime('%Y%m%d-%H%M')}-TRF-{trf.id}"
                )
                logger.warning(f" Using fallback request number: {trf.request_number}")

        # Update status and submitted_at.
        #
        # A TRF that's already mid-approval (e.g. "Pending HOD") but gets
        # edited and resubmitted is reset to "Draft" by the frontend first,
        # which lets it reach this action again even though its
        # WorkflowInstance never actually stopped. In that case, don't
        # overwrite status with a generic "Pending" - the duplicate-start
        # guard in WorkflowRouter/WorkflowEngine below returns the existing
        # instance as-is without correcting it, so a generic "Pending" would
        # persist and hide which step it's actually still waiting on.
        # Instead, resync status to the real current step.
        from django.contrib.contenttypes.models import ContentType
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance, WorkflowStep

        existing_active_instance = (
            WorkflowInstance.objects.filter(
                content_type=ContentType.objects.get_for_model(trf),
                object_id=trf.id,
                status__in=["pending", "in_progress", "on_hold"],
            )
            .order_by("-started_at")
            .first()
        )

        if existing_active_instance:
            current_step = WorkflowStep.objects.filter(
                workflow_template=existing_active_instance.workflow_template,
                step_order=existing_active_instance.current_step_order,
            ).first()
            if current_step:
                WorkflowEngine._update_entity_status_from_step(
                    existing_active_instance, current_step
                )
                trf.refresh_from_db()
        else:
            trf.status = "Pending"

        trf.submitted_at = timezone.now()
        trf.save()

        # Extract selected approvers from request data (optional)
        selected_approvers = request.data.get("selected_approvers", None)
        if selected_approvers:
            # Convert string keys to integers for consistency
            selected_approvers = {int(k): v for k, v in selected_approvers.items()}

        # Extract skipped steps from request data (optional)
        # Skipped steps are for approvers that are not available or not designated
        skipped_steps = request.data.get("skipped_steps", None)
        if skipped_steps:
            # Convert string keys to integers for consistency
            skipped_steps = {int(k): v for k, v in skipped_steps.items()}

        # Start workflow using WorkflowRouter
        try:
            workflow_instance = WorkflowRouter.start_workflow_for_request(
                entity=trf,
                entity_type=trf.workflow_entity_type,
                initiated_by=request.user,
                selected_approvers=selected_approvers,
                skipped_steps=skipped_steps,
                fallback_entity_type="travelrequest",
            )

            if workflow_instance:
                # Reload the TRF to get the updated status from workflow
                trf.refresh_from_db()
                logger.info(
                    f" Workflow started for TRF #{trf.id}: Workflow Instance #{workflow_instance.id}"
                )
                logger.info(f" Status updated to: {trf.status}")
            else:
                # Fallback to legacy approval system if no workflow configured
                logger.warning(
                    " No active workflow configured - creating legacy approval step"
                )
                TrfApprovalStep.objects.create(
                    trf=trf,
                    step_role="Department Focal",
                    step_name="Department Focal Review",
                    status="Pending",
                )
                trf.status = "Pending Department Focal"
                trf.save()
        except Exception as e:
            logger.error(f" Error starting workflow: {str(e)}")
            # Fallback to legacy system on error
            TrfApprovalStep.objects.create(
                trf=trf,
                step_role="Department Focal",
                step_name="Department Focal Review",
                status="Pending",
            )
            trf.status = "Pending Department Focal"
            trf.save()

        # Ensure we have the latest status before serializing
        trf.refresh_from_db()
        serializer = TravelRequestDetailSerializer(trf)
        return success_response(
            data=serializer.data,
            message="Travel request submitted successfully",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a TRF at current approval step using WorkflowEngine"""
        from django.contrib.contenttypes.models import ContentType
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance

        trf = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)

        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors, message="Invalid approval data"
            )

        step_role = serializer.validated_data["step_role"]
        comments = serializer.validated_data.get("comments", "")

        try:
            # Get the workflow instance for this TRF
            content_type = ContentType.objects.get_for_model(trf)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type, object_id=trf.id, status="in_progress"
            ).first()

            logger.debug(f" Approving TRF #{trf.id}")
            logger.debug(
                f" User: {request.user.email}, is_staff={request.user.is_staff}, is_superuser={request.user.is_superuser}"
            )
            logger.debug(f" Workflow instance found: {workflow_instance is not None}")

            if workflow_instance:
                # Find the current pending step (by order)
                # The WorkflowEngine will validate if the user is authorized
                current_step = (
                    workflow_instance.step_executions.filter(status="pending")
                    .order_by("workflow_step__step_order")
                    .first()
                )

                logger.debug(f" Pending step found: {current_step is not None}")
                if current_step:
                    logger.debug(
                        f" Step: {current_step.workflow_step.step_name}, assigned_to: {current_step.assigned_to}"
                    )

                if current_step:
                    # Use workflow engine to process approval
                    WorkflowEngine.process_action(
                        step_execution_id=current_step.id,
                        action="approve",
                        actioned_by=request.user,
                        comments=comments,
                    )

                    # Reload TRF to get updated status
                    trf.refresh_from_db()

                    # Also update legacy approval step for backward compatibility
                    approval_step, created = TrfApprovalStep.objects.get_or_create(
                        trf=trf,
                        step_role=step_role,
                        defaults={
                            "step_name": f"{step_role} Approval",
                            "status": "Pending",
                        },
                    )
                    approval_step.status = "Approved"
                    approval_step.comments = comments
                    approval_step.step_date = timezone.now()
                    approval_step.save()

                    trf_serializer = TravelRequestDetailSerializer(trf)
                    return success_response(
                        data=trf_serializer.data,
                        message="Travel request approved successfully",
                        status_code=status.HTTP_200_OK,
                    )
                else:
                    return error_response(
                        message="No pending approval step found for this role",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                # Fallback to legacy manual approval if no workflow found
                if not (request.user.is_superuser or can_approve(request.user, "trf")):
                    return forbidden_response(
                        message="You do not have permission to approve travel requests"
                    )

                logger.warning(
                    f" No workflow instance found for TRF #{trf.id}, using legacy approval"
                )

                # Find or create approval step for this role
                approval_step, created = TrfApprovalStep.objects.get_or_create(
                    trf=trf,
                    step_role=step_role,
                    defaults={
                        "step_name": f"{step_role} Approval",
                        "status": "Pending",
                    },
                )

                # Update approval step
                approval_step.status = "Approved"
                approval_step.comments = comments
                approval_step.step_date = datetime.now()
                approval_step.save()

                # Update TRF status based on approval workflow. Only real
                # roles that exist in this system's active workflow
                # templates (Department Focal, Line Manager, HOD) - "Travel
                # Desk" and "Finance" were never real roles here and never
                # matched any active TSR workflow step.
                status_progression = {
                    "Department Focal": "Pending HOD",
                    "Line Manager": "Pending HOD",
                    "HOD": "Approved",
                }

                if step_role in status_progression:
                    trf.status = status_progression[step_role]
                    trf.save()

                    # Create next approval step if not final
                    if trf.status != "Approved":
                        next_role = trf.status.replace("Pending ", "")
                        TrfApprovalStep.objects.get_or_create(
                            trf=trf,
                            step_role=next_role,
                            defaults={
                                "step_name": f"{next_role} Review",
                                "status": "Pending",
                            },
                        )

                AdminActionLog.log_action(
                    user=request.user,
                    action_type="workflow_step_approved",
                    description=(
                        f"Approved TRF #{trf.id} at step '{step_role}' "
                        "(legacy fallback - no active WorkflowTemplate)"
                    ),
                    entity_type="travelrequest",
                    entity_id=trf.id,
                    request=request,
                )

                trf_serializer = TravelRequestDetailSerializer(trf)
                return success_response(
                    data=trf_serializer.data,
                    message="Travel request approved successfully",
                    status_code=status.HTTP_200_OK,
                )

        except ValueError as e:
            # ValueError is raised by WorkflowEngine for authorization failures
            logger.error(f" ValueError in approve workflow: {str(e)}")
            return error_response(
                message=str(e), status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f" Error in approve workflow: {str(e)}")
            import traceback

            traceback.print_exc()
            return server_error_response(
                message="Failed to process approval", error_details=str(e)
            )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a TRF using WorkflowEngine"""
        from django.contrib.contenttypes.models import ContentType
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance

        trf = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)

        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors, message="Invalid rejection data"
            )

        step_role = serializer.validated_data["step_role"]
        comments = serializer.validated_data.get("comments", "")

        try:
            # Get the workflow instance for this TRF
            content_type = ContentType.objects.get_for_model(trf)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type, object_id=trf.id, status="in_progress"
            ).first()

            if workflow_instance:
                # Find the current step execution for the given role
                current_step = (
                    workflow_instance.step_executions.filter(status="pending")
                    .order_by("workflow_step__step_order")
                    .first()
                )

                if current_step:
                    # Use workflow engine to process rejection
                    WorkflowEngine.process_action(
                        step_execution_id=current_step.id,
                        action="reject",
                        actioned_by=request.user,
                        comments=comments,
                    )

                    # Reload TRF to get updated status
                    trf.refresh_from_db()

                    # Also update legacy approval step for backward compatibility
                    approval_step, created = TrfApprovalStep.objects.get_or_create(
                        trf=trf,
                        step_role=step_role,
                        defaults={
                            "step_name": f"{step_role} Approval",
                            "status": "Pending",
                        },
                    )
                    approval_step.status = "Rejected"
                    approval_step.comments = comments
                    approval_step.step_date = datetime.now()
                    approval_step.save()

                    trf_serializer = TravelRequestDetailSerializer(trf)
                    return success_response(
                        data=trf_serializer.data,
                        message="Travel request rejected successfully",
                        status_code=status.HTTP_200_OK,
                    )
                else:
                    return error_response(
                        message="No pending approval step found",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                # Fallback to legacy manual rejection if no workflow found
                if not (request.user.is_superuser or can_approve(request.user, "trf")):
                    return forbidden_response(
                        message="You do not have permission to reject travel requests"
                    )

                logger.warning(
                    f" No workflow instance found for TRF #{trf.id}, using legacy rejection"
                )

                # Find or create approval step for this role
                approval_step, created = TrfApprovalStep.objects.get_or_create(
                    trf=trf,
                    step_role=step_role,
                    defaults={
                        "step_name": f"{step_role} Approval",
                        "status": "Pending",
                    },
                )

                # Update approval step
                approval_step.status = "Rejected"
                approval_step.comments = comments
                approval_step.step_date = datetime.now()
                approval_step.save()

                # Update TRF status
                trf.status = "Rejected"
                trf.save()

                AdminActionLog.log_action(
                    user=request.user,
                    action_type="workflow_step_rejected",
                    description=(
                        f"Rejected TRF #{trf.id} at step '{step_role}' "
                        "(legacy fallback - no active WorkflowTemplate)"
                    ),
                    entity_type="travelrequest",
                    entity_id=trf.id,
                    request=request,
                )

                trf_serializer = TravelRequestDetailSerializer(trf)
                return success_response(
                    data=trf_serializer.data,
                    message="Travel request rejected successfully",
                    status_code=status.HTTP_200_OK,
                )

        except Exception as e:
            logger.error(f" Error in reject workflow: {str(e)}")
            import traceback

            traceback.print_exc()
            return server_error_response(
                message="Failed to process rejection", error_details=str(e)
            )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a TRF"""
        trf = self.get_object()

        if trf.status in ["Approved", "Completed"]:
            return error_response(
                message="Approved or completed TRFs cannot be cancelled",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        trf.status = "Cancelled"
        trf.save()

        serializer = self.get_serializer(trf)
        return success_response(
            data=serializer.data,
            message="Travel request cancelled successfully",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="check-accommodation-availability")
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
        itinerary_segments = (
            TrfItinerarySegment.objects.filter(trf=trf)
            .exclude(segment_date__isnull=True)
            .order_by("segment_date")
        )

        date_range = None
        if itinerary_segments.exists():
            first_segment = itinerary_segments.first()
            last_segment = itinerary_segments.last()
            date_range = {
                "start_date": first_segment.segment_date.strftime("%Y-%m-%d"),
                "end_date": last_segment.segment_date.strftime("%Y-%m-%d"),
            }

        response_data = {
            "is_available": existing_accommodation is None,
            "date_range": date_range,
            "tsr_id": trf.id,
            "tsr_request_number": trf.request_number,
        }

        if existing_accommodation:
            response_data["existing_accommodation"] = {
                "id": existing_accommodation.id,
                "request_number": existing_accommodation.request_number,
                "status": existing_accommodation.status,
                "requestor_name": existing_accommodation.requestor_name,
            }

        return success_response(
            data=response_data,
            message="Accommodation availability checked",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"], url_path="delete-itinerary")
    def delete_itinerary(self, request, pk=None):
        """Delete all itinerary segments for a TRF"""
        trf = self.get_object()
        count = TrfItinerarySegment.objects.filter(trf=trf).delete()[0]
        return success_response(
            data={"deleted": count},
            message=f"Deleted {count} itinerary segment(s)",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"], url_path="delete-meals")
    def delete_meals(self, request, pk=None):
        """Delete all meal selections for a TRF"""
        trf = self.get_object()
        count = TrfDailyMealSelection.objects.filter(trf=trf).delete()[0]
        return success_response(
            data={"deleted": count},
            message=f"Deleted {count} meal selection(s)",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="meal-status")
    def update_meal_status(self, request, pk=None):
        """Meal Admin: update the fulfillment status of a TRF's requested meals"""
        user = request.user
        if not (user.is_superuser or can_manage(user, "meal")):
            return forbidden_response(
                message="You do not have permission to process meal requests."
            )

        new_status = request.data.get("meal_processing_status")
        valid_statuses = dict(TravelRequest.MEAL_PROCESSING_STATUS_CHOICES)
        if new_status not in valid_statuses:
            return validation_error_response(
                {
                    "meal_processing_status": [
                        f"Must be one of: {', '.join(valid_statuses.keys())}"
                    ]
                }
            )

        trf = self.get_object()
        trf.meal_processing_status = new_status
        trf.save(update_fields=["meal_processing_status"])

        serializer = self.get_serializer(trf)
        return success_response(
            data=serializer.data,
            message=f"Meal status updated to {new_status}",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"], url_path="delete-passport")
    def delete_passport(self, request, pk=None):
        """Delete all passport details for a TRF"""
        trf = self.get_object()
        count = TrfPassportDetail.objects.filter(trf=trf).delete()[0]
        return success_response(
            data={"deleted": count},
            message=f"Deleted {count} passport detail(s)",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"], url_path="delete-bank")
    def delete_bank(self, request, pk=None):
        """Delete bank details for a TRF"""
        trf = self.get_object()
        count = TrfAdvanceBankDetail.objects.filter(trf=trf).delete()[0]
        return success_response(
            data={"deleted": count},
            message=f"Deleted {count} bank detail(s)",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"], url_path="delete-advance-amounts")
    def delete_advance_amounts(self, request, pk=None):
        """Delete all advance amount items for a TRF"""
        trf = self.get_object()
        count = TrfAdvanceAmountRequestedItem.objects.filter(trf=trf).delete()[0]
        return success_response(
            data={"deleted": count},
            message=f"Deleted {count} advance amount(s)",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="pending-approvals")
    def pending_approvals(self, request):
        """Get TRFs pending approval for the current user based on workflow step assignments"""
        from accounts.utils import is_module_admin
        from workflows.services import WorkflowApprovalHelper

        user = request.user

        # Admins and superusers see all pending requests
        # Use startswith to match any workflow-generated 'Pending *' status
        if user.is_superuser or is_module_admin(user, "trf"):
            queryset = TravelRequest.objects.filter(
                Q(status__startswith="Pending")
                | Q(status="Submitted")
                | Q(status="Under Review")
            ).order_by("-submitted_at")
        else:
            # Use workflow-based filtering: get entities where user's role matches current step
            pending_ids = WorkflowApprovalHelper.get_pending_entity_ids_for_user(
                user, TravelRequest
            )
            queryset = TravelRequest.objects.filter(id__in=pending_ids).order_by(
                "-submitted_at"
            )

        # Use detail serializer to include nested data (itinerary, accommodation, etc.)
        serializer = TravelRequestDetailSerializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message=f"Retrieved {queryset.count()} pending approval(s)",
            status_code=status.HTTP_200_OK,
        )

    @staticmethod
    def _parse_flight_datetime(value):
        """Parse an ISO datetime string into an aware datetime, or None."""
        from datetime import datetime

        if not value:
            return None
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = timezone.make_aware(parsed)
        return parsed

    @classmethod
    def _parse_flight_segments(cls, raw_segments):
        """
        Parse the `segments` JSON payload for book_flight into
        (outbound, return) lists, each a list of dicts with a parsed
        `departure_time`/`arrival_time`. Raises ValueError with a
        user-facing message on any structural or field problem.
        """
        import json

        try:
            segments = json.loads(raw_segments) if raw_segments else []
        except (TypeError, ValueError):
            raise ValueError("segments must be valid JSON")
        if not isinstance(segments, list) or not segments:
            raise ValueError("At least one outbound flight segment is required")

        required_fields = [
            "direction",
            "flightNumber",
            "departureAirport",
            "arrivalAirport",
            "departureDateTime",
            "arrivalDateTime",
        ]
        outbound, return_legs = [], []
        for index, seg in enumerate(segments, start=1):
            missing = [f for f in required_fields if not seg.get(f)]
            if missing:
                raise ValueError(f"Segment {index} is missing: {', '.join(missing)}")
            if seg["direction"] not in ("OUTBOUND", "RETURN"):
                raise ValueError(f"Segment {index} has an invalid direction")
            parsed = {
                "flight_number": seg["flightNumber"],
                "departure_airport": seg["departureAirport"],
                "arrival_airport": seg["arrivalAirport"],
                "departure_time": cls._parse_flight_datetime(seg["departureDateTime"]),
                "arrival_time": cls._parse_flight_datetime(seg["arrivalDateTime"]),
            }
            (outbound if seg["direction"] == "OUTBOUND" else return_legs).append(parsed)

        if not outbound:
            raise ValueError("At least one outbound flight segment is required")
        return outbound, return_legs

    @staticmethod
    def _save_flight_segments(flight_booking, outbound, return_legs):
        """Replace a booking's segment rows with the freshly parsed legs."""
        from bookings.models import FlightBookingSegment, SegmentDirection

        flight_booking.segments.all().delete()
        rows = [
            FlightBookingSegment(
                booking=flight_booking,
                direction=SegmentDirection.OUTBOUND,
                sequence=sequence,
                **leg,
            )
            for sequence, leg in enumerate(outbound, start=1)
        ] + [
            FlightBookingSegment(
                booking=flight_booking,
                direction=SegmentDirection.RETURN,
                sequence=sequence,
                **leg,
            )
            for sequence, leg in enumerate(return_legs, start=1)
        ]
        FlightBookingSegment.objects.bulk_create(rows)

    def _validate_book_flight_fields(
        self, trf, pnr, airline, e_ticket, existing_booking
    ):
        """Return a list of missing required field names (empty if valid)."""
        required = {"pnr": pnr}
        if trf.travel_type == "Overseas":
            required["airline"] = airline
        missing = [name for name, value in required.items() if not value]
        # E-ticket is required the first time a booking is created; an
        # existing booking already has one on file, so re-uploading isn't
        # forced on every edit.
        if not e_ticket and not (existing_booking and existing_booking.e_ticket):
            missing.append("eTicket")
        return missing

    @action(detail=True, methods=["post"], url_path="admin/book-flight")
    def book_flight(self, request, pk=None):
        """
        Book a flight for an approved TRF. Creates or updates the TRF's
        FlightBooking (summary record) plus its FlightBookingSegment rows -
        one per leg, supporting itineraries with connections on either the
        outbound or return direction, not just a single outbound/return pair.

        Expected payload (multipart/form-data, since eTicket is a file):
        {
            "pnr": "ABC123",
            "airline": "MH",              # required only for Overseas travel
            "segments": "[{\"direction\":\"OUTBOUND\",\"flightNumber\":\"MH123\",
                            \"departureAirport\":\"KUL\",\"arrivalAirport\":\"LHR\",
                            \"departureDateTime\":\"2025-12-01T10:00:00\",
                            \"arrivalDateTime\":\"2025-12-01T18:00:00\"}, ...]",
            "eTicket": <file>,             # required on first booking
            "flightNotes": "Optional notes"
        }
        """
        from bookings.models import FlightBooking, FlightType

        trf = self.get_object()

        if trf.status not in BOOKABLE_STATUSES:
            error_msg = f"Flights can only be booked for approved TRFs. Current status: {trf.status}"
            logger.error(f" Status validation failed: {error_msg}")
            return error_response(
                message=error_msg, status_code=status.HTTP_400_BAD_REQUEST
            )

        pnr = request.data.get("pnr", "")
        airline = request.data.get("airline", "")
        e_ticket = request.FILES.get("eTicket")
        flight_notes = request.data.get("flightNotes", "")

        existing_booking = FlightBooking.objects.filter(trf=trf).first()

        missing = self._validate_book_flight_fields(
            trf, pnr, airline, e_ticket, existing_booking
        )
        if missing:
            error_msg = f'Missing required fields: {", ".join(missing)}'
            logger.error(f" Field validation failed: {error_msg}")
            return error_response(
                message=error_msg,
                errors={"missing_fields": missing},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            outbound, return_legs = self._parse_flight_segments(
                request.data.get("segments")
            )
        except ValueError as e:
            logger.error(f" Segment validation failed: {e}")
            return error_response(
                message=str(e), status_code=status.HTTP_400_BAD_REQUEST
            )

        flight_type = FlightType.ROUND_TRIP if return_legs else FlightType.ONE_WAY
        summary = {
            "airline": airline or None,
            "flight_number": outbound[0]["flight_number"],
            "departure_airport": outbound[0]["departure_airport"],
            "arrival_airport": outbound[-1]["arrival_airport"],
            "departure_time": outbound[0]["departure_time"],
            "arrival_time": outbound[-1]["arrival_time"],
            "return_flight_number": (
                return_legs[0]["flight_number"] if return_legs else None
            ),
            "return_departure_time": (
                return_legs[0]["departure_time"] if return_legs else None
            ),
            "return_arrival_time": (
                return_legs[-1]["arrival_time"] if return_legs else None
            ),
            "flight_type": flight_type,
        }

        if existing_booking:
            for field, value in summary.items():
                setattr(existing_booking, field, value)
            if e_ticket:
                existing_booking.e_ticket = e_ticket
            existing_booking.booking_reference = pnr
            existing_booking.status = "CONFIRMED"
            existing_booking.booked_by = request.user
            existing_booking.confirmation_date = timezone.now()
            existing_booking.notes = flight_notes
            existing_booking.save()
            flight_booking = existing_booking
            logger.info(
                f" Updated existing flight booking {flight_booking.id} for TRF {trf.id}"
            )
        else:
            flight_booking = FlightBooking.objects.create(
                trf=trf,
                user=trf.created_by if trf.created_by else request.user,
                e_ticket=e_ticket,
                booking_reference=pnr,
                status="CONFIRMED",
                booked_by=request.user,
                booking_date=timezone.now(),
                confirmation_date=timezone.now(),
                notes=flight_notes,
                **summary,
            )
            logger.info(
                f" Created new flight booking {flight_booking.id} for TRF {trf.id}"
            )

        self._save_flight_segments(flight_booking, outbound, return_legs)

        trf.status = "Flight Booked"
        trf.save()

        serializer = TravelRequestDetailSerializer(trf)
        return created_response(
            data={
                "trf": serializer.data,
                "flight_booking": {
                    "id": flight_booking.id,
                    "booking_reference": flight_booking.booking_reference,
                    "status": flight_booking.status,
                },
            },
            message="Flight booking created successfully",
        )

    @action(detail=True, methods=["post"], url_path="export-pdf")
    def export_pdf(self, request, pk=None):
        """
        Dispatch an async PDF export task and return the Celery task ID.

        The client should poll GET /api/tasks/{task_id}/ until status is
        SUCCESS, then call GET /api/trf/travel-requests/{pk}/download-pdf/
        with ?task_id={task_id} to receive the PDF blob.
        """
        try:
            trf = TravelRequest.objects.get(pk=pk)
        except TravelRequest.DoesNotExist:
            return not_found_response(message="Travel Request not found")

        from trf.tasks import export_trf_pdf

        task = export_trf_pdf.apply_async(args=[trf.id], queue="pdfs")
        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["get"], url_path="download-pdf")
    def download_pdf(self, request, pk=None):
        """
        Stream a previously generated PDF from the Redis cache.

        Requires ?task_id=<celery-task-id> query parameter (returned by the
        POST /export-pdf/ action). Returns 404 if the PDF has expired or the
        task_id is unknown.
        """
        from django.core.cache import cache
        from django.http import HttpResponse

        task_id = request.query_params.get("task_id")
        if not task_id:
            return validation_error_response(
                errors={"task_id": ["This query parameter is required."]},
                message="task_id query parameter is required",
            )

        pdf_bytes = cache.get(f"pdf:{task_id}")
        if pdf_bytes is None:
            return not_found_response(
                message="PDF not found or has expired — please export again."
            )

        try:
            trf = TravelRequest.objects.get(pk=pk)
        except TravelRequest.DoesNotExist:
            return not_found_response(message="Travel Request not found")

        filename = f"TSR-{trf.request_number or trf.id}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


# =============== NESTED RESOURCE VIEWSETS ===============


class TrfAdvanceAmountRequestedItemViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Advance Amount Requested Items"""

    queryset = TrfAdvanceAmountRequestedItem.objects.all()
    serializer_class = TrfAdvanceAmountRequestedItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get("trf", None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by("-created_at")


class TrfAdvanceBankDetailViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Advance Bank Details"""

    queryset = TrfAdvanceBankDetail.objects.all()
    serializer_class = TrfAdvanceBankDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get("trf", None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by("-created_at")


class TrfApprovalStepViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Approval Steps"""

    queryset = TrfApprovalStep.objects.all()
    serializer_class = TrfApprovalStepSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get("trf", None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by("-created_at")


class TrfDailyMealSelectionViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Daily Meal Selections"""

    queryset = TrfDailyMealSelection.objects.all()
    serializer_class = TrfDailyMealSelectionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        logger.debug("\n=== TrfDailyMealSelection CREATE ===")
        logger.debug(f"Request data: {request.data}")
        logger.debug(f"TRF field value: {request.data.get('trf')}")
        logger.debug(f"Meal date value: {request.data.get('meal_date')}")
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        trf_id = self.request.query_params.get("trf", None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by("meal_date")


class TrfItinerarySegmentViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Itinerary Segments"""

    queryset = TrfItinerarySegment.objects.all()
    serializer_class = TrfItinerarySegmentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        logger.debug("\n=== TrfItinerarySegment CREATE ===")
        logger.debug(f"Request data: {request.data}")
        logger.debug(f"TRF field value: {request.data.get('trf')}")
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        trf_id = self.request.query_params.get("trf", None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by("segment_date")


class TrfMealProvisionViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Meal Provisions"""

    queryset = TrfMealProvision.objects.all()
    serializer_class = TrfMealProvisionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get("trf", None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by("-created_at")


class TrfPassportDetailViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Passport Details with file upload support"""

    queryset = TrfPassportDetail.objects.all()
    serializer_class = TrfPassportDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        """Include request in serializer context for building absolute URLs"""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def get_queryset(self):
        trf_id = self.request.query_params.get("trf", None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by("-created_at")

    @action(detail=True, methods=["post"], url_path="upload-passport")
    def upload_passport(self, request, pk=None):
        """
        Upload or update passport file for an existing passport detail record.
        Accepts multipart/form-data with 'passport_file' field.
        """
        passport_detail = self.get_object()

        if "passport_file" not in request.FILES:
            return error_response(
                message="No passport file provided",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        passport_file = request.FILES["passport_file"]

        # Validate file type
        allowed_types = ["application/pdf", "image/jpeg", "image/jpg", "image/png"]
        if passport_file.content_type not in allowed_types:
            return error_response(
                message="Passport file must be PDF, JPG, or PNG format",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024
        if passport_file.size > max_size:
            return error_response(
                message="Passport file size must not exceed 10MB",
                status_code=status.HTTP_400_BAD_REQUEST,
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
            message="Passport file uploaded successfully",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"], url_path="delete-passport-file")
    def delete_passport_file(self, request, pk=None):
        """Delete the passport file from an existing passport detail record."""
        passport_detail = self.get_object()

        if not passport_detail.passport_file:
            return error_response(
                message="No passport file to delete",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Delete the file
        passport_detail.passport_file.delete(save=True)

        serializer = self.get_serializer(passport_detail)
        return success_response(
            data=serializer.data,
            message="Passport file deleted successfully",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="upload-for-trf")
    def upload_for_trf(self, request):
        """
        Upload passport file for a TRF. Creates passport detail if it doesn't exist.
        Expects: trf (TRF ID) and passport_file in multipart/form-data
        """
        trf_id = request.data.get("trf")
        if not trf_id:
            return error_response(
                message="TRF ID is required", status_code=status.HTTP_400_BAD_REQUEST
            )

        if "passport_file" not in request.FILES:
            return error_response(
                message="No passport file provided",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        passport_file = request.FILES["passport_file"]

        # Validate file type
        allowed_types = ["application/pdf", "image/jpeg", "image/jpg", "image/png"]
        if passport_file.content_type not in allowed_types:
            return error_response(
                message="Passport file must be PDF, JPG, or PNG format",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024
        if passport_file.size > max_size:
            return error_response(
                message="Passport file size must not exceed 10MB",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Verify TRF exists
        try:
            trf = TravelRequest.objects.get(pk=trf_id)
        except TravelRequest.DoesNotExist:
            return not_found_response(message="TRF not found")

        # Get or create passport detail for this TRF
        passport_detail, created = TrfPassportDetail.objects.get_or_create(
            trf=trf, defaults={}
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
            message="Passport file uploaded successfully",
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
