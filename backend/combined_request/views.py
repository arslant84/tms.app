"""
Combined Request Views

Full implementation of ViewSets for the Combined Request API
with workflow integration and proper permission handling.
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

from accounts.utils import can_approve, can_view_all, has_permission
from django.contrib.contenttypes.models import ContentType
from utils.api_response import (
    created_response,
    error_response,
    forbidden_response,
    not_found_response,
    server_error_response,
    success_response,
    validation_error_response,
)
from utils.request_id_generator import extract_context_for_combined, generate_request_id
from workflows.engine import WorkflowEngine
from workflows.models import WorkflowInstance
from workflows.router import WorkflowRouter

from .models import (
    CombinedRequest,
    CombinedRequestApprovalStep,
    CombinedRequestDocument,
    CombinedRequestItinerary,
    CombinedRequestPassport,
    CombinedRequestTransportSegment,
)
from .serializers import (
    CombinedRequestApprovalStepSerializer,
    CombinedRequestCreateSerializer,
    CombinedRequestDetailSerializer,
    CombinedRequestDocumentSerializer,
    CombinedRequestItinerarySerializer,
    CombinedRequestListSerializer,
    CombinedRequestPassportSerializer,
    CombinedRequestTransportSegmentSerializer,
    CombinedRequestUpdateSerializer,
)


class CombinedRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Combined Request CRUD operations.

    Endpoints:
    - GET /api/combined-request/ - List all combined requests
    - POST /api/combined-request/ - Create a new combined request
    - GET /api/combined-request/{id}/ - Retrieve combined request details
    - PUT /api/combined-request/{id}/ - Update combined request
    - PATCH /api/combined-request/{id}/ - Partial update
    - DELETE /api/combined-request/{id}/ - Delete combined request
    - POST /api/combined-request/{id}/submit/ - Submit for approval
    - POST /api/combined-request/{id}/approve/ - Approve request
    - POST /api/combined-request/{id}/reject/ - Reject request
    - POST /api/combined-request/{id}/cancel/ - Cancel request
    - GET /api/combined-request/{id}/approval-history/ - Get approval history

    Filtering & Search:
    - ?search=query - Search across requestor_name, department, destination_city, request_number
    - ?status=Draft - Filter by status
    - ?include_travel=true - Filter by included modules
    - ?admin_view=true - Show all requests (for admins)
    """

    queryset = CombinedRequest.objects.all()
    serializer_class = CombinedRequestListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    # Search across key fields
    search_fields = [
        "requestor_name",
        "department",
        "destination_city",
        "request_number",
        "staff_id",
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
    ordering = ["-created_at"]

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
            filter_kwargs = {"pk": int(lookup_value)}
        else:
            filter_kwargs = {"request_number": lookup_value}

        queryset = self.filter_queryset(self.get_queryset())

        try:
            obj = queryset.get(**filter_kwargs)
        except CombinedRequest.DoesNotExist:
            from rest_framework.exceptions import NotFound

            try:
                obj = CombinedRequest.objects.get(**filter_kwargs)
                request_identifier = obj.request_number or f"ID #{obj.id}"
                raise NotFound(
                    f"Combined request {request_identifier} not found or you do not have permission to access it"
                )
            except CombinedRequest.DoesNotExist:
                raise NotFound(
                    f"Combined request not found with identifier: {lookup_value}"
                )

        self.check_object_permissions(self.request, obj)
        return obj

    def get_serializer_class(self):
        """Use appropriate serializer based on action"""
        if self.action == "list":
            return CombinedRequestListSerializer
        elif self.action == "retrieve":
            return CombinedRequestDetailSerializer
        elif self.action == "create":
            return CombinedRequestCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return CombinedRequestUpdateSerializer
        return CombinedRequestDetailSerializer

    def get_queryset(self):
        """
        Filter combined requests based on query parameters and user permissions

        Context-aware filtering:
        - admin_view=true: Show all requests if user has appropriate permissions
        - Approval actions: Allow access to requests pending user's approval
        - Otherwise: Show only user's own requests
        """
        from workflows.services import WorkflowApprovalHelper

        user = self.request.user
        queryset = self.queryset

        logger.debug("\n=== CombinedRequest GET_QUERYSET ===")
        logger.debug(f"User: {user}, Action: {self.action}")

        # For approval actions, allow access (authorization checked in WorkflowEngine)
        if self.action in ["approve", "reject"]:
            logger.info("Approval action: Allowing access to all requests")
            return queryset

        # For retrieve, check view_all permission or pending approvals
        if self.action == "retrieve":
            if can_view_all(user, "combined"):
                logger.info(
                    "Retrieve: User has view_all_combined - allowing full access"
                )
                return queryset
            pending_approval_ids = (
                WorkflowApprovalHelper.get_pending_entity_ids_for_user(
                    user, CombinedRequest
                )
            )
            queryset = queryset.filter(
                Q(requestor=user) | Q(id__in=pending_approval_ids)
            )
            return queryset

        # Check if admin view
        admin_view = (
            self.request.query_params.get("admin_view", "false").lower() == "true"
        )

        if admin_view and user.role:
            if can_view_all(user, "combined"):
                logger.info("Admin view: User has view_all_combined permission")
                pass  # No filtering
            elif has_permission(user, "approve_combined") or has_permission(
                user, "view_pending_approvals"
            ):
                if user.department:
                    queryset = queryset.filter(
                        department=(
                            user.department.name
                            if hasattr(user.department, "name")
                            else user.department
                        )
                    )
                else:
                    queryset = queryset.filter(requestor=user)
            else:
                pending_approval_ids = (
                    WorkflowApprovalHelper.get_pending_entity_ids_for_user(
                        user, CombinedRequest
                    )
                )
                if pending_approval_ids:
                    queryset = queryset.filter(
                        Q(requestor=user) | Q(id__in=pending_approval_ids)
                    )
                else:
                    queryset = queryset.filter(requestor=user)
        else:
            # Personal requests view
            queryset = queryset.filter(requestor=user)
            logger.info("Personal view: Showing only user's own requests")

        # Apply filters
        status_filter = self.request.query_params.get("status", None)
        if status_filter:
            queryset = queryset.filter(status__istartswith=status_filter)

        # Filter by included modules
        if self.request.query_params.get("include_travel", "").lower() == "true":
            queryset = queryset.filter(include_travel=True)
        if self.request.query_params.get("include_transport", "").lower() == "true":
            queryset = queryset.filter(include_transport=True)
        if self.request.query_params.get("include_accommodation", "").lower() == "true":
            queryset = queryset.filter(include_accommodation=True)
        if self.request.query_params.get("include_visa", "").lower() == "true":
            queryset = queryset.filter(include_visa=True)

        # Search
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                Q(requestor_name__icontains=search)
                | Q(department__icontains=search)
                | Q(destination_city__icontains=search)
                | Q(staff_id__icontains=search)
                | Q(request_number__icontains=search)
            )

        # Sorting
        sort_by = self.request.query_params.get("sortBy", None)
        sort_order = self.request.query_params.get("sortOrder", "descending")

        if sort_by and sort_by in self.ordering_fields:
            order_field = f"-{sort_by}" if sort_order == "descending" else sort_by
            return queryset.order_by(order_field)

        return queryset.order_by("-created_at")

    def create(self, request, *args, **kwargs):
        """Override to log validation errors clearly"""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(
                f"CombinedRequest CREATE validation errors: {serializer.errors}"
            )
            return validation_error_response(serializer.errors)
        self.perform_create(serializer)
        return created_response(data=serializer.data)

    def update(self, request, *args, **kwargs):
        """Override to add status check, logging and standardised success_response."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        # Block edits for non-editable statuses (mirrors TRF behaviour)
        current_status = instance.status or ""
        is_editable = current_status in (
            "Draft",
            "Rejected",
        ) or current_status.startswith("Pending")
        if not is_editable:
            return error_response(
                message=(
                    f"This request cannot be edited because its status is '{current_status}'. "
                    "Only Draft, Rejected, or Pending requests can be edited."
                ),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if not serializer.is_valid():
            logger.error(
                f"CombinedRequest UPDATE validation errors for #{instance.id}: {serializer.errors}"
            )
            return validation_error_response(serializer.errors)

        logger.info(
            f"CombinedRequest UPDATE #{instance.id}: "
            f"departure_date={request.data.get('departure_date')}, "
            f"return_date={request.data.get('return_date')}, "
            f"destination_city={request.data.get('destination_city')}"
        )

        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            instance._prefetched_objects_cache = {}

        # Re-fetch with the detail serializer so the response is complete
        instance.refresh_from_db()
        from .serializers import CombinedRequestDetailSerializer

        response_serializer = CombinedRequestDetailSerializer(instance)
        return success_response(
            data=response_serializer.data,
            message="Combined request updated successfully",
        )

    def perform_update(self, serializer):
        """Reset status to Draft when a request is edited so it can be re-submitted."""
        from django.utils import timezone

        serializer.save(status="Draft", submitted_at=None)

    def perform_create(self, serializer):
        """Set requestor and auto-populate info, optionally start workflow if submitted"""
        user = self.request.user
        validated_data = serializer.validated_data

        # Auto-populate requestor information if not provided
        if not validated_data.get("requestor_name"):
            validated_data["requestor_name"] = user.name or user.email
        if not validated_data.get("staff_id"):
            validated_data["staff_id"] = getattr(user, "staff_id", "")
        if not validated_data.get("department"):
            validated_data["department"] = (
                user.department.name if user.department else ""
            )
        if not validated_data.get("position"):
            validated_data["position"] = getattr(user, "position", "")
        if not validated_data.get("email"):
            validated_data["email"] = user.email

        # Get status from request data
        status_value = validated_data.get("status", "Draft")

        extra_kwargs = {}
        if status_value not in ["Draft"]:
            extra_kwargs["submitted_at"] = timezone.now()

        # Save the combined request
        combined_request = serializer.save(requestor=user, **extra_kwargs)

        # Start workflow if not Draft
        if status_value not in ["Draft"]:
            selected_approvers = self.request.data.get("selected_approvers", None)
            if selected_approvers:
                selected_approvers = {int(k): v for k, v in selected_approvers.items()}

            skipped_steps = self.request.data.get("skipped_steps", None)
            if skipped_steps:
                skipped_steps = {int(k): v for k, v in skipped_steps.items()}

            try:
                workflow_instance = WorkflowRouter.start_workflow_for_request(
                    entity=combined_request,
                    entity_type="combinedrequest",
                    initiated_by=user,
                    selected_approvers=selected_approvers,
                    skipped_steps=skipped_steps,
                )

                if workflow_instance:
                    combined_request.refresh_from_db()
                    logger.info(
                        f"Workflow started for Combined Request #{combined_request.id}"
                    )
            except Exception as e:
                logger.error(f"Error starting workflow: {str(e)}")

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """
        Submit a Combined Request for approval.
        Changes status from Draft to Pending and starts workflow.
        """
        combined_request = self.get_object()

        if combined_request.status != "Draft":
            return error_response(
                message="Only draft requests can be submitted",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Generate request number if not exists
        if not combined_request.request_number:
            try:
                context = extract_context_for_combined(
                    destination_city=combined_request.destination_city,
                    destination_country=combined_request.destination_country,
                )
                combined_request.request_number = generate_request_id("CMB", context)
                logger.info(
                    f"Generated request number: {combined_request.request_number}"
                )
            except Exception as e:
                logger.error(f"Error generating request number: {str(e)}")
                combined_request.request_number = f"CMB-{timezone.now().strftime('%Y%m%d-%H%M')}-{combined_request.id}"

        # Update status and submitted_at
        combined_request.status = "Pending"
        combined_request.submitted_at = timezone.now()

        # Update module statuses for included modules
        if combined_request.include_travel:
            combined_request.travel_status = "pending"
        if combined_request.include_transport:
            combined_request.transport_status = "pending"
        if combined_request.include_accommodation:
            combined_request.accommodation_status = "pending"
        if combined_request.include_visa:
            combined_request.visa_status = "pending"

        combined_request.save()

        # Extract approver selections
        selected_approvers = request.data.get("selected_approvers", None)
        if selected_approvers:
            selected_approvers = {int(k): v for k, v in selected_approvers.items()}

        skipped_steps = request.data.get("skipped_steps", None)
        if skipped_steps:
            skipped_steps = {int(k): v for k, v in skipped_steps.items()}

        # Start workflow
        try:
            workflow_instance = WorkflowRouter.start_workflow_for_request(
                entity=combined_request,
                entity_type="combinedrequest",
                initiated_by=request.user,
                selected_approvers=selected_approvers,
                skipped_steps=skipped_steps,
            )

            if workflow_instance:
                combined_request.refresh_from_db()
                logger.info(f"Workflow started: Instance #{workflow_instance.id}")
            else:
                logger.warning("No active workflow configured for combinedrequest")
                # Fallback - create a basic approval step
                CombinedRequestApprovalStep.objects.create(
                    combined_request=combined_request,
                    step_order=1,
                    step_name="Line Manager Approval",
                    step_role="Line Manager",
                    status="pending",
                )
                combined_request.status = "Pending Line Manager"
                combined_request.save()

        except Exception as e:
            logger.error(f"Error starting workflow: {str(e)}")
            combined_request.status = "Pending Line Manager"
            combined_request.save()

        combined_request.refresh_from_db()
        serializer = CombinedRequestDetailSerializer(combined_request)
        return success_response(
            data=serializer.data,
            message="Combined request submitted successfully",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a Combined Request at current approval step using WorkflowEngine"""
        combined_request = self.get_object()

        step_role = request.data.get("step_role", "")
        comments = request.data.get("comments", "")

        try:
            content_type = ContentType.objects.get_for_model(combined_request)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=combined_request.id,
                status="in_progress",
            ).first()

            logger.debug(f"Approving Combined Request #{combined_request.id}")
            logger.debug(
                f"User: {request.user.email}, Workflow found: {workflow_instance is not None}"
            )

            if workflow_instance:
                current_step = (
                    workflow_instance.step_executions.filter(status="pending")
                    .order_by("workflow_step__step_order")
                    .first()
                )

                if current_step:
                    WorkflowEngine.process_action(
                        step_execution_id=current_step.id,
                        action="approve",
                        actioned_by=request.user,
                        comments=comments,
                    )

                    combined_request.refresh_from_db()

                    # Update legacy approval step
                    approval_step, created = (
                        CombinedRequestApprovalStep.objects.get_or_create(
                            combined_request=combined_request,
                            step_order=current_step.workflow_step.step_order,
                            defaults={
                                "step_name": current_step.workflow_step.step_name,
                                "step_role": step_role,
                                "status": "pending",
                            },
                        )
                    )
                    approval_step.status = "approved"
                    approval_step.comments = comments
                    approval_step.approver = request.user
                    approval_step.actioned_at = timezone.now()
                    approval_step.save()

                    serializer = CombinedRequestDetailSerializer(combined_request)
                    return success_response(
                        data=serializer.data,
                        message="Combined request approved successfully",
                        status_code=status.HTTP_200_OK,
                    )
                else:
                    return error_response(
                        message="No pending approval step found",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                # Legacy fallback
                if not (
                    request.user.is_superuser or can_approve(request.user, "combined")
                ):
                    return forbidden_response(
                        message="You do not have permission to approve combined requests"
                    )

                if not combined_request.status.startswith("Pending"):
                    return error_response(
                        message=f"Cannot approve request with status {combined_request.status}",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

                logger.warning("No workflow instance found, using legacy approval")
                combined_request.status = "Approved"
                combined_request.save()

                serializer = CombinedRequestDetailSerializer(combined_request)
                return success_response(
                    data=serializer.data,
                    message="Combined request approved successfully",
                    status_code=status.HTTP_200_OK,
                )

        except ValueError as e:
            logger.error(f"ValueError in approve: {str(e)}")
            return error_response(
                message=str(e), status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in approve: {str(e)}", exc_info=True)
            return server_error_response(
                message="Failed to process approval", error_details=str(e)
            )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a Combined Request using WorkflowEngine"""
        combined_request = self.get_object()

        step_role = request.data.get("step_role", "")
        comments = request.data.get("comments", "")

        if not comments:
            return error_response(
                message="Comments are required when rejecting a request",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            content_type = ContentType.objects.get_for_model(combined_request)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=combined_request.id,
                status="in_progress",
            ).first()

            if workflow_instance:
                current_step = (
                    workflow_instance.step_executions.filter(status="pending")
                    .order_by("workflow_step__step_order")
                    .first()
                )

                if current_step:
                    WorkflowEngine.process_action(
                        step_execution_id=current_step.id,
                        action="reject",
                        actioned_by=request.user,
                        comments=comments,
                    )

                    combined_request.refresh_from_db()

                    # Update legacy approval step
                    approval_step, created = (
                        CombinedRequestApprovalStep.objects.get_or_create(
                            combined_request=combined_request,
                            step_order=current_step.workflow_step.step_order,
                            defaults={
                                "step_name": current_step.workflow_step.step_name,
                                "step_role": step_role,
                                "status": "pending",
                            },
                        )
                    )
                    approval_step.status = "rejected"
                    approval_step.comments = comments
                    approval_step.approver = request.user
                    approval_step.actioned_at = timezone.now()
                    approval_step.save()

                    serializer = CombinedRequestDetailSerializer(combined_request)
                    return success_response(
                        data=serializer.data,
                        message="Combined request rejected",
                        status_code=status.HTTP_200_OK,
                    )
                else:
                    return error_response(
                        message="No pending approval step found",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                if not (
                    request.user.is_superuser or can_approve(request.user, "combined")
                ):
                    return forbidden_response(
                        message="You do not have permission to reject combined requests"
                    )

                if not combined_request.status.startswith("Pending"):
                    return error_response(
                        message=f"Cannot reject request with status {combined_request.status}",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

                combined_request.status = "Rejected"
                combined_request.save()

                serializer = CombinedRequestDetailSerializer(combined_request)
                return success_response(
                    data=serializer.data,
                    message="Combined request rejected",
                    status_code=status.HTTP_200_OK,
                )

        except Exception as e:
            logger.error(f"Error in reject: {str(e)}", exc_info=True)
            return server_error_response(
                message="Failed to process rejection", error_details=str(e)
            )

    @action(detail=True, methods=["post"], url_path="process-module")
    def process_module(self, request, pk=None):
        """
        Save admin processing details for one module of a combined request
        and mark that module as completed.

        Body:
            module: 'travel' | 'transport' | 'accommodation' | 'visa'
            processing_data: dict of module-specific fields

        Side effects:
            - Saves processing_data into additional_data.processing.{module}
            - Sets {module}_status = 'completed'
            - Moves status Approved → Processing on first module save
            - Auto-sets status to 'Completed' when all included modules are done
        """
        combined_request = self.get_object()
        module = request.data.get("module", "")
        processing_data = request.data.get("processing_data", {})

        valid_modules = ["travel", "transport", "accommodation", "visa"]
        if module not in valid_modules:
            return error_response(
                message=f"Invalid module '{module}'. Must be one of: {', '.join(valid_modules)}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Check that the user has permission to process this specific module.
        # Full combined-request admins (process_combined_requests) may process all modules.
        # Module-specific admins may only process their own module.
        MODULE_PERMISSION_MAP = {
            "travel": "view_admin_flights",
            "transport": "view_admin_transport",
            "accommodation": "view_admin_accommodation",
            "visa": "view_admin_visa",
        }
        if not request.user.is_superuser:
            user_perms = (
                set(request.user.role.permissions.values_list("name", flat=True))
                if getattr(request.user, "role", None)
                else set()
            )
            has_process_all = "process_combined_requests" in user_perms
            has_module_perm = MODULE_PERMISSION_MAP.get(module, "") in user_perms
            if not (has_process_all or has_module_perm):
                return error_response(
                    message=f"You do not have permission to process the '{module}' module.",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        # Verify the module is actually included in this request
        include_field = f"include_{module}"
        if not getattr(combined_request, include_field, False):
            return error_response(
                message=f"Module '{module}' is not included in this combined request",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Build the processing result entry
        processing_result = {
            **processing_data,
            "status": "completed",
            "completed_at": timezone.now().isoformat(),
            "completed_by": getattr(request.user, "name", None) or str(request.user),
        }

        # Merge into additional_data.processing.{module}
        additional_data = dict(combined_request.additional_data or {})
        if "processing" not in additional_data:
            additional_data["processing"] = {}
        additional_data["processing"][module] = processing_result

        # Update the per-module status field
        setattr(combined_request, f"{module}_status", "completed")

        # Transition Approved → Processing on first module save
        if combined_request.status == "Approved":
            combined_request.status = "Processing"

        # Auto-complete when all included modules are done
        included_modules = combined_request.get_included_modules()
        all_done = all(
            additional_data["processing"].get(m, {}).get("status") == "completed"
            for m in included_modules
        )
        if all_done and included_modules:
            combined_request.status = "Completed"

        combined_request.additional_data = additional_data
        combined_request.save()

        combined_request.refresh_from_db()
        serializer = CombinedRequestDetailSerializer(combined_request)
        logger.info(
            f"CombinedRequest #{combined_request.id} module '{module}' processed by "
            f"{request.user}. Overall status: {combined_request.status}"
        )
        return success_response(
            data=serializer.data,
            message=f"{module.title()} module processed successfully",
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a Combined Request"""
        combined_request = self.get_object()

        if combined_request.status in ["Approved", "Completed", "Processing"]:
            return error_response(
                message="Approved, completed, or processing requests cannot be cancelled",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        combined_request.status = "Cancelled"
        combined_request.save()

        serializer = CombinedRequestDetailSerializer(combined_request)
        return success_response(
            data=serializer.data,
            message="Combined request cancelled successfully",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="upload-document")
    def upload_document(self, request, pk=None):
        """Upload a supporting document for a combined request."""
        combined_request = self.get_object()

        file = request.FILES.get("file")
        if not file:
            return error_response(
                message="No file provided.", status_code=status.HTTP_400_BAD_REQUEST
            )

        document_type = request.data.get("document_type", "supporting_doc")
        module = request.data.get("module", "visa")
        description = request.data.get("description", "")
        file_name = file.name

        doc = CombinedRequestDocument.objects.create(
            combined_request=combined_request,
            document_type=document_type,
            module=module,
            file=file,
            file_name=file_name,
            description=description,
            uploaded_by=request.user,
        )

        from .serializers import CombinedRequestDocumentSerializer

        serializer = CombinedRequestDocumentSerializer(doc)
        return success_response(
            data=serializer.data,
            message="Document uploaded successfully",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["delete"], url_path=r"documents/(?P<doc_id>\d+)")
    def delete_document(self, request, pk=None, doc_id=None):
        """Delete a supporting document from a combined request."""
        combined_request = self.get_object()
        try:
            doc = CombinedRequestDocument.objects.get(
                id=doc_id, combined_request=combined_request
            )
        except CombinedRequestDocument.DoesNotExist:
            return error_response(
                message="Document not found.", status_code=status.HTTP_404_NOT_FOUND
            )
        doc.file.delete(save=False)
        doc.delete()
        return success_response(message="Document deleted successfully")

    @action(detail=True, methods=["get"], url_path="approval-history")
    def approval_history(self, request, pk=None):
        """Get the approval history for a combined request"""
        combined_request = self.get_object()

        # Get workflow-based history
        content_type = ContentType.objects.get_for_model(combined_request)
        workflow_instances = WorkflowInstance.objects.filter(
            content_type=content_type, object_id=combined_request.id
        ).prefetch_related(
            "step_executions__workflow_step", "step_executions__actioned_by"
        )

        history = []
        for workflow in workflow_instances:
            for step_exec in workflow.step_executions.all().order_by(
                "workflow_step__step_order"
            ):
                history.append(
                    {
                        "step_order": step_exec.workflow_step.step_order,
                        "step_name": step_exec.workflow_step.step_name,
                        "status": step_exec.status,
                        "assigned_to": (
                            step_exec.assigned_to.name
                            if step_exec.assigned_to
                            else None
                        ),
                        "actioned_by": (
                            step_exec.actioned_by.name
                            if step_exec.actioned_by
                            else None
                        ),
                        "action_date": (
                            step_exec.action_date.isoformat()
                            if step_exec.action_date
                            else None
                        ),
                        "comments": step_exec.comments,
                    }
                )

        # Also include legacy approval steps
        legacy_steps = combined_request.approval_steps.all().order_by("step_order")
        serializer = CombinedRequestApprovalStepSerializer(legacy_steps, many=True)

        return success_response(
            data={"workflow_history": history, "legacy_steps": serializer.data},
            message="Retrieved approval history",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="export-pdf")
    def export_pdf(self, request, pk=None):
        """Export Combined Request to PDF"""
        from .pdf_generator import generate_combined_request_pdf

        cr = self.get_object()
        return generate_combined_request_pdf(cr)

    @action(detail=False, methods=["get"], url_path="pending-approvals")
    def pending_approvals(self, request):
        """Get Combined Requests pending approval for the current user"""
        from accounts.utils import is_module_admin
        from workflows.services import WorkflowApprovalHelper

        user = request.user

        if user.is_superuser or is_module_admin(user, "combined"):
            queryset = CombinedRequest.objects.filter(
                Q(status__startswith="Pending")
                | Q(status="Submitted")
                | Q(status="Under Review")
            ).order_by("-submitted_at")
        else:
            pending_ids = WorkflowApprovalHelper.get_pending_entity_ids_for_user(
                user, CombinedRequest
            )
            queryset = CombinedRequest.objects.filter(id__in=pending_ids).order_by(
                "-submitted_at"
            )

        serializer = CombinedRequestDetailSerializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message=f"Retrieved {queryset.count()} pending approval(s)",
            status_code=status.HTTP_200_OK,
        )


# Nested ViewSets for related resources


class CombinedRequestPassportViewSet(viewsets.ModelViewSet):
    """ViewSet for managing passport details"""

    serializer_class = CombinedRequestPassportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        combined_request_id = self.request.query_params.get("combined_request", None)
        if combined_request_id:
            return CombinedRequestPassport.objects.filter(
                combined_request_id=combined_request_id
            )
        return CombinedRequestPassport.objects.all()


class CombinedRequestItineraryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing itinerary segments"""

    serializer_class = CombinedRequestItinerarySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        combined_request_id = self.request.query_params.get("combined_request", None)
        if combined_request_id:
            return CombinedRequestItinerary.objects.filter(
                combined_request_id=combined_request_id
            )
        return CombinedRequestItinerary.objects.all().order_by("segment_order")


class CombinedRequestTransportSegmentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing transport segments"""

    serializer_class = CombinedRequestTransportSegmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        combined_request_id = self.request.query_params.get("combined_request", None)
        if combined_request_id:
            return CombinedRequestTransportSegment.objects.filter(
                combined_request_id=combined_request_id
            )
        return CombinedRequestTransportSegment.objects.all().order_by("segment_order")


class CombinedRequestDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing documents"""

    serializer_class = CombinedRequestDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        combined_request_id = self.request.query_params.get("combined_request", None)
        if combined_request_id:
            return CombinedRequestDocument.objects.filter(
                combined_request_id=combined_request_id
            )
        return CombinedRequestDocument.objects.all()

    def perform_create(self, serializer):
        """Set uploaded_by on document creation"""
        serializer.save(uploaded_by=self.request.user)
