import logging

from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from datetime import datetime

from accounts.utils import can_approve, can_view_all, has_permission
from utils import error_response, not_found_response, success_response
from utils.request_id_generator import generate_request_id
from workflows.router import WorkflowRouter

from .models import VisaApplication, VisaApprovalStep, VisaDocument
from .serializers import (
    VisaApplicationCreateUpdateSerializer,
    VisaApplicationDetailSerializer,
    VisaApplicationListSerializer,
    VisaApprovalStepSerializer,
    VisaDocumentSerializer,
)


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

        # For retrieve (viewing details), check view_all permission first, then pending approvals
        if self.action == "retrieve":
            # Users with view_all_visa permission can access any application detail (e.g. from Recent Activity)
            if can_view_all(user, "visa"):
                logger.info(
                    " Retrieve action: User has view_all_visa - allowing full access"
                )
                return queryset
            pending_approval_ids = (
                WorkflowApprovalHelper.get_pending_entity_ids_for_user(
                    user, VisaApplication
                )
            )
            queryset = queryset.filter(Q(user=user) | Q(id__in=pending_approval_ids))
            logger.info(
                f" Retrieve action: Filtering to own applications and {len(pending_approval_ids)} pending approval"
            )
            return queryset

        # Check if this is an admin view (Visa Admin module)
        admin_view = (
            self.request.query_params.get("admin_view", "false").lower() == "true"
        )

        # Permission-based filtering
        if admin_view and user.role:
            # Admin module context - check permissions
            if can_view_all(user, "visa"):
                logger.info(
                    f" Admin view: User {user.email or user.username} (role: {user.role.name}) has 'view_all_visa' permission - showing all visa applications"
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
        from django.utils import timezone

        # Get the status from validated data
        status_value = serializer.validated_data.get("status", "Draft")

        # Set submitted_date if status is not Draft
        extra_kwargs = {}
        if status_value != "Draft":
            extra_kwargs["submitted_date"] = timezone.now()

        # Generate request number if submitting (not Draft)
        if status_value not in ["Draft"]:
            try:
                # Extract context from destination field
                destination = serializer.validated_data.get("destination", "")
                context = (
                    destination if destination else "VIS"
                )  # Let generate_request_id handle validation

                logger.debug(f" Extracted context for Visa Application: {context}")

                # Generate unique request number (will auto-validate and limit context to 5 chars)
                request_number = generate_request_id("VIS", context)
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
            # Extract selected approvers from request data (optional)
            selected_approvers = self.request.data.get("selected_approvers", None)
            logger.info(
                f" Visa #{visa_application.id} - Raw selected_approvers from request: {selected_approvers}"
            )
            if selected_approvers:
                selected_approvers = {int(k): v for k, v in selected_approvers.items()}
                logger.info(
                    f" Visa #{visa_application.id} - Parsed selected_approvers: {selected_approvers}"
                )

            # Extract skipped steps from request data (optional)
            skipped_steps = self.request.data.get("skipped_steps", None)
            logger.info(
                f" Visa #{visa_application.id} - Raw skipped_steps from request: {skipped_steps}"
            )
            if skipped_steps:
                skipped_steps = {int(k): v for k, v in skipped_steps.items()}
                logger.info(
                    f" Visa #{visa_application.id} - Parsed skipped_steps: {skipped_steps}"
                )

            try:
                logger.info(
                    f" Starting workflow for Visa #{visa_application.id} with selected_approvers={selected_approvers}, skipped_steps={skipped_steps}"
                )
                workflow_instance = WorkflowRouter.start_workflow_for_request(
                    entity=visa_application,
                    entity_type="visaapplication",
                    initiated_by=self.request.user,
                    selected_approvers=selected_approvers,
                    skipped_steps=skipped_steps,
                )

                if workflow_instance:
                    # Reload the visa application to get the updated status from workflow
                    visa_application.refresh_from_db()
                    logger.info(
                        f" Workflow started for Visa Application #{visa_application.id}: Workflow Instance #{workflow_instance.id}"
                    )
                    logger.info(f" Status updated to: {visa_application.status}")
                else:
                    logger.warning(
                        " No active workflow configured for visaapplication - using legacy approval system"
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
        from accounts.utils import is_module_admin
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
        from django.contrib.contenttypes.models import ContentType
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance

        visa = self.get_object()
        step_role = request.data.get("step_role")
        comments = request.data.get("comments", "")

        try:
            # Get the workflow instance for this visa
            content_type = ContentType.objects.get_for_model(visa)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type, object_id=visa.id, status="in_progress"
            ).first()

            if workflow_instance:
                # Find the current pending step
                current_step = (
                    workflow_instance.step_executions.filter(status="pending")
                    .order_by("workflow_step__step_order")
                    .first()
                )

                if current_step:
                    # Use workflow engine to process approval
                    WorkflowEngine.process_action(
                        step_execution_id=current_step.id,
                        action="approve",
                        actioned_by=request.user,
                        comments=comments,
                    )

                    # Reload to get updated status
                    visa.refresh_from_db()

                    # Update legacy approval step for backward compatibility
                    approval_step, created = VisaApprovalStep.objects.get_or_create(
                        visa=visa,
                        step_role=step_role,
                        defaults={
                            "step_name": f"{step_role} Approval",
                            "status": "Approved",
                            "comments": comments,
                        },
                    )
                    if not created:
                        approval_step.status = "Approved"
                        approval_step.comments = comments
                        approval_step.save()

                    serializer = VisaApplicationDetailSerializer(visa)
                    return Response(serializer.data)
                else:
                    return Response(
                        {"error": "No pending approval step found"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                # Fallback to legacy approval logic
                if not (request.user.is_superuser or can_approve(request.user, "visa")):
                    return Response(
                        {
                            "error": "You do not have permission to approve visa applications"
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

                logger.warning(
                    f" No workflow instance found for Visa #{visa.id}, using legacy approval"
                )

                approval_step, created = VisaApprovalStep.objects.get_or_create(
                    visa=visa,
                    step_role=step_role,
                    defaults={
                        "step_name": f"{step_role} Approval",
                        "status": "Approved",
                        "comments": comments,
                    },
                )

                if not created:
                    approval_step.status = "Approved"
                    approval_step.comments = comments
                    approval_step.save()

                status_map = {"Department Focal": "Pending HOD", "HOD": "Approved"}
                visa.status = status_map.get(step_role, visa.status)
                visa.save()

                serializer = VisaApplicationDetailSerializer(visa)
                return Response(serializer.data)

        except Exception as e:
            logger.error(f" Error in approve workflow: {str(e)}")
            import traceback

            traceback.print_exc()
            return Response(
                {"error": f"Failed to process approval: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        """Reject a visa application using WorkflowEngine"""
        from django.contrib.contenttypes.models import ContentType
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance

        visa = self.get_object()
        step_role = request.data.get("step_role")
        comments = request.data.get("comments", "")

        try:
            content_type = ContentType.objects.get_for_model(visa)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type, object_id=visa.id, status="in_progress"
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

                    visa.refresh_from_db()

                    approval_step, created = VisaApprovalStep.objects.get_or_create(
                        visa=visa,
                        step_role=step_role,
                        defaults={
                            "step_name": f"{step_role} Approval",
                            "status": "Rejected",
                            "comments": comments,
                        },
                    )
                    if not created:
                        approval_step.status = "Rejected"
                        approval_step.comments = comments
                        approval_step.save()

                    serializer = VisaApplicationDetailSerializer(visa)
                    return Response(serializer.data)
            else:
                # Fallback to legacy rejection
                if not (request.user.is_superuser or can_approve(request.user, "visa")):
                    return Response(
                        {
                            "error": "You do not have permission to reject visa applications"
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

                approval_step, created = VisaApprovalStep.objects.get_or_create(
                    visa=visa,
                    step_role=step_role,
                    defaults={
                        "step_name": f"{step_role} Approval",
                        "status": "Rejected",
                        "comments": comments,
                    },
                )

                if not created:
                    approval_step.status = "Rejected"
                    approval_step.comments = comments
                    approval_step.save()

                visa.status = "Rejected"
                visa.save()

                serializer = VisaApplicationDetailSerializer(visa)
                return Response(serializer.data)

        except Exception as e:
            logger.error(f" Error in reject workflow: {str(e)}")
            import traceback

            traceback.print_exc()
            return Response(
                {"error": f"Failed to process rejection: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        """Mark visa application as completed after processing"""
        from django.contrib.contenttypes.models import ContentType
        from workflows.models import WorkflowInstance

        visa = self.get_object()

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

        # Update processing details if provided
        if "processing_details" in request.data:
            visa.processing_details = request.data["processing_details"]

        if "additional_comments" in request.data:
            visa.additional_comments = request.data["additional_comments"]

        visa.save()

        # Update workflow instance status to completed
        try:
            content_type = ContentType.objects.get_for_model(visa)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type, object_id=visa.id, status="approved"
            ).first()

            if workflow_instance:
                workflow_instance.status = "completed"
                workflow_instance.save()
                logger.info(
                    f" Workflow instance #{workflow_instance.id} marked as completed for Visa #{visa.id}"
                )
            else:
                logger.warning(
                    f" No approved workflow instance found for Visa #{visa.id}"
                )
        except Exception as e:
            logger.warning(f" Error updating workflow instance: {str(e)}")
            # Don't fail the completion if workflow update fails

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
                destination = visa.destination or "VIS"
                request_number = generate_request_id("VIS", destination)
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

        # Extract selected approvers from request data (optional)
        selected_approvers = request.data.get("selected_approvers", None)
        if selected_approvers:
            selected_approvers = {int(k): v for k, v in selected_approvers.items()}
            logger.info(
                f" Visa #{visa.id} SUBMIT - Parsed selected_approvers: {selected_approvers}"
            )

        # Extract skipped steps from request data (optional)
        skipped_steps = request.data.get("skipped_steps", None)
        if skipped_steps:
            skipped_steps = {int(k): v for k, v in skipped_steps.items()}
            logger.info(
                f" Visa #{visa.id} SUBMIT - Parsed skipped_steps: {skipped_steps}"
            )

        # Start workflow
        try:
            logger.info(
                f" Starting workflow for Visa #{visa.id} with selected_approvers={selected_approvers}, skipped_steps={skipped_steps}"
            )
            workflow_instance = WorkflowRouter.start_workflow_for_request(
                entity=visa,
                entity_type="visaapplication",
                initiated_by=request.user,
                selected_approvers=selected_approvers,
                skipped_steps=skipped_steps,
            )

            if workflow_instance:
                # Reload to get updated status from workflow
                visa.refresh_from_db()
                logger.info(
                    f" Workflow started for Visa #{visa.id}: Instance #{workflow_instance.id}, Status: {visa.status}"
                )
            else:
                logger.warning(" No active workflow configured for visaapplication")
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
        from django.utils import timezone

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
                # Extract context from destination field
                destination = serializer.validated_data.get(
                    "destination", instance.destination
                )
                context = (
                    destination if destination else "VIS"
                )  # Let generate_request_id handle validation

                logger.debug(
                    f" Extracted context for Visa Application #{instance.id}: {context}"
                )

                # Generate unique request number (will auto-validate and limit context to 5 chars)
                request_number = generate_request_id("VIS", context)
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
            # Extract selected approvers from request data (optional)
            selected_approvers = self.request.data.get("selected_approvers", None)
            logger.info(
                f" Visa #{visa_application.id} UPDATE - Raw selected_approvers: {selected_approvers}"
            )
            if selected_approvers:
                selected_approvers = {int(k): v for k, v in selected_approvers.items()}
                logger.info(
                    f" Visa #{visa_application.id} UPDATE - Parsed selected_approvers: {selected_approvers}"
                )

            # Extract skipped steps from request data (optional)
            skipped_steps = self.request.data.get("skipped_steps", None)
            logger.info(
                f" Visa #{visa_application.id} UPDATE - Raw skipped_steps: {skipped_steps}"
            )
            if skipped_steps:
                skipped_steps = {int(k): v for k, v in skipped_steps.items()}
                logger.info(
                    f" Visa #{visa_application.id} UPDATE - Parsed skipped_steps: {skipped_steps}"
                )

            try:
                logger.info(
                    f" Starting workflow for Visa #{visa_application.id} with selected_approvers={selected_approvers}, skipped_steps={skipped_steps}"
                )
                workflow_instance = WorkflowRouter.start_workflow_for_request(
                    entity=visa_application,
                    entity_type="visaapplication",
                    initiated_by=self.request.user,
                    selected_approvers=selected_approvers,
                    skipped_steps=skipped_steps,
                )

                if workflow_instance:
                    visa_application.refresh_from_db()
                    logger.info(
                        f" Workflow started for Visa Application #{visa_application.id}: Workflow Instance #{workflow_instance.id}"
                    )
                    logger.info(f" Status after workflow: {visa_application.status}")
                else:
                    logger.warning(" No active workflow configured for visaapplication")
            except Exception as e:
                logger.error(
                    f" Error starting workflow for Visa Application #{visa_application.id}: {str(e)}"
                )
                import traceback

                traceback.print_exc()
                pass

        # Handle status change to Completed
        if old_status == "Approved" and new_status == "Completed":
            from django.contrib.contenttypes.models import ContentType
            from workflows.models import WorkflowInstance

            try:
                content_type = ContentType.objects.get_for_model(visa_application)
                workflow_instance = WorkflowInstance.objects.filter(
                    content_type=content_type,
                    object_id=visa_application.id,
                    status="approved",
                ).first()

                if workflow_instance:
                    workflow_instance.status = "completed"
                    workflow_instance.save()
                    logger.info(
                        f" Workflow instance #{workflow_instance.id} marked as completed for Visa #{visa_application.id}"
                    )
                else:
                    logger.warning(
                        f" No approved workflow instance found for Visa #{visa_application.id}"
                    )
            except Exception as e:
                logger.warning(
                    f" Error updating workflow instance on completion: {str(e)}"
                )
                # Don't fail the update if workflow update fails

    @action(detail=True, methods=["get"], url_path="export-pdf")
    def export_pdf(self, request, pk=None):
        """
        Export Visa Application to PDF

        Returns a PDF document containing all visa application details including:
        - Applicant information
        - Travel details
        - Passport information
        - Visa type and entry details
        - Approval history and workflow status
        """
        import io

        from django.http import HttpResponse
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        visa = self.get_object()

        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
        )

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=18,
            spaceAfter=20,
            textColor=colors.HexColor("#0d9488"),
        )
        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            fontSize=12,
            spaceBefore=15,
            spaceAfter=10,
            textColor=colors.HexColor("#0d9488"),
        )
        normal_style = styles["Normal"]

        elements = []

        # Title
        title = f"Visa Application - {visa.request_number or f'VISA-{visa.id}'}"
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 12))

        # Status badge
        status_text = f"<b>Status:</b> {visa.status}"
        elements.append(Paragraph(status_text, normal_style))
        elements.append(Spacer(1, 12))

        # Table style
        table_style = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d9488")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )

        # Applicant Information
        elements.append(Paragraph("Applicant Information", heading_style))
        applicant_data = [
            ["Field", "Value"],
            ["Name", visa.requestor_name or "Not provided"],
            ["Staff ID", visa.staff_id or "Not provided"],
            ["Department", visa.department or "Not provided"],
            ["Position", visa.position or "Not provided"],
            ["Email", visa.email or (visa.user.email if visa.user else "Not provided")],
            ["Contact Telephone", visa.contact_telephone or "Not provided"],
            ["Home Address", (visa.home_address or "Not provided")[:80]],
        ]
        applicant_table = Table(applicant_data, colWidths=[2 * inch, 5 * inch])
        applicant_table.setStyle(table_style)
        elements.append(applicant_table)

        # Status & Tracking
        elements.append(Paragraph("Status &amp; Tracking", heading_style))
        tracking_data = [
            ["Field", "Value"],
            ["Request Number", visa.request_number or f"VISA-{visa.id}"],
            ["Current Status", visa.status],
            ["TRF Reference", visa.trf_reference_number or "Not linked"],
            [
                "Created",
                (
                    visa.created_at.strftime("%Y-%m-%d %H:%M")
                    if visa.created_at
                    else "Not available"
                ),
            ],
            [
                "Submitted",
                (
                    visa.submitted_date.strftime("%Y-%m-%d %H:%M")
                    if visa.submitted_date
                    else "Not submitted"
                ),
            ],
            [
                "Processing Started",
                (
                    visa.processing_started_at.strftime("%Y-%m-%d %H:%M")
                    if visa.processing_started_at
                    else "Not started"
                ),
            ],
            [
                "Processing Completed",
                (
                    visa.processing_completed_at.strftime("%Y-%m-%d %H:%M")
                    if visa.processing_completed_at
                    else "Not completed"
                ),
            ],
            [
                "Last Updated",
                (
                    visa.updated_at.strftime("%Y-%m-%d %H:%M")
                    if visa.updated_at
                    else "Not available"
                ),
            ],
        ]
        tracking_table = Table(tracking_data, colWidths=[2 * inch, 5 * inch])
        tracking_table.setStyle(table_style)
        elements.append(tracking_table)

        # Travel Details
        elements.append(Paragraph("Travel Details", heading_style))
        travel_data = [
            ["Field", "Value"],
            ["Destination", visa.destination or "-"],
            ["Travel Purpose", visa.travel_purpose or "-"],
            [
                "Trip Start Date",
                (
                    visa.trip_start_date.strftime("%Y-%m-%d")
                    if visa.trip_start_date
                    else "-"
                ),
            ],
            [
                "Trip End Date",
                visa.trip_end_date.strftime("%Y-%m-%d") if visa.trip_end_date else "-",
            ],
            [
                "Approximate Arrival",
                (
                    visa.approximately_arrival_date.strftime("%Y-%m-%d")
                    if visa.approximately_arrival_date
                    else "-"
                ),
            ],
            ["Duration of Stay", visa.duration_of_stay or "-"],
            ["Itinerary Details", (visa.itinerary_details or "-")[:100]],
        ]
        travel_table = Table(travel_data, colWidths=[2 * inch, 5 * inch])
        travel_table.setStyle(table_style)
        elements.append(travel_table)

        # Visa Information
        elements.append(Paragraph("Visa Information", heading_style))
        visa_info_data = [
            ["Field", "Value"],
            ["Visa Type", visa.visa_type or "-"],
            ["Visa Entry Type", visa.visa_entry_type or "-"],
            ["Request Type", visa.request_type or "-"],
            ["Work Visit Category", visa.work_visit_category or "-"],
            ["Application Fees Borne By", visa.application_fees_borne_by or "-"],
            ["Cost Centre Number", visa.cost_centre_number or "-"],
            ["TRF Reference Number", visa.trf_reference_number or "-"],
        ]
        visa_info_table = Table(visa_info_data, colWidths=[2 * inch, 5 * inch])
        visa_info_table.setStyle(table_style)
        elements.append(visa_info_table)

        # Passport Details
        elements.append(Paragraph("Passport Details", heading_style))
        passport_data = [
            ["Field", "Value"],
            ["Passport Number", visa.passport_number or "-"],
            [
                "Date of Issuance",
                (
                    visa.passport_date_of_issuance.strftime("%Y-%m-%d")
                    if visa.passport_date_of_issuance
                    else "-"
                ),
            ],
            ["Place of Issuance", visa.passport_place_of_issuance or "-"],
            [
                "Expiry Date",
                (
                    visa.passport_expiry_date.strftime("%Y-%m-%d")
                    if visa.passport_expiry_date
                    else "-"
                ),
            ],
        ]
        passport_table = Table(passport_data, colWidths=[2 * inch, 5 * inch])
        passport_table.setStyle(table_style)
        elements.append(passport_table)

        # Personal Demographics
        elements.append(Paragraph("Personal Demographics", heading_style))
        personal_data = [
            ["Field", "Value"],
            [
                "Date of Birth",
                visa.date_of_birth.strftime("%Y-%m-%d") if visa.date_of_birth else "-",
            ],
            ["Place of Birth", visa.place_of_birth or "-"],
            ["Citizenship", visa.citizenship or "-"],
            ["Marital Status", visa.marital_status or "-"],
            ["Family Information", (visa.family_information or "-")[:80]],
            ["Education Details", (visa.education_details or "-")[:80]],
        ]
        personal_table = Table(personal_data, colWidths=[2 * inch, 5 * inch])
        personal_table.setStyle(table_style)
        elements.append(personal_table)

        # Employment Information
        if visa.current_employer_name or visa.current_employer_address:
            elements.append(Paragraph("Employment Information", heading_style))
            employer_data = [
                ["Field", "Value"],
                ["Employer Name", visa.current_employer_name or "-"],
                ["Employer Address", (visa.current_employer_address or "-")[:80]],
            ]
            employer_table = Table(employer_data, colWidths=[2 * inch, 5 * inch])
            employer_table.setStyle(table_style)
            elements.append(employer_table)

        # Processing Details - format as table if available
        if visa.processing_details and isinstance(visa.processing_details, dict):
            elements.append(Paragraph("Processing Details", heading_style))
            processing_data = [["Field", "Value"]]
            # Map field names to readable labels
            field_labels = {
                "visa_number": "Visa Number",
                "visa_valid_from": "Valid From",
                "visa_valid_to": "Valid To",
                "completed_at": "Completed At",
                "processing_notes": "Processing Notes",
                "completed_by_admin": "Completed by Admin",
            }
            for key, value in visa.processing_details.items():
                label = field_labels.get(key, key.replace("_", " ").title())
                # Format boolean values
                if isinstance(value, bool):
                    value = "Yes" if value else "No"
                processing_data.append([label, str(value)[:80] if value else "-"])
            processing_table = Table(processing_data, colWidths=[2 * inch, 5 * inch])
            processing_table.setStyle(table_style)
            elements.append(processing_table)

        # Approval History - try workflow first, then fall back to legacy approval steps
        from django.contrib.contenttypes.models import ContentType
        from workflows.models import WorkflowInstance

        approval_found = False

        # Try workflow-based approval history
        try:
            content_type = ContentType.objects.get_for_model(visa)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type, object_id=visa.id
            ).first()

            if workflow_instance and workflow_instance.step_executions.exists():
                # Build table first, then add heading only if successful
                approval_data = [
                    ["Step", "Role", "Status", "Actioned By", "Date", "Comments"]
                ]
                for step in workflow_instance.step_executions.all().order_by(
                    "step_order"
                ):
                    approval_data.append(
                        [
                            str(step.step_order),
                            step.step_name or step.role_required or "-",
                            step.status or "-",
                            step.actioned_by.name if step.actioned_by else "-",
                            (
                                step.actioned_at.strftime("%Y-%m-%d %H:%M")
                                if step.actioned_at
                                else "-"
                            ),
                            (step.comments or "-")[:30],
                        ]
                    )
                # Only add if we have actual data rows (more than just header)
                if len(approval_data) > 1:
                    elements.append(Paragraph("Approval History", heading_style))
                    approval_table = Table(
                        approval_data,
                        colWidths=[
                            0.4 * inch,
                            1.2 * inch,
                            0.9 * inch,
                            1.2 * inch,
                            1.3 * inch,
                            2 * inch,
                        ],
                    )
                    approval_table.setStyle(table_style)
                    elements.append(approval_table)
                    approval_found = True
        except Exception:
            pass

        # Fall back to legacy approval steps if no workflow found
        if not approval_found:
            approval_steps = visa.visaapprovalstep_set.all().order_by("created_at")
            if approval_steps.exists():
                elements.append(Paragraph("Approval History", heading_style))
                approval_data = [["Role", "Status", "Date", "Comments"]]
                for step in approval_steps:
                    approval_data.append(
                        [
                            step.step_role or "-",
                            step.status or "-",
                            (
                                step.step_date.strftime("%Y-%m-%d %H:%M")
                                if step.step_date
                                else "-"
                            ),
                            (step.comments or "-")[:50],
                        ]
                    )
                approval_table = Table(
                    approval_data,
                    colWidths=[1.5 * inch, 1.2 * inch, 1.5 * inch, 3 * inch],
                )
                approval_table.setStyle(table_style)
                elements.append(approval_table)

        # Additional Comments
        if visa.additional_comments:
            elements.append(Paragraph("Additional Comments", heading_style))
            elements.append(Paragraph(visa.additional_comments[:500], normal_style))

        # Footer
        elements.append(Spacer(1, 20))
        footer_style = ParagraphStyle(
            "Footer", parent=styles["Normal"], fontSize=8, textColor=colors.grey
        )
        footer_text = f"Generated on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')} | Travel Management System"
        elements.append(Paragraph(footer_text, footer_style))

        # Build PDF
        doc.build(elements)
        buffer.seek(0)

        # Create response
        filename = f"Visa-{visa.request_number or visa.id}.pdf"
        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class VisaApprovalStepViewSet(viewsets.ModelViewSet):
    """ViewSet for visa approval steps"""

    queryset = VisaApprovalStep.objects.all().order_by("step_date")
    serializer_class = VisaApprovalStepSerializer
    permission_classes = [IsAuthenticated]


class VisaDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for visa documents"""

    queryset = VisaDocument.objects.all().order_by("-uploaded_at")
    serializer_class = VisaDocumentSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="by-visa/(?P<visa_id>[^/.]+)")
    def by_visa(self, request, visa_id=None):
        """Get all documents for a specific visa application"""
        documents = self.queryset.filter(visa_id=visa_id)
        serializer = self.get_serializer(documents, many=True)
        return Response(serializer.data)
