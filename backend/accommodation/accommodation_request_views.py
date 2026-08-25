"""
AccommodationRequestViewSet - the accommodation module's dominant class.

Split out of accommodation/views.py (see
docs/CODEBASE_REFACTOR_ROADMAP.md item 6) - a pure file move, no logic
changed. Staff-house/room/booking viewsets moved to their own sibling
modules in the same split.
"""

import logging

from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)
from accounts.models import AdminActionLog
from accounts.utils import has_permission

from .models import AccommodationRequest
from .serializers import AccommodationRequestSerializer
from .services import (
    assign_accommodation,
    generate_accommodation_request_number,
    generate_accommodation_request_number_with_fallback,
    process_accommodation_approval_action,
    start_accommodation_workflow,
)


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
    pagination_class = PageNumberPagination

    # Search across key fields
    search_fields = ["requestor_name", "staff_id", "department", "request_number"]

    # Allow ordering
    ordering_fields = ["created_at", "submitted_at", "status"]
    ordering = ["-created_at"]  # Default: newest first

    def get_object(self):
        """
        Override to show proper request_number in error messages
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field or "pk"
        lookup_value = self.kwargs[lookup_url_kwarg]

        # Try to determine if it's a numeric ID or request_number
        if lookup_value.isdigit():
            filter_kwargs = {"pk": int(lookup_value)}
        else:
            filter_kwargs = {"request_number": lookup_value}

        queryset = self.filter_queryset(self.get_queryset())

        try:
            obj = queryset.get(**filter_kwargs)
        except AccommodationRequest.DoesNotExist:
            from rest_framework.exceptions import NotFound

            # Try to fetch from full queryset to get request_number for better error message
            try:
                obj = AccommodationRequest.objects.get(**filter_kwargs)
                request_identifier = obj.request_number or f"ID #{obj.id}"
                raise NotFound(
                    f"Accommodation request {request_identifier} not found or you do not have permission to access it"
                )
            except AccommodationRequest.DoesNotExist:
                raise NotFound(
                    f"Accommodation request not found with identifier: {lookup_value}"
                )

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def get_serializer_class(self):
        """Use detailed serializer for retrieve action"""
        if self.action == "retrieve":
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
        if self.action == "retrieve":
            queryset = queryset.prefetch_related(
                "bookings",
                "bookings__staff_house",
                "bookings__room",
                "trf__trfitinerarysegment_set",  # Prefetch TRF itinerary segments for TSR dates
            )

        # Optimize for list view - prefetch TRF itinerary segments for TSR dates
        if self.action == "list":
            queryset = queryset.prefetch_related("trf__trfitinerarysegment_set")

        # For approval actions, allow access to requests pending the user's approval
        if self.action in ["approve", "reject"]:
            logger.info(
                " Approval action: Allowing access to all accommodation requests (authorization checked in WorkflowEngine)"
            )
            return queryset  # No filtering - authorization handled by WorkflowEngine

        # For retrieve action, check permissions and workflow assignment
        if self.action == "retrieve":
            from workflows.services import WorkflowApprovalHelper

            # Check if user has admin permissions to view all
            can_view_all = (
                user.role.permissions.filter(
                    name__in=[
                        "view_all_accommodation",
                        "approve_accommodation",
                        "process_accommodation",
                    ]
                ).exists()
                if user.role
                else False
            )

            if user.is_superuser or can_view_all:
                logger.info(
                    f" Retrieve action: User {user.email or user.username} has admin permissions - allowing access to all requests"
                )
                return queryset  # No filtering for admins

            # Include requests pending user's approval via workflow
            pending_approval_ids = (
                WorkflowApprovalHelper.get_pending_entity_ids_for_user(
                    user, AccommodationRequest
                )
            )
            if pending_approval_ids:
                queryset = queryset.filter(
                    Q(requestor_name=user.get_full_name())
                    | Q(staff_id=user.staff_id)
                    | Q(id__in=pending_approval_ids)
                )
                logger.info(
                    f" Retrieve action: User {user.email or user.username} - showing own requests plus {len(pending_approval_ids)} pending approval"
                )
            else:
                # Regular users can view their own requests only
                logger.info(
                    f" Retrieve action: User {user.email or user.username} - filtering by requestor"
                )
                # Filter by requestor_name or staff_id to handle different data entry methods
                queryset = queryset.filter(
                    Q(requestor_name=user.get_full_name()) | Q(staff_id=user.staff_id)
                )
            return queryset

        # For assign action, check if user has admin permissions
        if self.action == "assign" and (user.is_superuser or user.role):
            can_view_all = (
                user.role.permissions.filter(
                    name__in=[
                        "view_all_accommodation",
                        "approve_accommodation",
                        "process_accommodation",
                    ]
                ).exists()
                if user.role
                else False
            )

            if user.is_superuser or can_view_all:
                logger.info(
                    f" Assign action: User {user.email or user.username} has admin permissions - allowing access to all requests"
                )
                return queryset  # No filtering for admins

        # Check if this is an admin view (Accommodation Admin module)
        admin_view = (
            self.request.query_params.get("admin_view", "false").lower() == "true"
        )

        # Permission-based filtering
        if admin_view and (user.is_superuser or user.role):
            # Admin module context - check permissions
            can_view_all = (
                user.role.permissions.filter(name="view_all_accommodation").exists()
                if user.role
                else False
            )

            if user.is_superuser or can_view_all:
                logger.info(
                    f" Admin view: User {user.email or user.username} (role: {user.role.name if user.role else None}) has 'view_all_accommodation' permission - showing all accommodation requests"
                )
                pass  # No filtering - show all
            elif user.role.permissions.filter(
                name__in=["approve_accommodation", "view_pending_approvals"]
            ).exists():
                # Department-level approvers - could be extended to filter by department if needed
                queryset = queryset.filter(requestor_name=user.get_full_name())
                logger.info(
                    " Admin view: Approver - showing own accommodation requests"
                )
            else:
                # No admin permissions - show only own
                queryset = queryset.filter(requestor_name=user.get_full_name())
                logger.warning(
                    " Admin view: User lacks permission - showing only own accommodation requests"
                )
        else:
            # Personal requests view - always show only user's own requests
            queryset = queryset.filter(requestor_name=user.get_full_name())
            logger.info(
                f" Personal view: User {user.email or user.username} - showing only own accommodation requests"
            )

        # Apply additional filters from query parameters
        status_filter = self.request.query_params.get("status", None)
        department = self.request.query_params.get("department", None)
        requestor_name = self.request.query_params.get("requestor_name", None)

        if status_filter:
            # Use startswith to match workflow statuses like "Pending Line Manager"
            # when filter is "Pending"
            queryset = queryset.filter(status__istartswith=status_filter)

        if department:
            queryset = queryset.filter(department__icontains=department)

        if requestor_name:
            queryset = queryset.filter(requestor_name__icontains=requestor_name)

        # Apply search filter
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                Q(requestor_name__icontains=search)
                | Q(staff_id__icontains=search)
                | Q(request_number__icontains=search)
                | Q(department__icontains=search)
                | Q(email__icontains=search)
            )
            logger.debug(f"Searching accommodation for: {search}")

        return queryset.order_by("-created_at")

    def create(self, request, *args, **kwargs):
        """Create a new accommodation request"""
        if not request.user.is_superuser and not has_permission(
            request.user, "create_accommodation"
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "You do not have permission to create accommodation requests."
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Create accommodation request and optionally start workflow if submitted"""
        # Get status from request data, default to 'Draft' if not provided
        status_value = serializer.validated_data.get("status", "Draft")

        # Set submitted_at timestamp if status is being submitted (not Draft)
        extra_kwargs = {}
        if status_value in ["Pending", "Submitted"]:
            extra_kwargs["submitted_at"] = timezone.now()

            # Generate request number if submitting directly (not Draft)
            if not serializer.validated_data.get("request_number"):
                request_number = generate_accommodation_request_number(
                    serializer.validated_data.get("additional_data", {})
                )
                if request_number:
                    extra_kwargs["request_number"] = request_number

        # Save the accommodation request
        accommodation_request = serializer.save(**extra_kwargs)

        # Start workflow if status is submitted (not Draft)
        if status_value in ["Pending", "Submitted"]:
            start_accommodation_workflow(
                accommodation_request, self.request.data, self.request.user
            )

    def perform_update(self, serializer):
        """Update accommodation request and start workflow if status changes to Pending/Submitted"""
        old_status = self.get_object().status
        new_status = serializer.validated_data.get("status", old_status)

        # Set submitted_at timestamp if status is changing to submitted (not Draft)
        extra_kwargs = {}
        if new_status in ["Pending", "Submitted"] and old_status == "Draft":
            extra_kwargs["submitted_at"] = timezone.now()

            # Generate request number if submitting (changing from Draft to Pending/Submitted)
            accommodation_request = self.get_object()
            if not accommodation_request.request_number:
                request_number = generate_accommodation_request_number(
                    serializer.validated_data.get("additional_data", {})
                )
                if request_number:
                    extra_kwargs["request_number"] = request_number

        # Save the accommodation request
        accommodation_request = serializer.save(**extra_kwargs)

        # Start workflow if status changed from Draft to Pending/Submitted
        if new_status in ["Pending", "Submitted"] and old_status == "Draft":
            start_accommodation_workflow(
                accommodation_request, self.request.data, self.request.user
            )

    def perform_destroy(self, instance):
        """Log deletion before removing the record, since nothing else audits this."""
        AdminActionLog.log_action(
            user=self.request.user,
            action_type="entity_deleted",
            description=f"Deleted Accommodation Request #{instance.id} ({instance.request_number or 'no request number'})",
            entity_type="accommodation",
            entity_id=str(instance.id),
            request=self.request,
        )
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """
        Submit an accommodation request for approval
        Changes status from Draft to Pending and starts workflow
        """
        accommodation_request = self.get_object()

        # Validate status
        if accommodation_request.status != "Draft":
            return Response(
                {
                    "error": f"Cannot submit accommodation request with status {accommodation_request.status}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate request number if it doesn't exist
        if not accommodation_request.request_number:
            accommodation_request.request_number = (
                generate_accommodation_request_number_with_fallback(
                    accommodation_request
                )
            )

        # Update status and submitted_at
        accommodation_request.status = "Pending"
        accommodation_request.submitted_at = timezone.now()
        accommodation_request.save()

        # Start workflow using WorkflowRouter
        start_accommodation_workflow(accommodation_request, request.data, request.user)

        # Ensure we have the latest status before serializing
        accommodation_request.refresh_from_db()
        serializer = self.get_serializer(accommodation_request)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve an accommodation request using WorkflowEngine"""
        accommodation_request = self.get_object()
        comments = request.data.get("comments", "")
        result = process_accommodation_approval_action(
            accommodation_request, request, "approve", comments
        )
        if result is None:
            return None
        data, http_status = result
        return Response(data, status=http_status)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject an accommodation request using WorkflowEngine"""
        accommodation_request = self.get_object()
        comments = request.data.get("comments", "")
        result = process_accommodation_approval_action(
            accommodation_request, request, "reject", comments
        )
        if result is None:
            return None
        data, http_status = result
        return Response(data, status=http_status)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel an accommodation request"""
        accommodation_request = self.get_object()

        if accommodation_request.status in ["Approved", "Completed"]:
            return Response(
                {
                    "error": "Approved or completed accommodation requests cannot be cancelled"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        accommodation_request.status = "Cancelled"
        accommodation_request.save()

        serializer = self.get_serializer(accommodation_request)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="pending-approvals")
    def pending_approvals(self, request):
        """Deprecated: accommodation requests no longer have their own approval step.

        They ride entirely on their linked TSR's approval (see WorkflowEngine's
        accommodation cascade), so there is nothing for this queue to ever return.
        Kept as a no-op endpoint rather than removed, since the route may still be
        referenced by older clients/bookmarks.
        """
        return Response([])

    @action(detail=True, methods=["get"], url_path="export-pdf")
    def export_pdf(self, request, pk=None):
        """Export Accommodation Request to PDF - see accommodation/pdf_export.py"""
        from .pdf_export import build_request_pdf

        accommodation_request = self.get_object()
        return build_request_pdf(accommodation_request)

    @action(detail=True, methods=["post"])
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

        data, http_status = assign_accommodation(
            accommodation_request,
            staff_house_id=request.data.get("staff_house"),
            room_id=request.data.get("room"),
            start_date_str=request.data.get("start_date"),
            end_date_str=request.data.get("end_date"),
            notes=request.data.get("notes", ""),
            assigned_room_info=request.data.get("assigned_room_info", ""),
            actioned_by=request.user,
        )
        return Response(data, status=http_status)
