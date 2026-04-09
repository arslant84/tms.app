"""
ViewSet Mixins for TMS Application

Reusable mixins to eliminate duplicate code across viewsets.
These mixins provide common functionality for:
- Dual lookup (ID or request_number)
- Workflow-aware queryset filtering
- Requestor info auto-population

Usage:
    from utils.viewset_mixins import DualLookupMixin, WorkflowAwareQuerySetMixin

    class TravelRequestViewSet(DualLookupMixin, WorkflowAwareQuerySetMixin, viewsets.ModelViewSet):
        model_class = TravelRequest
        entity_type = 'travelrequest'
        permission_name = 'trf'
        # ...
"""

import logging
from django.db.models import Q
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination


class StandardResultsPagination(PageNumberPagination):
    """Default pagination: respects client-supplied page_size, capped at 1000."""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 1000

logger = logging.getLogger(__name__)


class DualLookupMixin:
    """
    Mixin that supports lookup by both numeric ID and request_number.

    Required attributes on viewset:
        - model_class: The model class (e.g., TravelRequest)

    The mixin will:
        1. Check if lookup value is numeric (use pk) or string (use request_number)
        2. Try to get object from filtered queryset
        3. Provide helpful error message with request_number if available
        4. Check object permissions

    Example:
        class TravelRequestViewSet(DualLookupMixin, viewsets.ModelViewSet):
            model_class = TravelRequest
            queryset = TravelRequest.objects.all()
    """

    # Override in viewset if model doesn't have 'request_number' field
    request_number_field = 'request_number'

    def get_object(self):
        """
        Override to support lookup by both numeric ID and request_number
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field or 'pk'
        lookup_value = self.kwargs.get(lookup_url_kwarg)

        if lookup_value is None:
            raise NotFound('No identifier provided')

        # Determine if it's a numeric ID or request_number
        lookup_str = str(lookup_value)
        if lookup_str.isdigit():
            filter_kwargs = {'pk': int(lookup_value)}
        else:
            filter_kwargs = {self.request_number_field: lookup_value}

        queryset = self.filter_queryset(self.get_queryset())

        try:
            obj = queryset.get(**filter_kwargs)
        except self.model_class.DoesNotExist:
            # Try to fetch from full queryset to get request_number for better error message
            try:
                obj = self.model_class.objects.get(**filter_kwargs)
                request_identifier = getattr(obj, self.request_number_field, None) or f"ID #{obj.id}"
                model_name = self.model_class._meta.verbose_name
                raise NotFound(
                    f'{model_name.title()} {request_identifier} not found or you do not have permission to access it'
                )
            except self.model_class.DoesNotExist:
                model_name = self.model_class._meta.verbose_name
                raise NotFound(f'{model_name.title()} not found with identifier: {lookup_value}')

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj


class WorkflowAwareQuerySetMixin:
    """
    Mixin that provides workflow-aware queryset filtering.

    Required attributes on viewset:
        - model_class: The model class
        - permission_name: Base permission name (e.g., 'trf', 'transport', 'visa')

    Optional attributes:
        - user_field: Field linking to user (default: 'created_by' or 'requestor' or 'user')

    The mixin provides:
        - Approval action pass-through (no filtering for approve/reject)
        - Admin view filtering (view_all_X permission)
        - Personal view with pending approval items
        - Search and status filtering helpers
    """

    # Override in viewset as needed
    user_field = None  # Will auto-detect: created_by, requestor, or user
    permission_name = None  # e.g., 'trf', 'transport', 'visa'

    def _get_user_field(self):
        """Auto-detect the user field if not specified"""
        if self.user_field:
            return self.user_field

        # Try common field names
        model = self.model_class
        for field_name in ['created_by', 'requestor', 'user']:
            if hasattr(model, field_name):
                return field_name

        # Default fallback
        return 'created_by'

    def get_workflow_filtered_queryset(self, queryset):
        """
        Apply workflow-aware filtering to queryset.

        Call this in get_queryset() after getting the base queryset:
            def get_queryset(self):
                queryset = super().get_queryset()
                queryset = self.get_workflow_filtered_queryset(queryset)
                # Apply additional filters...
                return queryset
        """
        from workflows.services import WorkflowApprovalHelper

        user = self.request.user
        user_field = self._get_user_field()

        # For approval actions, allow access to all (authorization handled by WorkflowEngine)
        if self.action in ['approve', 'reject']:
            logger.info(f" Approval action: Allowing access to all {self.model_class._meta.verbose_name_plural}")
            return queryset

        # For retrieve (viewing details), include items pending user's approval via workflow
        if self.action == 'retrieve':
            pending_approval_ids = WorkflowApprovalHelper.get_pending_entity_ids_for_user(user, self.model_class)
            if pending_approval_ids:
                user_filter = {user_field: user}
                queryset = queryset.filter(Q(**user_filter) | Q(id__in=pending_approval_ids))
                logger.info(
                    f" Retrieve action: Including user's items and {len(pending_approval_ids)} pending approval"
                )
                return queryset

        # Check if this is an admin view
        admin_view = self.request.query_params.get('admin_view', 'false').lower() == 'true'

        # Permission-based filtering
        if admin_view and user.role:
            view_all_permission = f'view_all_{self.permission_name}'
            can_view_all = user.role.permissions.filter(name=view_all_permission).exists()

            if can_view_all:
                logger.info(
                    f" Admin view: User {user.username} (role: {user.role.name}) "
                    f"has '{view_all_permission}' permission - showing all"
                )
                # No filtering - show all
            elif user.role.permissions.filter(name__in=[f'approve_{self.permission_name}', 'view_pending_approvals']).exists():
                # Department-level approvers
                if hasattr(user, 'department') and user.department:
                    queryset = queryset.filter(department=user.department)
                    logger.info(f" Admin view: Approver role - showing department items")
                else:
                    user_filter = {user_field: user}
                    queryset = queryset.filter(**user_filter)
                    logger.warning(f" Admin view: Approver but no department - showing only own")
            else:
                # No admin permissions - show own plus pending approval
                pending_approval_ids = WorkflowApprovalHelper.get_pending_entity_ids_for_user(user, self.model_class)
                user_filter = {user_field: user}
                if pending_approval_ids:
                    queryset = queryset.filter(Q(**user_filter) | Q(id__in=pending_approval_ids))
                    logger.info(
                        f" Admin view: User lacks permission - showing own plus {len(pending_approval_ids)} pending"
                    )
                else:
                    queryset = queryset.filter(**user_filter)
                    logger.warning(f" Admin view: User lacks permission - showing only own items")
        else:
            # Personal requests view - show user's own items plus those pending their approval
            pending_approval_ids = WorkflowApprovalHelper.get_pending_entity_ids_for_user(user, self.model_class)
            user_filter = {user_field: user}
            if pending_approval_ids:
                queryset = queryset.filter(Q(**user_filter) | Q(id__in=pending_approval_ids))
                logger.info(
                    f" Personal view: User {user.username} - showing own plus {len(pending_approval_ids)} pending"
                )
            else:
                queryset = queryset.filter(**user_filter)
                logger.info(f" Personal view: User {user.username} - showing only own items")

        return queryset

    def apply_status_filter(self, queryset):
        """
        Apply status filter from query params.
        Uses startswith matching to handle workflow statuses like "Pending Line Manager".
        """
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status__istartswith=status_filter)
        return queryset


class RequestorPopulationMixin:
    """
    Mixin that auto-populates requestor information from authenticated user.

    The mixin will populate these fields if not provided:
        - requestor_name: From user.get_full_name() or user.email
        - staff_id: From user.employee_id or user.staff_id
        - department: From user.department
        - position: From user.position or user.job_title

    Also handles:
        - Setting submitted_at timestamp if status is not Draft
        - Triggering workflow if status is submitted

    Required attributes on viewset:
        - entity_type: Workflow entity type (e.g., 'travelrequest', 'transportrequest')
    """

    entity_type = None  # e.g., 'travelrequest', 'transportrequest', 'visaapplication'

    def populate_requestor_info(self, validated_data, user):
        """
        Auto-populate requestor information from authenticated user.

        Args:
            validated_data: Serializer's validated data
            user: Authenticated user

        Returns:
            dict: Extra kwargs to pass to serializer.save()
        """
        # Auto-populate requestor information if not provided
        if not validated_data.get('requestor_name'):
            validated_data['requestor_name'] = user.get_full_name() or user.email

        if not validated_data.get('staff_id'):
            validated_data['staff_id'] = getattr(user, 'employee_id', '') or getattr(user, 'staff_id', '')

        if not validated_data.get('department'):
            validated_data['department'] = getattr(user, 'department', '')

        if not validated_data.get('position'):
            validated_data['position'] = getattr(user, 'position', '') or getattr(user, 'job_title', '')

        return validated_data

    def get_create_extra_kwargs(self, validated_data, user):
        """
        Get extra kwargs for serializer.save() during create.
        Handles submitted_at timestamp based on status.

        Args:
            validated_data: Serializer's validated data
            user: Authenticated user

        Returns:
            dict: Extra kwargs for serializer.save()
        """
        from django.utils import timezone
        from utils.constants import RequestStatus

        extra_kwargs = {}
        status_value = validated_data.get('status', RequestStatus.DRAFT)

        # Set submitted_at timestamp if status is not Draft
        if status_value not in RequestStatus.draft_statuses():
            extra_kwargs['submitted_at'] = timezone.now()

        return extra_kwargs

    def start_workflow_if_needed(self, instance, user, status_value, selected_approvers=None):
        """
        Start workflow if status indicates submission.

        Args:
            instance: Created/updated model instance
            user: Authenticated user
            status_value: Current status value
            selected_approvers: Optional dict mapping step_order to selected user_id

        Returns:
            WorkflowInstance or None
        """
        from workflows.router import WorkflowRouter
        from utils.constants import RequestStatus

        if status_value in RequestStatus.draft_statuses():
            return None

        try:
            workflow_instance = WorkflowRouter.start_workflow_for_request(
                entity=instance,
                entity_type=self.entity_type,
                initiated_by=user,
                selected_approvers=selected_approvers
            )

            if workflow_instance:
                # Reload to get the updated status from workflow
                instance.refresh_from_db()
                logger.info(
                    f" Workflow started for {self.entity_type} #{instance.id}: "
                    f"Workflow Instance #{workflow_instance.id}"
                )
                logger.info(f" Status updated to: {instance.status}")
                return workflow_instance
            else:
                logger.warning(f" No active workflow configured for {self.entity_type}")
                return None

        except Exception as e:
            logger.error(f" Error starting workflow for {self.entity_type} #{instance.id}: {str(e)}")
            # Don't fail the request creation if workflow fails
            return None
