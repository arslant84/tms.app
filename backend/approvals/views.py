"""
Unified Approvals API

Provides a single endpoint for all pending approvals across all modules:
- Travel Requests (TRF/TSR)
- Transport Requests
- Visa Applications
- Accommodation Requests
- Combined Requests (unified TSR + Transport + Accommodation + Visa)
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from datetime import datetime
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from utils.api_response import success_response, paginated_response, get_pagination_params
from accounts.utils import has_permission, can_approve

from trf.models import TravelRequest
from transport.models import TransportRequest
from visa.models import VisaApplication
from accommodation.models import AccommodationRequest
# CombinedRequest is imported lazily inside functions to avoid circular import issues
from workflows.models import WorkflowInstance, WorkflowStepExecution
from accounts.models import Role, AdminActionLog


@extend_schema(
    tags=['Approvals'],
    summary='List pending approvals',
    description='Get all pending approvals across all modules (TRF, Transport, Visa, Accommodation, Combined). '
                'Returns items based on user role and workflow assignments.',
    parameters=[
        OpenApiParameter('page', OpenApiTypes.INT, description='Page number', default=1),
        OpenApiParameter('limit', OpenApiTypes.INT, description='Items per page', default=20),
        OpenApiParameter('type', OpenApiTypes.STR, description='Filter by type: trf, transport, visa, accommodation, combined')
    ],
    responses={200: {'description': 'List of pending approval items'}}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unified_approvals(request):
    """
    Get all pending approvals across all modules

    Returns a unified list of items pending approval based on:
    - User's role matching the workflow step's approver_role
    - OR user being specifically assigned to the step
    - OR user being admin (override)
    """
    user = request.user
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 20))
    item_type = request.GET.get('type', None)  # 'trf', 'transport', 'visa', 'accommodation', 'combined'

    offset = (page - 1) * limit

    # Define approval statuses that should appear in approval queue
    approval_statuses = [
        'Pending',
        'Pending Department Focal',
        'Pending HOD',
        'Pending Travel Desk',
        'Pending Finance',
        'Pending Line Manager',
        'Pending Visa Clerk',
        'Submitted',
        'Under Review'
    ]

    all_items = []

    # Helper function to check if user can approve this entity
    def can_user_approve(entity, module_name):
        """Check if current user is authorized to approve this entity based on workflow step.

        IMPORTANT: When a specific approver is selected (assigned_to is set),
        ONLY that user (or admin/delegated users) can approve. Role-based
        matching is only used when no specific user is assigned.
        """
        # Only superusers see ALL approvals without workflow check
        if user.is_superuser:
            return True

        # Get workflow instance for this entity
        content_type = ContentType.objects.get_for_model(entity)
        workflow_instance = WorkflowInstance.objects.filter(
            content_type=content_type,
            object_id=entity.id,
            status='in_progress'
        ).first()

        if not workflow_instance:
            # No workflow - only show to superusers (handled above)
            return False

        # Get current pending step execution
        current_step_execution = workflow_instance.step_executions.filter(
            status='pending'
        ).order_by('workflow_step__step_order').first()

        if not current_step_execution:
            return False

        # Check if user is directly assigned to this step (specific approver was selected)
        if current_step_execution.assigned_to == user:
            return True

        # If a specific approver is assigned (assigned_to is NOT null),
        # only that user can approve - skip role-based matching and only check delegations
        from django.utils import timezone
        if current_step_execution.assigned_to is not None:
            active_delegations = current_step_execution.delegations.filter(
                delegated_to=user,
                is_active=True
            ).filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
            ).exists()
            return active_delegations

        # Role-based matching - only when NO specific user is assigned (assigned_to is NULL)
        if hasattr(user, 'role') and user.role and current_step_execution.workflow_step.approver_role:
            approver_role_value = current_step_execution.workflow_step.approver_role

            # Compare user's role UUID with step's approver_role
            if str(user.role.id) == approver_role_value:
                return True

            # Also try role name comparison for legacy data
            if user.role.name == approver_role_value:
                return True

            # Try looking up the role by UUID to compare names
            try:
                step_role = Role.objects.get(id=approver_role_value)
                if user.role.id == step_role.id:
                    return True
            except (Role.DoesNotExist, ValueError):
                pass

        # Check for active delegation
        active_delegations = current_step_execution.delegations.filter(
            delegated_to=user,
            is_active=True
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        ).exists()

        return active_delegations

    # Helper function to format items
    def format_item(obj, item_type_name):
        # Get requestor name from various possible fields
        requestor_name = ''
        if hasattr(obj, 'requestor_name'):
            requestor_name = obj.requestor_name
        elif hasattr(obj, 'staff_name'):
            requestor_name = obj.staff_name
        elif hasattr(obj, 'user') and obj.user:
            requestor_name = obj.user.name if hasattr(obj.user, 'name') else obj.user.email

        # Get purpose from various possible fields
        purpose = ''
        if hasattr(obj, 'purpose') and obj.purpose:
            purpose = obj.purpose
        elif hasattr(obj, 'travel_purpose') and obj.travel_purpose:
            purpose = obj.travel_purpose
        elif hasattr(obj, 'title') and obj.title:
            purpose = obj.title
        else:
            purpose = f'{item_type_name} Request'

        # Get request_number (formatted ID) or fallback to numeric ID
        request_identifier = getattr(obj, 'request_number', None) or str(obj.id)

        return {
            'id': str(obj.id),  # Keep numeric ID for API calls
            'requestNumber': request_identifier,  # Display formatted request number
            'requestorName': requestor_name,
            'itemType': item_type_name,
            'purpose': purpose,
            'status': obj.status,
            'submittedAt': (obj.submitted_at if hasattr(obj, 'submitted_at') and obj.submitted_at
                           else obj.submitted_date if hasattr(obj, 'submitted_date') and obj.submitted_date
                           else obj.created_at).isoformat() if hasattr(obj, 'created_at') else None,
            'department': getattr(obj, 'department', '') or getattr(obj, 'department_code', ''),
        }

    # 1. Travel Requests (TRF/TSR) - exclude Accommodation type
    if not item_type or item_type == 'trf':
        trfs = TravelRequest.objects.filter(
            status__in=approval_statuses
        ).exclude(
            Q(travel_type='Accommodation') | Q(travel_type__icontains='Accommodation')
        ).order_by('-submitted_at')

        for trf in trfs:
            # Only include if user is authorized to approve
            if can_user_approve(trf, 'trf'):
                item = format_item(trf, 'TSR')
                item['travelType'] = getattr(trf, 'travel_type', '')
                all_items.append(item)

    # 2. Transport Requests
    if not item_type or item_type == 'transport':
        transports = TransportRequest.objects.filter(
            status__in=approval_statuses
        ).order_by('-submitted_at')

        for transport in transports:
            # Only include if user is authorized to approve
            if can_user_approve(transport, 'transport'):
                item = format_item(transport, 'Transport')
                all_items.append(item)

    # 3. Visa Applications
    if not item_type or item_type == 'visa':
        visas = VisaApplication.objects.filter(
            status__in=approval_statuses
        ).order_by('-submitted_date')

        for visa in visas:
            # Only include if user is authorized to approve
            if can_user_approve(visa, 'visa'):
                item = format_item(visa, 'Visa')
                item['destination'] = getattr(visa, 'destination', '')
                item['visaType'] = getattr(visa, 'visa_type', '')
                all_items.append(item)

    # 4. Accommodation Requests (from TRF with Accommodation travel_type)
    if not item_type or item_type == 'accommodation':
        accommodations = TravelRequest.objects.filter(
            status__in=approval_statuses,
            travel_type='Accommodation'
        ).order_by('-submitted_at')

        for accom in accommodations:
            # Only include if user is authorized to approve
            if can_user_approve(accom, 'trf'):
                item = format_item(accom, 'Accommodation')
                # Try to get accommodation details
                accom_details = accom.accommodation_details.first() if hasattr(accom, 'accommodation_details') else None
                if accom_details:
                    item['location'] = getattr(accom_details, 'location', '')
                    item['checkInDate'] = getattr(accom_details, 'check_in_date', None)
                    item['checkOutDate'] = getattr(accom_details, 'check_out_date', None)
                all_items.append(item)

        # Also check standalone accommodation requests
        standalone_accommodations = AccommodationRequest.objects.filter(
            status__in=approval_statuses
        ).order_by('-submitted_at')

        for accom in standalone_accommodations:
            # Only include if user is authorized to approve
            if can_user_approve(accom, 'accommodation'):
                item = format_item(accom, 'Accommodation')
                # Get location from additional_data
                if hasattr(accom, 'additional_data') and isinstance(accom.additional_data, dict):
                    item['location'] = accom.additional_data.get('location', '')
                    item['checkInDate'] = accom.additional_data.get('requested_check_in_date', '')
                    item['checkOutDate'] = accom.additional_data.get('requested_check_out_date', '')
                all_items.append(item)

    # 5. Combined Requests (TSR + Transport + Accommodation + Visa)
    if not item_type or item_type == 'combined':
        from combined_request.models import CombinedRequest
        combined_requests = CombinedRequest.objects.filter(
            status__in=approval_statuses
        ).order_by('-submitted_at')

        for combined in combined_requests:
            # Only include if user is authorized to approve
            if can_user_approve(combined, 'combinedrequest'):
                item = format_item(combined, 'Combined')
                # Add included modules info
                item['includedModules'] = combined.get_included_modules()
                item['travelType'] = getattr(combined, 'travel_type', '')
                item['destination'] = f"{combined.destination_city or ''}, {combined.destination_country or ''}".strip(', ')
                all_items.append(item)

    # Sort all items by submission date (newest first)
    all_items.sort(key=lambda x: x['submittedAt'] or '', reverse=True)

    # Apply pagination
    total_count = len(all_items)
    paginated_items = all_items[offset:offset + limit]

    return success_response(
        data=paginated_items,
        message=f'Retrieved {len(paginated_items)} pending approval(s)',
        status_code=200,
        meta={
            'pagination': {
                'page': page,
                'limit': limit,
                'total_count': total_count,
                'total_pages': (total_count + limit - 1) // limit,
                'has_next': page < ((total_count + limit - 1) // limit),
                'has_previous': page > 1
            }
        }
    )


@extend_schema(
    tags=['Approvals'],
    summary='Bulk approve/reject',
    description='Approve or reject multiple items at once. Supports TRF, Transport, Visa, and Accommodation requests.',
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'items': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'type': {'type': 'string', 'enum': ['trf', 'transport', 'visa', 'accommodation']}
                        }
                    }
                },
                'action': {'type': 'string', 'enum': ['approve', 'reject']},
                'comments': {'type': 'string'}
            },
            'required': ['items', 'action']
        }
    },
    responses={
        200: {'description': 'Bulk action completed with results'},
        400: {'description': 'Invalid request data'}
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_approve(request):
    """
    Bulk approve or reject multiple items at once

    Request body:
    {
        "items": [
            {"id": "123", "type": "trf"},
            {"id": "456", "type": "transport"},
            ...
        ],
        "action": "approve" or "reject",
        "comments": "Optional comments for all items"
    }
    """
    from django.db import transaction
    from utils.api_response import success_response, error_response
    import logging

    logger = logging.getLogger(__name__)
    user = request.user

    items = request.data.get('items', [])
    action = request.data.get('action', '').lower()
    comments = request.data.get('comments', '')

    if not items:
        return error_response(
            message='No items provided for bulk action',
            status_code=400
        )

    if action not in ['approve', 'reject']:
        return error_response(
            message='Invalid action. Must be "approve" or "reject"',
            status_code=400
        )

    # Map item types to models (lazy import CombinedRequest to avoid circular import)
    from combined_request.models import CombinedRequest
    type_model_map = {
        'trf': TravelRequest,
        'transport': TransportRequest,
        'visa': VisaApplication,
        'accommodation': AccommodationRequest,
        'combined': CombinedRequest
    }

    results = {
        'success': [],
        'failed': []
    }

    with transaction.atomic():
        for item in items:
            item_id = item.get('id')
            item_type = item.get('type', '').lower()

            if item_type not in type_model_map:
                results['failed'].append({
                    'id': item_id,
                    'type': item_type,
                    'error': f'Unknown item type: {item_type}'
                })
                continue

            model = type_model_map[item_type]

            try:
                obj = model.objects.get(id=item_id)

                # Check if user can approve this item
                from django.contrib.contenttypes.models import ContentType
                content_type = ContentType.objects.get_for_model(obj)

                workflow_instance = WorkflowInstance.objects.filter(
                    content_type=content_type,
                    object_id=obj.id,
                    status='in_progress'
                ).first()

                if not workflow_instance:
                    results['failed'].append({
                        'id': item_id,
                        'type': item_type,
                        'error': 'No active workflow found'
                    })
                    continue

                # Get current pending step
                current_step = workflow_instance.step_executions.filter(
                    status='pending'
                ).order_by('workflow_step__step_order').first()

                if not current_step:
                    results['failed'].append({
                        'id': item_id,
                        'type': item_type,
                        'error': 'No pending workflow step'
                    })
                    continue

                # Update step execution
                from django.utils import timezone
                current_step.status = 'approved' if action == 'approve' else 'rejected'
                current_step.actioned_by = user
                current_step.action_date = timezone.now()
                current_step.comments = comments
                current_step.save()

                # Update main object status based on action
                if action == 'approve':
                    # Check if there are more steps
                    next_step = workflow_instance.step_executions.filter(
                        status='pending',
                        workflow_step__step_order__gt=current_step.workflow_step.step_order
                    ).order_by('workflow_step__step_order').first()

                    if next_step:
                        # Move to next step status
                        obj.status = f'Pending {next_step.workflow_step.step_name}'
                    else:
                        # Final approval
                        obj.status = 'Approved'
                        workflow_instance.status = 'approved'
                        workflow_instance.completed_at = timezone.now()
                        workflow_instance.save()
                else:
                    obj.status = 'Rejected'
                    workflow_instance.status = 'rejected'
                    workflow_instance.completed_at = timezone.now()
                    workflow_instance.save()

                obj.save()

                # Send notifications based on workflow step configuration
                from workflows.notifications import WorkflowNotifications
                if action == 'approve':
                    WorkflowNotifications.trigger_configured_notifications(current_step, 'approval')
                    # If workflow completed, also send workflow_completed notifications
                    if workflow_instance.status == 'approved':
                        WorkflowNotifications.notify_workflow_completed(workflow_instance)
                else:
                    WorkflowNotifications.trigger_configured_notifications(current_step, 'rejection')

                # Log the action
                AdminActionLog.objects.create(
                    user=user,
                    action_type=f'bulk_{action}',
                    entity_type=item_type,
                    entity_id=str(item_id),
                    description=f'Bulk {action} - {comments[:100]}' if comments else f'Bulk {action}',
                    ip_address=request.META.get('REMOTE_ADDR', '')
                )

                results['success'].append({
                    'id': item_id,
                    'type': item_type,
                    'new_status': obj.status
                })

            except model.DoesNotExist:
                results['failed'].append({
                    'id': item_id,
                    'type': item_type,
                    'error': 'Item not found'
                })
            except Exception as e:
                logger.error(f'Error processing bulk {action} for {item_type} {item_id}: {str(e)}')
                results['failed'].append({
                    'id': item_id,
                    'type': item_type,
                    'error': str(e)
                })

    return success_response(
        data=results,
        message=f'Bulk {action} completed: {len(results["success"])} success, {len(results["failed"])} failed',
        status_code=200
    )


@extend_schema(
    tags=['Approvals'],
    summary='Get approval history',
    description='Get approval history for a specific item or all items. Shows workflow step executions and status changes.',
    parameters=[
        OpenApiParameter('item_id', OpenApiTypes.STR, description='ID of the specific item'),
        OpenApiParameter('item_type', OpenApiTypes.STR, description='Type: trf, transport, visa, accommodation'),
        OpenApiParameter('page', OpenApiTypes.INT, description='Page number', default=1),
        OpenApiParameter('limit', OpenApiTypes.INT, description='Items per page', default=20)
    ],
    responses={200: {'description': 'Approval history records'}}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def approval_history(request):
    """
    Get approval history for a specific item or all items

    Query params:
    - item_id: ID of the specific item (optional)
    - item_type: Type of item (trf, transport, visa, accommodation) (required if item_id is provided)
    - page: Page number (default: 1)
    - limit: Items per page (default: 20)
    """
    from django.contrib.contenttypes.models import ContentType
    from utils.api_response import success_response, error_response

    user = request.user
    item_id = request.GET.get('item_id')
    item_type = request.GET.get('item_type', '').lower()
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 20))

    offset = (page - 1) * limit

    # Map item types to models (lazy import CombinedRequest to avoid circular import)
    from combined_request.models import CombinedRequest
    type_model_map = {
        'trf': TravelRequest,
        'transport': TransportRequest,
        'visa': VisaApplication,
        'accommodation': AccommodationRequest,
        'combined': CombinedRequest
    }

    history_items = []

    if item_id and item_type:
        # Get history for specific item
        if item_type not in type_model_map:
            return error_response(
                message=f'Invalid item type: {item_type}',
                status_code=400
            )

        model = type_model_map[item_type]

        try:
            obj = model.objects.get(id=item_id)
            content_type = ContentType.objects.get_for_model(obj)

            # Get all workflow instances for this item
            workflows = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=obj.id
            ).order_by('-created_at')

            for workflow in workflows:
                # Get all step executions
                steps = workflow.step_executions.select_related(
                    'workflow_step', 'actioned_by', 'assigned_to'
                ).order_by('workflow_step__step_order')

                for step in steps:
                    history_items.append({
                        'id': str(step.id),
                        'item_id': str(obj.id),
                        'item_type': item_type,
                        'step_name': step.workflow_step.step_name,
                        'step_order': step.workflow_step.step_order,
                        'status': step.status,
                        'assigned_to': {
                            'id': step.assigned_to.id if step.assigned_to else None,
                            'name': step.assigned_to.get_full_name() if step.assigned_to else None,
                            'email': step.assigned_to.email if step.assigned_to else None
                        } if step.assigned_to else None,
                        'actioned_by': {
                            'id': step.actioned_by.id if step.actioned_by else None,
                            'name': step.actioned_by.get_full_name() if step.actioned_by else None,
                            'email': step.actioned_by.email if step.actioned_by else None
                        } if step.actioned_by else None,
                        'action_date': step.action_date.isoformat() if step.action_date else None,
                        'comments': step.comments,
                        'created_at': step.created_at.isoformat(),
                        'workflow_status': workflow.status
                    })

        except model.DoesNotExist:
            return error_response(
                message=f'{item_type.upper()} with id {item_id} not found',
                status_code=404
            )

    else:
        # Get all recent approval history (admin only for full history)
        from django.conf import settings

        # Get recent workflow step executions
        step_executions = WorkflowStepExecution.objects.select_related(
            'workflow_instance', 'workflow_step', 'actioned_by', 'assigned_to'
        ).exclude(
            status='pending'
        ).order_by('-action_date')

        # For non-admin users, filter to their own items
        has_approval_access = user.is_superuser or has_permission(user, 'view_pending_approvals') or can_approve(user)
        if not has_approval_access and not settings.DEBUG:
            # This is a simplified filter - in production you'd want more precise filtering
            step_executions = step_executions.filter(
                Q(actioned_by=user) | Q(assigned_to=user)
            )

        for step in step_executions[:100]:  # Limit to 100 for performance
            workflow = step.workflow_instance

            # Get the actual item details
            try:
                content_type = workflow.content_type
                model_class = content_type.model_class()
                obj = model_class.objects.get(id=workflow.object_id)

                # Determine item type
                model_name = content_type.model
                if model_name == 'travelrequest':
                    detected_type = 'trf'
                elif model_name == 'transportrequest':
                    detected_type = 'transport'
                elif model_name == 'visaapplication':
                    detected_type = 'visa'
                elif model_name == 'accommodationrequest':
                    detected_type = 'accommodation'
                elif model_name == 'combinedrequest':
                    detected_type = 'combined'
                else:
                    detected_type = model_name

                history_items.append({
                    'id': str(step.id),
                    'item_id': str(workflow.object_id),
                    'item_type': detected_type,
                    'item_summary': getattr(obj, 'purpose', None) or getattr(obj, 'title', None) or str(obj),
                    'step_name': step.workflow_step.step_name,
                    'status': step.status,
                    'actioned_by': {
                        'id': step.actioned_by.id if step.actioned_by else None,
                        'name': step.actioned_by.get_full_name() if step.actioned_by else None,
                        'email': step.actioned_by.email if step.actioned_by else None
                    } if step.actioned_by else None,
                    'action_date': step.action_date.isoformat() if step.action_date else None,
                    'comments': step.comments
                })
            except Exception:
                continue

    # Apply pagination
    total_count = len(history_items)
    paginated_items = history_items[offset:offset + limit]

    return success_response(
        data=paginated_items,
        message=f'Retrieved {len(paginated_items)} approval history record(s)',
        status_code=200,
        meta={
            'pagination': {
                'page': page,
                'limit': limit,
                'total_count': total_count,
                'total_pages': (total_count + limit - 1) // limit if total_count > 0 else 1,
                'has_next': page < ((total_count + limit - 1) // limit) if total_count > 0 else False,
                'has_previous': page > 1
            }
        }
    )
