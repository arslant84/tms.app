from accounts.utils import can_manage, has_any_permission
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from utils import error_response, success_response

from .engine import WorkflowEngine
from .models import (
    WorkflowAuditLog,
    WorkflowCondition,
    WorkflowDelegation,
    WorkflowInstance,
    WorkflowStep,
    WorkflowStepExecution,
    WorkflowTemplate,
)
from .serializers import (
    WorkflowActionSerializer,
    WorkflowAuditLogSerializer,
    WorkflowConditionSerializer,
    WorkflowDelegationSerializer,
    WorkflowInstanceCreateSerializer,
    WorkflowInstanceDetailSerializer,
    WorkflowInstanceSerializer,
    WorkflowStepExecutionSerializer,
    WorkflowStepSerializer,
    WorkflowTemplateCreateSerializer,
    WorkflowTemplateDetailSerializer,
    WorkflowTemplateSerializer,
)


class WorkflowTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing workflow templates
    Admin only - templates define reusable workflows
    """

    queryset = WorkflowTemplate.objects.all()
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        """Filter templates by entity type and status"""
        queryset = super().get_queryset()

        entity_type = self.request.query_params.get("entity_type", None)
        if entity_type:
            queryset = queryset.filter(entity_type__iexact=entity_type)

        is_active = self.request.query_params.get("is_active", None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset.prefetch_related("steps", "steps__conditions")

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "retrieve":
            return WorkflowTemplateDetailSerializer
        elif self.action in ["create", "update", "partial_update"]:
            return WorkflowTemplateCreateSerializer
        return WorkflowTemplateSerializer

    def perform_create(self, serializer):
        """Set creator when creating template"""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """Duplicate a workflow template with all steps"""
        original = self.get_object()

        # Create duplicate template
        duplicate = WorkflowTemplate.objects.create(
            name=f"{original.name} (Copy)",
            description=original.description,
            entity_type=original.entity_type,
            is_active=False,  # Start as inactive
            allow_parallel_steps=original.allow_parallel_steps,
            auto_approve_on_condition=original.auto_approve_on_condition,
            created_by=request.user,
        )

        # Duplicate all steps
        for step in original.steps.all():
            new_step = WorkflowStep.objects.create(
                workflow_template=duplicate,
                step_order=step.step_order,
                step_name=step.step_name,
                step_description=step.step_description,
                approver_role=step.approver_role,
                approver_user=step.approver_user,
                is_required=step.is_required,
                can_skip=step.can_skip,
                requires_comments=step.requires_comments,
                sla_hours=step.sla_hours,
            )

            # Duplicate conditions
            for condition in step.conditions.all():
                WorkflowCondition.objects.create(
                    workflow_step=new_step,
                    condition_type=condition.condition_type,
                    field_name=condition.field_name,
                    field_value=condition.field_value,
                    logical_operator=condition.logical_operator,
                    is_active=condition.is_active,
                )

        serializer = WorkflowTemplateDetailSerializer(duplicate)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class WorkflowStepViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing workflow steps
    Admin only - steps define the approval stages
    """

    queryset = WorkflowStep.objects.all()
    serializer_class = WorkflowStepSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        """Filter steps by template"""
        queryset = super().get_queryset()

        template_id = self.request.query_params.get("template", None)
        if template_id:
            queryset = queryset.filter(workflow_template_id=template_id)

        return queryset.select_related(
            "workflow_template", "approver_user"
        ).prefetch_related("conditions")


class WorkflowConditionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing workflow conditions
    Admin only - conditions determine when steps execute
    """

    queryset = WorkflowCondition.objects.all()
    serializer_class = WorkflowConditionSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        """Filter conditions by step"""
        queryset = super().get_queryset()

        step_id = self.request.query_params.get("step", None)
        if step_id:
            queryset = queryset.filter(workflow_step_id=step_id)

        return queryset.select_related("workflow_step")


class WorkflowInstanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing workflow instances
    Tracks active workflows for entities
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter instances based on user role and permissions"""
        user = self.request.user
        queryset = WorkflowInstance.objects.all()

        # Users with workflow management permission see all
        is_workflow_admin = user.is_superuser or can_manage(user, "workflow")
        if not is_workflow_admin:
            # Regular users see instances they initiated or have pending approvals
            queryset = queryset.filter(
                Q(initiated_by=user)
                | Q(
                    step_executions__assigned_to=user, step_executions__status="pending"
                )
            ).distinct()

        # Filter by status
        status_filter = self.request.query_params.get("status", None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by entity type
        entity_type = self.request.query_params.get("entity_type", None)
        if entity_type:
            queryset = queryset.filter(
                workflow_template__entity_type__iexact=entity_type
            )

        # Filter by template
        template_id = self.request.query_params.get("template", None)
        if template_id:
            queryset = queryset.filter(workflow_template_id=template_id)

        # Filter by object_id
        object_id = self.request.query_params.get("object_id", None)
        if object_id:
            queryset = queryset.filter(object_id=object_id)

        return queryset.select_related(
            "workflow_template", "content_type", "initiated_by"
        ).prefetch_related("step_executions", "step_executions__workflow_step")

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "retrieve":
            return WorkflowInstanceDetailSerializer
        elif self.action == "create":
            return WorkflowInstanceCreateSerializer
        return WorkflowInstanceSerializer

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """
        Start a workflow instance
        Transitions from 'pending' to 'in_progress'
        """
        instance = self.get_object()

        if instance.status != "pending":
            return Response(
                {"error": f"Cannot start workflow with status {instance.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.status = "in_progress"
        instance.save()

        # Create audit log
        WorkflowAuditLog.objects.create(
            workflow_instance=instance,
            action_type="started",
            action_description="Workflow started",
            performed_by=request.user,
        )

        serializer = WorkflowInstanceDetailSerializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """
        Cancel a workflow instance
        Only initiator or admin can cancel
        """
        instance = self.get_object()

        # Check permissions - initiator or workflow admin can cancel
        is_workflow_admin = request.user.is_superuser or can_manage(
            request.user, "workflow"
        )
        if instance.initiated_by != request.user and not is_workflow_admin:
            return Response(
                {"error": "Only the initiator or admin can cancel this workflow"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if instance.status in ["approved", "rejected", "cancelled"]:
            return Response(
                {"error": f"Cannot cancel workflow with status {instance.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.status = "cancelled"
        instance.completed_at = timezone.now()
        instance.save()

        # Update all pending steps
        instance.step_executions.filter(status="pending").update(status="cancelled")

        # Create audit log
        WorkflowAuditLog.objects.create(
            workflow_instance=instance,
            action_type="cancelled",
            action_description=request.data.get("reason", "Workflow cancelled"),
            performed_by=request.user,
        )

        serializer = WorkflowInstanceDetailSerializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def my_pending_approvals(self, request):
        """
        Get workflow instances with pending approvals for current user
        """
        user = request.user
        user_role = user.role.name if hasattr(user, "role") and user.role else None

        queryset = (
            self.get_queryset()
            .filter(
                Q(step_executions__assigned_to=user, step_executions__status="pending")
                | Q(
                    step_executions__workflow_step__approver_role=user_role,
                    step_executions__status="pending",
                    step_executions__assigned_to__isnull=True,
                )
            )
            .distinct()
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class WorkflowStepExecutionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing workflow step executions
    Handles approval/rejection of individual steps
    """

    queryset = WorkflowStepExecution.objects.all()
    serializer_class = WorkflowStepExecutionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter executions by instance and user"""
        queryset = super().get_queryset()

        instance_id = self.request.query_params.get("instance", None)
        if instance_id:
            queryset = queryset.filter(workflow_instance_id=instance_id)

        status_filter = self.request.query_params.get("status", None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.select_related(
            "workflow_instance", "workflow_step", "assigned_to", "actioned_by"
        )

    @action(detail=False, methods=["get"])
    def my_pending(self, request):
        """
        Get pending approvals for current user
        Returns all step executions assigned to this user or their role
        """
        user = request.user
        user_role = user.role if hasattr(user, "role") and user.role else None

        # Build query for user's pending approvals
        # approver_role stores role UUID as string (e.g., "f9bce96c-9bc2-41b1-aa60-cf8febda571a")
        queryset = (
            WorkflowStepExecution.objects.filter(status="pending")
            .filter(
                Q(assigned_to=user)
                | Q(
                    workflow_step__approver_role=(
                        str(user_role.id) if user_role else None
                    ),
                    assigned_to__isnull=True,
                )
            )
            .select_related(
                "workflow_instance",
                "workflow_instance__initiated_by",
                "workflow_step",
                "assigned_to",
            )
            .order_by("-created_at")
        )

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def take_action(self, request, pk=None):
        """
        Take action on a workflow step (approve/reject/skip/delegate)
        """
        step_execution = self.get_object()
        user = request.user

        # Validate action serializer
        action_serializer = WorkflowActionSerializer(data=request.data)
        action_serializer.is_valid(raise_exception=True)

        action = action_serializer.validated_data["action"]
        comments = action_serializer.validated_data.get("comments", "")

        # Check if user has permission to act on this step
        user_role = user.role.name if hasattr(user, "role") and user.role else None
        workflow_step = step_execution.workflow_step
        is_workflow_admin = user.is_superuser or can_manage(user, "workflow")

        can_action = (
            step_execution.assigned_to == user
            or (
                workflow_step.approver_role == user_role
                and not step_execution.assigned_to
            )
            or is_workflow_admin
        )

        if not can_action:
            return Response(
                {"error": "You do not have permission to action this step"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate step status
        if step_execution.status != "pending":
            return Response(
                {"error": f"Cannot action step with status {step_execution.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate workflow instance status
        if step_execution.workflow_instance.status not in ["in_progress", "pending"]:
            return Response(
                {"error": "Workflow is not active"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Validate step is current or parallel allowed
        instance = step_execution.workflow_instance
        if not instance.workflow_template.allow_parallel_steps:
            if workflow_step.step_order != instance.current_step_order:
                return Response(
                    {"error": "This step is not currently active"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Handle delegation
        if action == "delegate":
            delegated_to_id = action_serializer.validated_data.get("delegated_to_id")
            try:
                from accounts.models import User

                delegated_to = User.objects.get(id=delegated_to_id)
            except User.DoesNotExist:
                return Response(
                    {"error": "Delegated user does not exist"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create delegation
            WorkflowDelegation.objects.create(
                workflow_step_execution=step_execution,
                delegated_from=user,
                delegated_to=delegated_to,
                reason=comments,
            )

            step_execution.assigned_to = delegated_to
            step_execution.status = "delegated"
            step_execution.save()

            # Create audit log
            WorkflowAuditLog.objects.create(
                workflow_instance=instance,
                action_type="delegated",
                action_description=f"Step delegated to {delegated_to.email}",
                performed_by=user,
            )

            serializer = WorkflowStepExecutionSerializer(step_execution)
            return Response(serializer.data)

        # Handle skip/approve/reject via WorkflowEngine.process_action — the
        # canonical, transactional, entity-status-updating implementation.
        # (This also fixes a prior bug where this endpoint never updated the
        # underlying entity's `status` field, only the workflow bookkeeping.)
        if action == "skip":
            if not workflow_step.can_skip:
                return Response(
                    {"error": "This step cannot be skipped"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if action in ("skip", "approve", "reject"):
            try:
                WorkflowEngine.process_action(
                    step_execution_id=step_execution.id,
                    action=action,
                    actioned_by=user,
                    comments=comments,
                )
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            step_execution.refresh_from_db()
            serializer = WorkflowStepExecutionSerializer(step_execution)
            return Response(serializer.data)


class WorkflowDelegationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for workflow delegations
    """

    queryset = WorkflowDelegation.objects.all()
    serializer_class = WorkflowDelegationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter delegations by user"""
        queryset = super().get_queryset()
        user = self.request.user

        # Workflow admins see all delegations
        is_workflow_admin = user.is_superuser or can_manage(user, "workflow")
        if not is_workflow_admin:
            queryset = queryset.filter(Q(delegated_from=user) | Q(delegated_to=user))

        return queryset.select_related(
            "workflow_step_execution", "delegated_from", "delegated_to"
        )


class WorkflowAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for workflow audit logs
    """

    queryset = WorkflowAuditLog.objects.all()
    serializer_class = WorkflowAuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter audit logs by instance"""
        queryset = super().get_queryset()

        instance_id = self.request.query_params.get("instance", None)
        if instance_id:
            queryset = queryset.filter(workflow_instance_id=instance_id)

        action_type = self.request.query_params.get("action_type", None)
        if action_type:
            queryset = queryset.filter(action_type=action_type)

        return queryset.select_related("workflow_instance", "performed_by")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_eligible_approvers(request, entity_type: str):
    """
    Get eligible approvers for all steps in a workflow template.

    Args:
        entity_type: Type of entity (travelrequest, visaapplication, etc.)

    Query Params:
        requester_id: Optional. User ID of the original requester for department
                      filtering. Use this in edit mode to ensure approvers are
                      filtered by the original requester's department, not the
                      current viewer's department.
        staff_id: Optional. Staff ID of the original requester. Used as fallback
                  when requester_id is not available (for modules like accommodation
                  that store staff_id instead of user FK).

    Returns:
        Standardized response with template info and eligible approvers per step
    """
    from django.contrib.auth import get_user_model
    from django.db.models import Q

    from .models import WorkflowTemplate
    from .services import WorkflowApprovalHelper

    User = get_user_model()

    # Determine the requester for department filtering
    # Priority: requester_id > staff_id > current user
    requester_id = request.query_params.get("requester_id")
    staff_id = request.query_params.get("staff_id")

    requester = None
    if requester_id:
        try:
            requester = User.objects.select_related("department").get(id=requester_id)
        except (User.DoesNotExist, ValueError):
            pass

    if not requester and staff_id:
        try:
            requester = (
                User.objects.select_related("department")
                .filter(staff_id=staff_id)
                .first()
            )
        except Exception:
            pass

    if not requester:
        requester = request.user

    # Build flexible query to handle common entity_type aliases
    # Maps frontend values to possible database values
    entity_type_aliases = {
        "travelrequest": ["travelrequest", "trf", "travel_request", "travel-request"],
        "visaapplication": [
            "visaapplication",
            "visa",
            "visa_application",
            "visa-application",
        ],
        "transportrequest": [
            "transportrequest",
            "transport",
            "transport_request",
            "transport-request",
        ],
        "accommodation": [
            "accommodation",
            "accommodationrequest",
            "accommodation_request",
        ],
    }

    # Get all possible aliases for this entity_type
    search_values = entity_type_aliases.get(entity_type.lower(), [entity_type])

    # Build OR query for all possible values (case-insensitive)
    query = Q()
    for value in search_values:
        query |= Q(entity_type__iexact=value)

    template = (
        WorkflowTemplate.objects.filter(query, is_active=True)
        .prefetch_related("steps")
        .first()
    )

    if not template:
        return error_response(
            message=f"No active workflow template found for {entity_type}",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    steps_data = []
    for step in template.steps.all().order_by("step_order"):
        approvers = WorkflowApprovalHelper.get_eligible_approvers_for_step(
            step, requester
        )
        steps_data.append(
            {
                "step_order": step.step_order,
                "step_name": step.step_name,
                "step_description": step.step_description,
                "is_required": step.is_required,
                "can_skip": step.can_skip,
                "approver_role": step.approver_role,
                "approver_permission": step.approver_permission,
                "eligible_approvers": [
                    {
                        "id": user.id,
                        "email": user.email,
                        "full_name": user.get_full_name(),
                        "department": user.department.name if user.department else None,
                        "role": user.role.name if user.role else None,
                    }
                    for user in approvers
                ],
            }
        )

    return success_response(
        data={
            "template_id": str(template.id),
            "template_name": template.name,
            "entity_type": entity_type,
            "steps": steps_data,
        },
        message="Eligible approvers retrieved successfully",
    )
