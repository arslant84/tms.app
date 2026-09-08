"""
TravelRequestViewSet - the TRF module's dominant class.

Split out of trf/views.py (see docs/CODEBASE_REFACTOR_ROADMAP.md item 9)
- a pure file move for get_queryset/CRUD/small actions, with the
request-number/workflow-start duplication and approve/reject dispatch
collapsed into trf/services.py, and book_flight's helper methods moved to
trf/flight_booking.py (already well-factored internally, so this is a
mechanical move). Nested sub-resource ViewSets moved to their own sibling
module (trf_nested_views.py) in the same split.
"""

import logging
from datetime import datetime

from accounts.models import AdminActionLog
from accounts.utils import can_manage, can_view_all, has_permission
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from utils.api_response import (
    created_response,
    error_response,
    forbidden_response,
    not_found_response,
    success_response,
    validation_error_response,
)
from utils.constants import BOOKABLE_STATUSES
from utils.viewset_mixins import StandardResultsPagination

from . import flight_booking
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
)
from .services import process_trf_approval_action, start_trf_workflow

logger = logging.getLogger(__name__)


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
            try:
                start_trf_workflow(trf, self.request.data, user)
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
            # Removed: a substring match on the role's display *name*
            # (any role containing "ticket"/"travel desk"/"booking"/"admin")
            # used to grant booking access here too - not a real permission
            # check, so any role later named to include "admin" (e.g.
            # "Transport Admin", "Accommodation Admin", "Meal Admin" - none
            # of which are ticketing/booking-related) got book_flight access
            # by accident. Confirmed via a role-data audit (2026-09-07) that
            # the 3 roles relying on this had zero flight bookings ever
            # created by their users - dead capability, not a relied-upon
            # one. See docs/RBAC_AND_ADMIN_ACCESS_FIX_ROADMAP.md Fix 4.
            # Superuser/view_all_trf admins still reach book_flight via the
            # general admin bypass below (Fix 2); anyone who legitimately
            # needs booking access gets the real manage_bookings permission.

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

        # Department Focal queue: read-only visibility into their own
        # department's requests and every arrangement module they needed
        # (flight/meal/transport/accommodation/visa) — full status per
        # module, not just an all-or-nothing gate, so the Focal can see
        # what's still pending as well as what's done. Pass ?ready=true to
        # narrow to only fully-arranged requests (used by the notification
        # helper's definition of "done"; the queue itself defaults to
        # showing everything).
        department_focal_queue = (
            self.request.query_params.get("department_focal_queue", "false").lower()
            == "true"
        )
        if department_focal_queue:
            if not (
                user.is_superuser or has_permission(user, "view_admin_department_focal")
            ):
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied(
                    "You do not have permission to view the Department Focal queue."
                )
            own_department = (
                (user.department.name if user.department else "").strip().lower()
            )
            candidates = (
                queryset.filter(department__iexact=own_department)
                .exclude(status="Draft")
                .order_by("-created_at")
                if own_department
                else queryset.none()
            )
            ready_only = (
                self.request.query_params.get("ready", "false").lower() == "true"
            )
            if not ready_only:
                return candidates
            ready_ids = [t.id for t in candidates if t.is_fully_arranged]
            return TravelRequest.objects.filter(id__in=ready_ids).order_by(
                "-created_at"
            )

        # For retrieve (viewing details) and PDF export/download, check
        # view_all permission first, then pending approvals. export_pdf/
        # download_pdf previously bypassed get_queryset() entirely (fetched
        # via TravelRequest.objects.get(pk=pk) directly) - any authenticated
        # user could export/download any other user's TRF PDF. They now go
        # through self.get_object() like retrieve, so they need the same
        # bypass here.
        if self.action in ("retrieve", "export_pdf", "download_pdf"):
            # Users with view_all_trf permission can access any TRF detail (e.g. from Recent Activity)
            if user.is_superuser or can_view_all(user, "trf"):
                logger.info(
                    f" {self.action} action: User has view_all_trf - allowing full access"
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
                f" {self.action} action: Filtering to own TRFs and {len(pending_approval_ids)} pending approval"
            )
            return queryset

        # Write/delete/cancel actions and book_flight: give admins
        # (is_superuser or view_all_trf) the same full-access bypass as
        # retrieve, so an admin acting on a TRF they didn't create doesn't
        # get a false 404 (the same bug shape already fixed on
        # transport/visa - see docs/RBAC_AND_ADMIN_ACCESS_FIX_ROADMAP.md
        # Fix 2). Deliberately NOT extended to the pending-approval fallback
        # that retrieve/export_pdf/download_pdf get above: none of these
        # actions have their own internal permission check beyond
        # get_object() (confirmed by reading each one), so a user with only
        # a pending *approval* step on this TRF should not gain the ability
        # to edit/delete/cancel/book-flight-for it - reviewing a request
        # isn't the same as being allowed to modify it. Non-admins continue
        # to fall through to the existing owner-only filtering below
        # unchanged (admin_view only ever applies to the list endpoint, so
        # these detail actions land on the final `else` either way).
        if self.action in (
            "update",
            "partial_update",
            "destroy",
            "cancel",
            "delete_itinerary",
            "delete_meals",
            "delete_passport",
            "delete_bank",
            "delete_advance_amounts",
            "book_flight",
        ):
            if user.is_superuser or can_view_all(user, "trf"):
                logger.info(
                    f" {self.action} action: User has view_all_trf - allowing admin access"
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
                from trf.services import generate_unique_tsr_request_number

                request_number = generate_unique_tsr_request_number(trf)
                trf.request_number = request_number
                logger.info(f" Generated request number: {request_number}")
            except Exception as e:
                logger.error(f" Error generating request number: {str(e)}")
                import traceback

                traceback.print_exc()
                # Fallback to simple format
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
        # guard in WorkflowRouter/WorkflowEngine below now merges any
        # newly-submitted selected_approvers/skipped_steps into the existing
        # instance (for not-yet-approved steps only - see
        # WorkflowEngine._apply_resubmit_selection), but it still doesn't
        # change workflow_instance.current_step_order or the entity status
        # by itself. Resync status to the real current step here regardless.
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

        # Start workflow using WorkflowRouter
        try:
            workflow_instance = start_trf_workflow(trf, request.data, request.user)

            if not workflow_instance:
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
        trf = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)

        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors, message="Invalid approval data"
            )

        step_role = serializer.validated_data["step_role"]
        comments = serializer.validated_data.get("comments", "")

        logger.debug(f" Approving TRF #{trf.id}")
        logger.debug(
            f" User: {request.user.email}, is_staff={request.user.is_staff}, is_superuser={request.user.is_superuser}"
        )

        return process_trf_approval_action(trf, request, "approve", step_role, comments)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a TRF using WorkflowEngine"""
        trf = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)

        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors, message="Invalid rejection data"
            )

        step_role = serializer.validated_data["step_role"]
        comments = serializer.validated_data.get("comments", "")

        return process_trf_approval_action(trf, request, "reject", step_role, comments)

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

        from trf.services import notify_department_focal_if_ready

        notify_department_focal_if_ready(trf)

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

        missing = flight_booking.validate_book_flight_fields(
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
            outbound, return_legs = flight_booking.parse_flight_segments(
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
            flight_booking_obj = existing_booking
            logger.info(
                f" Updated existing flight booking {flight_booking_obj.id} for TRF {trf.id}"
            )
        else:
            flight_booking_obj = FlightBooking.objects.create(
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
                f" Created new flight booking {flight_booking_obj.id} for TRF {trf.id}"
            )

        flight_booking.save_flight_segments(flight_booking_obj, outbound, return_legs)

        trf.status = "Flight Booked"
        trf.save()

        serializer = TravelRequestDetailSerializer(trf)
        return created_response(
            data={
                "trf": serializer.data,
                "flight_booking": {
                    "id": flight_booking_obj.id,
                    "booking_reference": flight_booking_obj.booking_reference,
                    "status": flight_booking_obj.status,
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
        # self.get_object() goes through get_queryset()'s ownership/
        # view_all_trf/pending-approval filtering (see the "retrieve" branch
        # above, which this action now shares) - previously this fetched the
        # TRF directly, bypassing all authorization.
        trf = self.get_object()

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

        # Authorization first (see get_queryset()'s "retrieve" branch, shared
        # by this action) - before touching the cache, so an unauthorized
        # request for this pk is rejected regardless of whether task_id is
        # valid.
        trf = self.get_object()

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

        filename = f"TSR-{trf.request_number or trf.id}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
