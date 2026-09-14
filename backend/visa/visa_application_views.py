"""
VisaApplicationViewSet - the visa module's dominant class.

Split out of visa/views.py (see docs/CODEBASE_REFACTOR_ROADMAP.md item 8)
- a pure file move for get_queryset/CRUD/small actions, with the
request-number/workflow-start/approve-reject-dispatch duplication
collapsed into visa/services.py. Approval-step/document viewsets moved to
their own sibling module in the same split.
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
from utils import error_response, success_response

from .models import VisaApplication
from .serializers import (
    VisaApplicationCreateUpdateSerializer,
    VisaApplicationDetailSerializer,
    VisaApplicationListSerializer,
)
from .services import (
    finalize_visa_workflow_completion,
    generate_unique_visa_request_number,
    process_visa_approval_action,
    start_visa_workflow,
)

logger = logging.getLogger(__name__)


class VisaApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet for visa applications with different serializers for list/detail/create"""

    queryset = (
        VisaApplication.objects.all()
        .select_related("user")
        .prefetch_related("visaapprovalstep_set", "visadocument_set")
        .order_by("-created_at")
    )
    permission_classes = [IsAuthenticated]

    # Search across key fields
    search_fields = [
        "requestor_name",
        "destination",
        "passport_number",
        "request_number",
        "user__email",
    ]

    # Allow ordering
    ordering_fields = [
        "created_at",
        "submitted_date",
        "trip_start_date",
        "destination",
        "status",
    ]
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
        except VisaApplication.DoesNotExist:
            from rest_framework.exceptions import NotFound

            # Try to fetch from full queryset to get request_number for better error message
            try:
                obj = VisaApplication.objects.get(**filter_kwargs)
                request_identifier = obj.request_number or f"ID #{obj.id}"
                raise NotFound(
                    f"Visa application {request_identifier} not found or you do not have permission to access it"
                )
            except VisaApplication.DoesNotExist:
                raise NotFound(
                    f"Visa application not found with identifier: {lookup_value}"
                )

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def get_queryset(self):
        """
        Filter visa applications based on user permissions

        Context-aware filtering:
        - Approval actions (approve/reject/retrieve): Allow access to applications pending user's approval
        - admin_view=true: Show all/department visas if user has appropriate permissions (Admin Module)
        - Otherwise: Show only user's own visa applications (Personal Requests view)
        """
        from workflows.services import WorkflowApprovalHelper

        user = self.request.user
        queryset = self.queryset

        # For approval actions, allow access to applications pending the user's approval
        if self.action in ["approve", "reject"]:
            logger.info(
                " Approval action: Allowing access to all visa applications (authorization checked in WorkflowEngine)"
            )
            return queryset  # No filtering - authorization handled by WorkflowEngine

        # Every action below operates on ONE specific existing application
        # identified by pk in the URL (via self.get_object()) - they must
        # get the same view_all/superuser bypass as retrieve, else
        # get_object() 404s before the action even runs for anyone acting
        # on an application they didn't personally create - e.g. a visa
        # admin marking someone else's approved application as completed
        # from the Visa Processing admin page. None of these write-path
        # callers ever pass admin_view=true (that param only ever existed
        # for the list endpoint). See the matching fix in
        # transport/views.py's TransportRequestViewSet.get_queryset.
        if self.action in (
            "retrieve",
            "update",
            "partial_update",
            "destroy",
            "submit",
            "complete",
            "upload_passport",
            "delete_passport_file",
            "export_pdf",
        ):
            # Users with view_all_visa permission can access any application detail (e.g. from Recent Activity)
            if user.is_superuser or can_view_all(user, "visa"):
                logger.info(
                    " %s action: User has view_all_visa - allowing full access",
                    self.action,
                )
                return queryset
            pending_approval_ids = (
                WorkflowApprovalHelper.get_pending_entity_ids_for_user(
                    user, VisaApplication
                )
            )
            queryset = queryset.filter(Q(user=user) | Q(id__in=pending_approval_ids))
            logger.info(
                " %s action: Filtering to own applications and %s pending approval",
                self.action,
                len(pending_approval_ids),
            )
            return queryset

        # Check if this is an admin view (Visa Admin module)
        admin_view = (
            self.request.query_params.get("admin_view", "false").lower() == "true"
        )

        # Permission-based filtering
        if admin_view and (user.is_superuser or user.role):
            # Admin module context - check permissions
            if user.is_superuser or can_view_all(user, "visa"):
                logger.info(
                    f" Admin view: User {user.email or user.username} (role: {user.role.name if user.role else None}) has 'view_all_visa' permission - showing all visa applications"
                )
                pass  # No filtering - show all
            elif user.role.permissions.filter(
                name__in=["approve_visa", "view_pending_approvals"]
            ).exists():
                # Department-level approvers
                if user.department:
                    queryset = queryset.filter(user__department=user.department)
                    logger.info(
                        " Admin view: Approver - showing department visa applications"
                    )
                else:
                    queryset = queryset.filter(user=user)
                    logger.warning(
                        " Admin view: Approver but no department - showing only own"
                    )
            else:
                # No admin permissions - show only own plus pending approval
                pending_approval_ids = (
                    WorkflowApprovalHelper.get_pending_entity_ids_for_user(
                        user, VisaApplication
                    )
                )
                if pending_approval_ids:
                    queryset = queryset.filter(
                        Q(user=user) | Q(id__in=pending_approval_ids)
                    )
                    logger.info(
                        f" Admin view: User - showing own applications plus {len(pending_approval_ids)} pending approval"
                    )
                else:
                    queryset = queryset.filter(user=user)
                    logger.warning(
                        " Admin view: User lacks permission - showing only own visa applications"
                    )
        else:
            # Personal requests view - show user's own applications plus those pending their approval
            pending_approval_ids = (
                WorkflowApprovalHelper.get_pending_entity_ids_for_user(
                    user, VisaApplication
                )
            )
            if pending_approval_ids:
                queryset = queryset.filter(
                    Q(user=user) | Q(id__in=pending_approval_ids)
                )
                logger.info(
                    f" Personal view: User {user.email or user.username} - showing own applications plus {len(pending_approval_ids)} pending approval"
                )
            else:
                queryset = queryset.filter(user=user)
                logger.info(
                    f" Personal view: User {user.email or user.username} - showing only own visa applications"
                )

        # Apply status filter if provided
        status_filter = self.request.query_params.get("status", None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            logger.debug(f" Filtering by status: {status_filter}")

        # Apply search filter
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                Q(requestor_name__icontains=search)
                | Q(destination__icontains=search)
                | Q(passport_number__icontains=search)
                | Q(request_number__icontains=search)
                | Q(department__icontains=search)
                | Q(staff_id__icontains=search)
                | Q(user__email__icontains=search)
                | Q(user__name__icontains=search)
            )
            logger.debug(f" Searching for: {search}")

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "list":
            return VisaApplicationListSerializer
        elif self.action in ["create", "update", "partial_update"]:
            return VisaApplicationCreateUpdateSerializer
        return VisaApplicationDetailSerializer

    def create(self, request, *args, **kwargs):
        """Create a new visa application"""
        if not request.user.is_superuser and not has_permission(
            request.user, "create_visa"
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "You do not have permission to create visa applications."
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Set user and submitted_date when creating visa application"""
        # Get the status from validated data
        status_value = serializer.validated_data.get("status", "Draft")

        # Set submitted_date if status is not Draft
        extra_kwargs = {}
        if status_value != "Draft":
            extra_kwargs["submitted_date"] = timezone.now()

        # Generate request number if submitting (not Draft)
        if status_value not in ["Draft"]:
            try:
                request_number = generate_unique_visa_request_number(
                    destination=serializer.validated_data.get("destination", ""),
                    trip_start_date=serializer.validated_data.get("trip_start_date"),
                    applicant_name=serializer.validated_data.get("requestor_name", ""),
                )
                extra_kwargs["request_number"] = request_number
                logger.info(f" Generated request number: {request_number}")
            except Exception as e:
                logger.error(f" Error generating request number: {str(e)}")
                import traceback

                traceback.print_exc()

        # Save the visa application
        visa_application = serializer.save(user=self.request.user, **extra_kwargs)

        # Start workflow if status is submitted (not Draft)
        # Only check for 'Pending' or 'Submitted' since those are what frontend sends
        # Workflow will update status to dynamic values like 'Pending HOD' etc.
        if status_value in ["Pending", "Submitted"]:
            try:
                start_visa_workflow(
                    visa_application, self.request.data, self.request.user
                )
            except Exception as e:
                logger.error(
                    f" Error starting workflow for Visa Application #{visa_application.id}: {str(e)}"
                )
                import traceback

                traceback.print_exc()
                # Don't fail the request creation if workflow fails
                pass

    @action(detail=False, methods=["get"], url_path="pending-approvals")
    def pending_approvals(self, request):
        """Get visa applications pending approval for the current user based on workflow step assignments"""
        from workflows.services import WorkflowApprovalHelper

        user = request.user

        # Admins and superusers see all pending requests
        # Use startswith to match any workflow-generated 'Pending *' status
        if user.is_superuser or is_module_admin(user, "visa"):
            queryset = self.queryset.filter(
                Q(status__startswith="Pending")
                | Q(status="Submitted")
                | Q(status="Under Review")
            ).order_by("-submitted_date")
        else:
            # Use workflow-based filtering: get entities where user's role matches current step
            pending_ids = WorkflowApprovalHelper.get_pending_entity_ids_for_user(
                user, VisaApplication
            )
            queryset = self.queryset.filter(id__in=pending_ids).order_by(
                "-submitted_date"
            )

        serializer = VisaApplicationListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="my-applications")
    def my_applications(self, request):
        """Get current user's visa applications"""
        queryset = self.queryset.filter(user=request.user)
        serializer = VisaApplicationListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        """Approve a visa application using WorkflowEngine"""
        visa = self.get_object()
        step_role = request.data.get("step_role")
        comments = request.data.get("comments", "")

        result = process_visa_approval_action(
            visa, request, "approve", comments, step_role
        )
        if result is None:
            return None
        data, http_status = result
        return Response(data, status=http_status)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        """Reject a visa application using WorkflowEngine"""
        visa = self.get_object()
        step_role = request.data.get("step_role")
        comments = request.data.get("comments", "")

        result = process_visa_approval_action(
            visa, request, "reject", comments, step_role
        )
        if result is None:
            return None
        data, http_status = result
        return Response(data, status=http_status)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        """Mark visa application as completed after processing"""
        visa = self.get_object()

        # complete() had no internal permission check at all - the queryset
        # bypass above lets an application's own applicant reach this via
        # Q(user=user) (that's correct for retrieve/submit/export_pdf, which
        # share the same bypass tuple), but completing is an admin/processing
        # action, not something the applicant should be able to do to their
        # own approved application. Mirrors transport's complete(), which
        # already requires is_module_admin - see docs/
        # RBAC_AND_ADMIN_ACCESS_FIX_ROADMAP.md Fix 5. Confirmed no
        # applicant-facing frontend page calls this endpoint today (only
        # visa-processing.component.ts / visa-admin.component.ts, both
        # under features/admin/visa/).
        if not (request.user.is_superuser or is_module_admin(request.user, "visa")):
            return error_response(
                message="Only visa admin can mark applications as completed.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # If already completed, just return success with current data
        if visa.status == "Completed":
            serializer = VisaApplicationDetailSerializer(visa)
            return Response(serializer.data)

        # Validate that visa is in a processable status
        valid_statuses = ["Approved", "Processing", "Processing with Visa Clerk"]
        if visa.status not in valid_statuses:
            return Response(
                {
                    "error": f'Cannot complete visa with status "{visa.status}". Only visas with status {", ".join(valid_statuses)} can be marked as completed.'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update visa status and processing details
        visa.status = "Completed"
        visa.processing_completed_at = timezone.now()
        visa.processing_completed_by = request.user

        # Update processing details if provided
        if "processing_details" in request.data:
            visa.processing_details = request.data["processing_details"]

        if "additional_comments" in request.data:
            visa.additional_comments = request.data["additional_comments"]

        visa.save()

        finalize_visa_workflow_completion(visa, completed_by=request.user)

        serializer = VisaApplicationDetailSerializer(visa)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        """
        Submit a visa application for approval.
        Changes status from Draft to Pending and starts workflow.
        This endpoint properly returns the updated status after workflow starts.
        """
        visa = self.get_object()

        # Validate status
        if visa.status != "Draft":
            return Response(
                {
                    "error": f"Cannot submit visa application with status {visa.status}. Only Draft applications can be submitted."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate request number if it doesn't exist
        if not visa.request_number:
            try:
                request_number = generate_unique_visa_request_number(
                    destination=visa.destination,
                    trip_start_date=visa.trip_start_date,
                    applicant_name=visa.requestor_name,
                )
                visa.request_number = request_number
                logger.info(f" Generated request number: {request_number}")
            except Exception as e:
                logger.error(f" Error generating request number: {str(e)}")
                # Fallback to simple format
                visa.request_number = (
                    f"VIS-{datetime.now().strftime('%Y%m%d-%H%M')}-VIS-{visa.id}"
                )

        # Set submitted date
        visa.submitted_date = timezone.now()
        visa.status = "Pending"  # Initial status before workflow updates it
        visa.save()

        # Start workflow
        try:
            start_visa_workflow(visa, request.data, request.user)
        except Exception as e:
            logger.error(f" Error starting workflow for Visa #{visa.id}: {str(e)}")
            import traceback

            traceback.print_exc()
            # Don't fail - visa is already saved with Pending status

        # Return fresh serialized data with updated status
        serializer = VisaApplicationDetailSerializer(visa, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="upload-passport")
    def upload_passport(self, request, pk=None):
        """
        Upload or update passport file for an existing visa application.
        Accepts multipart/form-data with 'passport_file' field.
        """
        visa = self.get_object()

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
        if visa.passport_file:
            visa.passport_file.delete(save=False)

        # Save new file
        visa.passport_file = passport_file
        visa.save()

        serializer = VisaApplicationDetailSerializer(visa, context={"request": request})
        return success_response(
            data=serializer.data,
            message="Passport file uploaded successfully",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"], url_path="delete-passport-file")
    def delete_passport_file(self, request, pk=None):
        """Delete the passport file from an existing visa application."""
        visa = self.get_object()

        if not visa.passport_file:
            return error_response(
                message="No passport file to delete",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Delete the file
        visa.passport_file.delete(save=True)

        serializer = VisaApplicationDetailSerializer(visa, context={"request": request})
        return success_response(
            data=serializer.data,
            message="Passport file deleted successfully",
            status_code=status.HTTP_200_OK,
        )

    def perform_update(self, serializer):
        """Update submitted_date when status changes from Draft and start workflow"""
        instance = serializer.instance
        old_status = instance.status
        new_status = serializer.validated_data.get("status", old_status)

        # Set submitted_date if changing from Draft and not already set
        extra_kwargs = {}
        if (
            old_status == "Draft"
            and new_status != "Draft"
            and not instance.submitted_date
        ):
            extra_kwargs["submitted_date"] = timezone.now()

        # Generate request number if transitioning from Draft and doesn't have one
        if (
            old_status == "Draft"
            and new_status not in ["Draft"]
            and not instance.request_number
        ):
            try:
                request_number = generate_unique_visa_request_number(
                    destination=serializer.validated_data.get(
                        "destination", instance.destination
                    ),
                    trip_start_date=serializer.validated_data.get(
                        "trip_start_date", instance.trip_start_date
                    ),
                    applicant_name=instance.requestor_name,
                )
                extra_kwargs["request_number"] = request_number
                logger.info(f" Generated request number: {request_number}")
            except Exception as e:
                logger.error(f" Error generating request number: {str(e)}")
                import traceback

                traceback.print_exc()
                # Fallback to simple format
                extra_kwargs["request_number"] = (
                    f"VIS-{datetime.now().strftime('%Y%m%d-%H%M')}-VIS-{instance.id}"
                )
                logger.warning(
                    f" Using fallback request number: {extra_kwargs['request_number']}"
                )

        # Save the visa application
        visa_application = serializer.save(**extra_kwargs)

        # Start workflow if transitioning from Draft to submitted status
        # Only check for 'Pending' or 'Submitted' since those are what frontend sends
        if old_status == "Draft" and new_status in ["Pending", "Submitted"]:
            try:
                start_visa_workflow(
                    visa_application, self.request.data, self.request.user
                )
            except Exception as e:
                logger.error(
                    f" Error starting workflow for Visa Application #{visa_application.id}: {str(e)}"
                )
                import traceback

                traceback.print_exc()
                pass

        # Handle status change to Completed. Now shares the same completion
        # side effects (notify_processing_completed + linked-TRF
        # department-focal notification) as the dedicated `complete` action
        # - see finalize_visa_workflow_completion's docstring for why this
        # previously silently skipped both.
        if old_status == "Approved" and new_status == "Completed":
            finalize_visa_workflow_completion(
                visa_application, completed_by=self.request.user
            )

    def perform_destroy(self, instance):
        """Log deletion before removing the record, since nothing else audits this."""
        AdminActionLog.log_action(
            user=self.request.user,
            action_type="entity_deleted",
            description=f"Deleted Visa Application #{instance.id} ({instance.request_number or 'no request number'})",
            entity_type="visaapplication",
            entity_id=str(instance.id),
            request=self.request,
        )
        super().perform_destroy(instance)

    @action(detail=True, methods=["get"], url_path="export-pdf")
    def export_pdf(self, request, pk=None):
        """Export Visa Application to PDF - see visa/pdf_export.py"""
        from .pdf_export import build_request_pdf

        visa = self.get_object()
        return build_request_pdf(visa)
