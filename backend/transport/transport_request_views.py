"""
TransportRequestViewSet - the transport module's dominant class.

Split out of transport/views.py (see docs/CODEBASE_REFACTOR_ROADMAP.md
item 7) - a pure file move, no logic changed. Approval-step/vehicle-
assignment viewsets moved to their own sibling module in the same split.
"""

import logging
from datetime import datetime

from accounts.models import AdminActionLog
from accounts.utils import can_view_all, has_permission, is_module_admin
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from utils.viewset_mixins import StandardResultsPagination

from .models import TransportApprovalStep, TransportRequest
from .serializers import (
    ApprovalActionSerializer,
    TransportRequestCreateSerializer,
    TransportRequestDetailSerializer,
    TransportRequestSerializer,
    TransportRequestUpdateSerializer,
)
from .services import (
    generate_unique_transport_request_number,
    process_transport_approval_action,
    start_transport_workflow,
)

logger = logging.getLogger(__name__)


class TransportRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing transport requests
    Supports CRUD operations and custom actions for workflow
    """

    permission_classes = [IsAuthenticated]
    # Was plain DRF PageNumberPagination, which ignores the client's
    # ?page_size= entirely (it has no page_size_query_param configured) and
    # always returns exactly PAGE_SIZE=10 regardless of what's requested.
    # Callers like the Transport Processing admin page ask for page_size=1000
    # expecting "all requests" - silently capping at page 1/10 items hid most
    # approved requests from that page. StandardResultsPagination (the
    # project-wide default other viewsets already get automatically) honors
    # page_size, capped at 100.
    pagination_class = StandardResultsPagination

    # Search across key fields
    search_fields = [
        "purpose",
        "request_number",
        "requestor_name",
        "staff_id",
        "department",
        "requestor__email",
        "requestor__name",
    ]

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
        if str(lookup_value).isdigit():
            filter_kwargs = {"pk": int(lookup_value)}
        else:
            filter_kwargs = {"request_number": lookup_value}

        queryset = self.filter_queryset(self.get_queryset())

        try:
            obj = queryset.get(**filter_kwargs)
        except TransportRequest.DoesNotExist:
            from rest_framework.exceptions import NotFound

            # Try to fetch from full queryset to get request_number for better error message
            try:
                obj = TransportRequest.objects.get(**filter_kwargs)
                request_identifier = obj.request_number or f"ID #{obj.id}"
                raise NotFound(
                    f"Transport request {request_identifier} not found or you do not have permission to access it"
                )
            except TransportRequest.DoesNotExist:
                raise NotFound(
                    f"Transport request not found with identifier: {lookup_value}"
                )

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def get_queryset(self):
        """
        Get queryset based on user permissions and filters

        Context-aware filtering:
        - Approval actions (approve/reject/retrieve): Allow access to requests pending user's approval
        - admin_view=true: Show all requests if user has view_all_transport permission (Admin Module)
        - Otherwise: Show only user's own requests (Personal Requests view)
        """
        from django.db.models import Q
        from workflows.services import WorkflowApprovalHelper

        user = self.request.user
        queryset = TransportRequest.objects.all()

        # For approval actions, allow access to requests pending the user's approval
        if self.action in ["approve", "reject"]:
            logger.info(
                " Approval action: Allowing access to all transport requests (authorization checked in WorkflowEngine)"
            )
            return queryset  # No filtering - authorization handled by WorkflowEngine

        # Every action below operates on ONE specific existing request
        # identified by pk in the URL (via self.get_object()) and already
        # enforces its own, finer-grained authorization internally (e.g.
        # complete() requires transport admin, cancel() requires owner-or-
        # admin, submit() requires the requestor) - none of them rely on
        # get_queryset() for security, only for looking the object up. They
        # must get the same view_all/superuser bypass as retrieve, else
        # get_object() 404s before ever reaching that internal check for
        # anyone acting on a request they didn't personally create - e.g. a
        # transport admin completing someone else's approved request, or
        # Transport Processing's "assign vehicle" booking-details PATCH.
        # None of these write-path callers ever pass admin_view=true (that
        # param only ever existed for the list endpoint).
        if self.action in (
            "retrieve",
            "update",
            "partial_update",
            "destroy",
            "submit",
            "cancel",
            "complete",
            "cancel_assignment",
            "reject_old",
            "export_pdf",
        ):
            # complete()/cancel()'s own internal check is is_module_admin
            # (view_all OR manage/process transport) - a strict superset of
            # can_view_all. A user with only manage_transport/
            # process_transport (no view_all_transport) would pass those
            # actions' own internal check but still 404 here first if this
            # bypass only checked can_view_all like the rest of the group -
            # see docs/RBAC_AND_ADMIN_ACCESS_FIX_ROADMAP.md Fix 6. The other
            # actions here (view/submit/export) are left on can_view_all
            # since viewing and processing are different permissions for
            # them - this is about precision, not blanket-widening.
            # cancel_assignment (Undo Completion) has the same is_module_admin
            # internal check as complete(), so it needs the same bypass -
            # else a transport admin can only ever undo their own requests.
            if self.action in ("cancel", "complete", "cancel_assignment"):
                is_admin = user.is_superuser or is_module_admin(user, "transport")
            else:
                is_admin = user.is_superuser or can_view_all(user, "transport")

            if is_admin:
                logger.info(
                    " %s action: User has admin access - allowing full visibility",
                    self.action,
                )
                return queryset
            pending_approval_ids = (
                WorkflowApprovalHelper.get_pending_entity_ids_for_user(
                    user, TransportRequest
                )
            )
            # Also include requests the user has ever acted on - without this,
            # an approver loses access to a request the instant their step
            # resolves (404 on revisiting via Recent Activity/email/back button).
            acted_ids = WorkflowApprovalHelper.get_acted_entity_ids_for_user(
                user, TransportRequest
            )
            queryset = queryset.filter(
                Q(requestor=user) | Q(id__in=pending_approval_ids) | Q(id__in=acted_ids)
            )
            logger.info(
                " %s action: Filtering to own requests and %s pending approval",
                self.action,
                len(pending_approval_ids),
            )
            return queryset

        # Check if this is an admin view (Transport Admin module)
        admin_view = (
            self.request.query_params.get("admin_view", "false").lower() == "true"
        )

        # Permission-based filtering
        if admin_view and (user.is_superuser or user.role):
            # Admin module context - check if user has permission to view all
            if user.is_superuser or can_view_all(user, "transport"):
                logger.info(
                    f" Admin view: User {user.email or user.username} (role: {user.role.name if user.role else None}) has 'view_all_transport' permission - showing all transport requests"
                )
                pass  # No filtering - show all transport requests
            else:
                # User doesn't have permission - show only their own plus pending approval
                pending_approval_ids = (
                    WorkflowApprovalHelper.get_pending_entity_ids_for_user(
                        user, TransportRequest
                    )
                )
                if pending_approval_ids:
                    queryset = queryset.filter(
                        Q(requestor=user) | Q(id__in=pending_approval_ids)
                    )
                    logger.info(
                        f" Admin view: User {user.email or user.username} - showing own requests plus {len(pending_approval_ids)} pending approval"
                    )
                else:
                    queryset = queryset.filter(requestor=user)
                    logger.warning(
                        f" Admin view: User {user.email or user.username} lacks permission - showing only own transport requests"
                    )
        else:
            # Personal requests view - show only user's own transport requests
            queryset = queryset.filter(requestor=user)
            logger.info(
                f" Personal view: User {user.email or user.username} - showing only own transport requests"
            )

        # Query parameter filters
        status_filter = self.request.query_params.get("status", None)
        if status_filter:
            # Use startswith to match workflow statuses like "Pending Line Manager"
            # when filter is "Pending"
            queryset = queryset.filter(status__istartswith=status_filter)

        trf_id = self.request.query_params.get("trf", None)
        if trf_id:
            queryset = queryset.filter(trf_id=trf_id)

        requestor_id = self.request.query_params.get("requestor", None)
        if requestor_id:
            queryset = queryset.filter(requestor_id=requestor_id)

        # Date range filters
        from_date = self.request.query_params.get("from_date", None)
        to_date = self.request.query_params.get("to_date", None)
        if from_date:
            queryset = queryset.filter(created_at__gte=from_date)
        if to_date:
            queryset = queryset.filter(created_at__lte=to_date)

        # Search filter
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                Q(purpose__icontains=search)
                | Q(request_number__icontains=search)
                | Q(requestor_name__icontains=search)
                | Q(staff_id__icontains=search)
                | Q(department__icontains=search)
                | Q(requestor__email__icontains=search)
                | Q(requestor__name__icontains=search)
            )

        # Explicit ordering: TransportRequest has no Meta.ordering, so without
        # this, row order (and therefore which rows land on which page) is
        # undefined and can vary between two otherwise-identical requests -
        # unsafe under pagination, where the client relies on page 1 meaning
        # the same rows each time.
        return (
            queryset.select_related("requestor", "trf")
            .prefetch_related("approval_steps", "vehicle_assignments")
            .order_by("-created_at", "-id")
        )

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "retrieve":
            return TransportRequestDetailSerializer
        elif self.action == "create":
            return TransportRequestCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return TransportRequestUpdateSerializer
        return TransportRequestSerializer

    def create(self, request, *args, **kwargs):
        """Create a new transport request"""
        if not request.user.is_superuser and not has_permission(
            request.user, "create_transport"
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "You do not have permission to create transport requests."
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Set requestor to current user and auto-populate requestor info"""
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
        # Only check for 'Pending' or 'Submitted' since those are what frontend sends
        # Workflow will update status to dynamic values like 'Pending HOD' etc.
        extra_kwargs = {}
        if status_value in ["Pending", "Submitted"]:
            extra_kwargs["submitted_at"] = timezone.now()

            # Generate request number if submitting directly (not Draft)
            if not validated_data.get("request_number"):
                try:
                    request_number = generate_unique_transport_request_number(
                        transport_details=validated_data.get("transport_details", []),
                        applicant_name=validated_data["requestor_name"],
                    )
                    extra_kwargs["request_number"] = request_number
                    logger.info(
                        f" Generated request number during creation: {request_number}"
                    )
                except Exception as e:
                    logger.error(f" Error generating request number: {str(e)}")
                    # Will be generated later if needed

        # Save the transport request
        transport_request = serializer.save(requestor=user, **extra_kwargs)

        # Start workflow if status is submitted (not Draft). Skipped entirely for
        # TSR-embedded requests (trf is set) - those ride on the parent TSR's own
        # approval instead of starting a separate transportrequest workflow; see
        # WorkflowEngine._cascade_status_to_linked_transport, which flips their
        # status to match the TSR's outcome once it resolves. Ad-hoc requests
        # (trf is null) are completely unaffected by this guard.
        if status_value in ["Pending", "Submitted"] and not transport_request.trf_id:
            try:
                start_transport_workflow(transport_request, self.request.data, user)
            except Exception as e:
                logger.error(
                    f" Error starting workflow for Transport Request #{transport_request.id}: {str(e)}"
                )
                # Don't fail the request creation if workflow fails
                pass

    def perform_update(self, serializer):
        """Handle transport request update, including workflow restart when re-submitting"""
        from django.contrib.contenttypes.models import ContentType
        from workflows.models import WorkflowInstance

        instance = serializer.instance
        old_status = instance.status
        new_status = serializer.validated_data.get("status", old_status)

        # Save the transport request
        transport_request = serializer.save()

        # Check if this is a re-submission (status changing to Pending from a non-Draft status)
        is_resubmission = (
            new_status == "Pending"
            and old_status not in ["Draft", "Pending"]
            and (old_status == "Rejected" or old_status.startswith("Pending"))
        )

        # Check if this is a first submission (Draft -> Pending)
        is_first_submission = old_status == "Draft" and new_status == "Pending"

        if is_first_submission or is_resubmission:
            # Update submitted_at timestamp
            transport_request.submitted_at = timezone.now()

            # Generate request number if doesn't exist
            if not transport_request.request_number:
                try:
                    transport_request.request_number = (
                        generate_unique_transport_request_number(
                            transport_details=transport_request.transport_details or [],
                            applicant_name=transport_request.requestor_name,
                        )
                    )
                    logger.info(
                        f" Generated request number: {transport_request.request_number}"
                    )
                except Exception as e:
                    logger.error(f" Error generating request number: {str(e)}")

            transport_request.save()

            # Cancel any existing in-progress workflow
            if is_resubmission:
                try:
                    content_type = ContentType.objects.get_for_model(transport_request)
                    existing_workflow = WorkflowInstance.objects.filter(
                        content_type=content_type,
                        object_id=transport_request.id,
                        status="in_progress",
                    ).first()
                    if existing_workflow:
                        existing_workflow.status = "cancelled"
                        existing_workflow.completed_at = timezone.now()
                        existing_workflow.save()
                        logger.info(
                            f" Cancelled existing workflow {existing_workflow.id} for re-submission"
                        )
                except Exception as e:
                    logger.warning(f" Error cancelling existing workflow: {str(e)}")

            # Start new workflow - skipped for TSR-embedded requests (trf is set),
            # same as perform_create/submit above.
            if not transport_request.trf_id:
                try:
                    start_transport_workflow(
                        transport_request, self.request.data, self.request.user
                    )
                except Exception as e:
                    logger.error(f" Error starting workflow: {str(e)}")

    def perform_destroy(self, instance):
        """Log deletion before removing the record, since nothing else audits this."""
        AdminActionLog.log_action(
            user=self.request.user,
            action_type="entity_deleted",
            description=f"Deleted Transport Request #{instance.id} ({instance.request_number or 'no request number'})",
            entity_type="transportrequest",
            entity_id=str(instance.id),
            request=self.request,
        )
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """
        Submit a transport request for approval
        Changes status from Draft to Pending and starts workflow
        """
        transport_request = self.get_object()

        # Validate requestor
        if transport_request.requestor != request.user:
            return Response(
                {"error": "Only the requestor can submit this transport request"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate status
        if transport_request.status != "Draft":
            return Response(
                {
                    "error": f"Cannot submit transport request with status {transport_request.status}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate has at least one transport detail
        if (
            not transport_request.transport_details
            or len(transport_request.transport_details) == 0
        ):
            return Response(
                {"error": "Transport request must have at least one transport detail"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate request number if it doesn't exist
        if not transport_request.request_number:
            try:
                request_number = generate_unique_transport_request_number(
                    transport_details=transport_request.transport_details or [],
                    applicant_name=transport_request.requestor_name,
                )
                transport_request.request_number = request_number
                logger.info(f" Generated request number: {request_number}")
            except Exception as e:
                logger.error(f" Error generating request number: {str(e)}")
                import traceback

                traceback.print_exc()
                # Fallback to simple format
                transport_request.request_number = f"TRN-{datetime.now().strftime('%Y%m%d-%H%M')}-TRN-{transport_request.id}"
                logger.warning(
                    f" Using fallback request number: {transport_request.request_number}"
                )

        # Update status and submitted_at
        transport_request.status = "Pending"
        transport_request.submitted_at = timezone.now()
        transport_request.save()

        # Start workflow using WorkflowRouter - skipped entirely for TSR-embedded
        # requests (trf is set), which ride on the parent TSR's own approval
        # instead. See WorkflowEngine._cascade_status_to_linked_transport, which
        # flips their status to match the TSR's outcome once it resolves. They
        # stay at the generic "Pending" status set above with no
        # WorkflowInstance/legacy approval step, exactly like embedded
        # Accommodation requests.
        if not transport_request.trf_id:
            try:
                workflow_instance = start_transport_workflow(
                    transport_request, request.data, request.user
                )

                if not workflow_instance:
                    # Fallback to legacy approval system if no workflow configured
                    logger.warning(
                        " No active workflow configured - creating legacy approval step"
                    )
                    TransportApprovalStep.objects.create(
                        transport_request=transport_request,
                        step_role="HOD",
                        step_name="HOD Approval",
                        status="Pending",
                    )
                    transport_request.status = "Pending Department Focal"
                    transport_request.save()
            except Exception as e:
                logger.error(f" Error starting workflow: {str(e)}")
                # Fallback to legacy system on error
                TransportApprovalStep.objects.create(
                    transport_request=transport_request,
                    step_role="HOD",
                    step_name="HOD Approval",
                    status="Pending",
                )
                transport_request.status = "Pending Department Focal"
                transport_request.save()

        # Ensure we have the latest status before serializing
        transport_request.refresh_from_db()
        serializer = TransportRequestDetailSerializer(transport_request)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """
        Approve a transport request using WorkflowEngine
        """
        transport_request = self.get_object()

        action_serializer = ApprovalActionSerializer(
            data=request.data, context={"action_type": "approve"}
        )
        action_serializer.is_valid(raise_exception=True)
        comments = action_serializer.validated_data.get("comments", "")

        result = process_transport_approval_action(
            transport_request, request, "approve", comments
        )
        if result is None:
            return None
        data, http_status = result
        return Response(data, status=http_status)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a transport request using WorkflowEngine"""
        transport_request = self.get_object()

        action_serializer = ApprovalActionSerializer(
            data=request.data, context={"action_type": "reject"}
        )
        action_serializer.is_valid(raise_exception=True)
        comments = action_serializer.validated_data.get("comments", "")

        result = process_transport_approval_action(
            transport_request, request, "reject", comments
        )
        if result is None:
            return None
        data, http_status = result
        return Response(data, status=http_status)

    @action(detail=True, methods=["post"])
    def reject_old(self, request, pk=None):
        """
        Reject a transport request at current approval step

        Deprecated: superseded by `reject`, which does everything this does
        plus the modern WorkflowEngine path. Kept registered (not part of
        this refactor's scope to remove) - see
        docs/CODEBASE_REFACTOR_ROADMAP.md item 7 for the "confirm unused,
        then delete" follow-up.
        """
        transport_request = self.get_object()
        user = request.user

        # Get user role
        user_role = user.role.name if hasattr(user, "role") and user.role else None

        # Validate status
        if transport_request.status not in ["Pending", "Approved"]:
            return Response(
                {
                    "error": f"Cannot reject transport request with status {transport_request.status}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get current pending approval step
        current_step = transport_request.approval_steps.filter(status="Pending").first()

        if not current_step:
            return Response(
                {"error": "No pending approval step found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate user has permission for this step
        is_admin = user.is_superuser or is_module_admin(user, "transport")
        if not is_admin and user_role != current_step.step_role:
            return Response(
                {
                    "error": f"You do not have permission to reject at step {current_step.step_role}"
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get approval action data
        action_serializer = ApprovalActionSerializer(
            data=request.data, context={"action_type": "reject"}
        )
        action_serializer.is_valid(raise_exception=True)
        comments = action_serializer.validated_data.get("comments", "")

        # Update current step
        current_step.status = "Rejected"
        current_step.step_date = timezone.now()
        current_step.comments = comments
        current_step.save()

        # Update transport request status
        transport_request.status = "Rejected"
        transport_request.save()

        serializer = TransportRequestDetailSerializer(transport_request)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def cancel_assignment(self, request, pk=None):
        """
        Undo a mistaken completion (transport admin only) - mirrors
        FlightBookingViewSet.cancel: soft-cancels the vehicle assignment
        (kept for audit trail, not deleted) and reverts the request back
        to Processing with Transport Admin so it can be reassigned and
        re-completed.
        """
        transport_request = self.get_object()

        if not request.user.is_superuser and not is_module_admin(
            request.user, "transport"
        ):
            return Response(
                {"error": "Only transport admin can undo a completed request"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if transport_request.status != "Completed":
            return Response(
                {
                    "error": f"Cannot undo completion for a request with status {transport_request.status}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        active_assignments = list(
            transport_request.vehicle_assignments.exclude(status="Cancelled")
        )
        for assignment in active_assignments:
            assignment.status = "Cancelled"
            assignment.save(update_fields=["status"])

        transport_request.status = "Processing with Transport Admin"
        transport_request.save(update_fields=["status"])

        assignment_ids = ", ".join(f"#{a.id}" for a in active_assignments) or "none"
        AdminActionLog.log_action(
            user=request.user,
            action_type="vehicle_assignment_cancelled",
            description=(
                f"Undid completion of transport request {transport_request.request_number} "
                f"(vehicle assignment(s) {assignment_ids} cancelled)"
            ),
            entity_type="TransportRequest",
            entity_id=str(transport_request.id),
            request=request,
        )

        serializer = TransportRequestDetailSerializer(transport_request)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """
        Cancel a transport request (by requestor or admin)
        """
        transport_request = self.get_object()

        # Validate requestor or admin
        is_admin = request.user.is_superuser or is_module_admin(
            request.user, "transport"
        )
        if transport_request.requestor != request.user and not is_admin:
            return Response(
                {
                    "error": "Only the requestor or admin can cancel this transport request"
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate status
        if transport_request.status in ["Completed", "Cancelled"]:
            return Response(
                {
                    "error": f"Cannot cancel transport request with status {transport_request.status}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update status
        transport_request.status = "Cancelled"
        transport_request.save()

        serializer = TransportRequestDetailSerializer(transport_request)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """
        Mark a transport request as completed (by transport admin only)
        """
        transport_request = self.get_object()

        # Validate user has transport admin permission
        if not request.user.is_superuser and not is_module_admin(
            request.user, "transport"
        ):
            return Response(
                {"error": "Only transport admin can mark requests as completed"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate status - can only complete approved or processing requests
        if transport_request.status not in [
            "Approved",
            "Processing with Transport Admin",
        ]:
            return Response(
                {
                    "error": f"Cannot complete transport request with status {transport_request.status}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate that vehicle has been assigned
        if not transport_request.vehicle_assignments.exists():
            return Response(
                {"error": "Cannot complete request without vehicle assignment"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update status
        transport_request.status = "Completed"
        transport_request.save()

        # Notify the requester - this action happens after the approval
        # workflow already finished, so it needs its own trigger (see
        # WorkflowNotifications.notify_processing_completed).
        try:
            from django.contrib.contenttypes.models import ContentType
            from workflows.models import WorkflowInstance
            from workflows.notifications import WorkflowNotifications

            content_type = ContentType.objects.get_for_model(transport_request)
            workflow_instance = (
                WorkflowInstance.objects.filter(
                    content_type=content_type, object_id=transport_request.id
                )
                .order_by("-created_at")
                .first()
            )
            if workflow_instance:
                WorkflowNotifications.notify_processing_completed(
                    workflow_instance, completed_by=request.user
                )
        except Exception:
            logger.exception(
                "Failed to send processing completion notification for "
                "TransportRequest #%s",
                transport_request.id,
            )

        if transport_request.trf:
            from trf.services import notify_department_focal_if_ready

            notify_department_focal_if_ready(transport_request.trf)

        serializer = TransportRequestDetailSerializer(transport_request)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
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

    @action(detail=False, methods=["get"], url_path="pending-approvals")
    def pending_approvals(self, request):
        """
        Get all transport requests pending approval for the current user based on workflow step assignments
        """
        from workflows.services import WorkflowApprovalHelper

        user = request.user

        # Admins and superusers see all pending requests
        # Use startswith to match any workflow-generated 'Pending *' status
        if user.is_superuser or is_module_admin(user, "transport"):
            queryset = (
                self.get_queryset()
                .filter(
                    Q(status__startswith="Pending")
                    | Q(status="Submitted")
                    | Q(status="Under Review")
                )
                .order_by("-submitted_at")
            )
        else:
            # Use workflow-based filtering: get entities where user's role matches current step
            pending_ids = WorkflowApprovalHelper.get_pending_entity_ids_for_user(
                user, TransportRequest
            )
            queryset = (
                self.get_queryset().filter(id__in=pending_ids).order_by("-submitted_at")
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="export-pdf")
    def export_pdf(self, request, pk=None):
        """Export Transport Request to PDF - see transport/pdf_export.py"""
        from .pdf_export import build_request_pdf

        transport_request = self.get_object()
        return build_request_pdf(transport_request)
