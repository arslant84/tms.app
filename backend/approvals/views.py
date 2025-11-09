"""
Unified Approvals API

Provides a single endpoint for all pending approvals across all modules:
- Travel Requests (TRF/TSR)
- Transport Requests
- Visa Applications
- Accommodation Requests
- Expense Claims
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from datetime import datetime

from trf.models import TravelRequest
from transport.models import TransportRequest
from visa.models import VisaApplication
from accommodation.models import AccommodationRequest
from expenses.models import ExpenseClaim
from workflows.models import WorkflowInstance, WorkflowStepExecution
from accounts.models import Role, AdminActionLog


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
    item_type = request.GET.get('type', None)  # 'trf', 'transport', 'visa', 'accommodation', 'claim'

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
        """Check if current user is authorized to approve this entity"""
        # Admin override - with audit logging
        if user.is_staff or user.is_superuser:
            # SECURITY: Log admin override action for audit trail
            AdminActionLog.log_action(
                admin=user,
                action_type='approval_override',
                entity_type=module_name,
                entity_id=entity.id,
                description=f'Admin {user.email} viewed {module_name} #{entity.id} in approval queue (admin override)',
                request=request
            )
            return True

        # Get workflow instance for this entity
        content_type = ContentType.objects.get_for_model(entity)
        workflow_instance = WorkflowInstance.objects.filter(
            content_type=content_type,
            object_id=entity.id,
            status='in_progress'
        ).first()

        if not workflow_instance:
            # No workflow - fallback to showing to admins only
            return False

        # Get current pending step execution
        current_step_execution = workflow_instance.step_executions.filter(
            status='pending'
        ).order_by('workflow_step__step_order').first()

        if not current_step_execution:
            return False

        # Check if user is directly assigned
        if current_step_execution.assigned_to == user:
            return True

        # Check if user has the required role
        if hasattr(user, 'role') and user.role and current_step_execution.workflow_step.approver_role:
            # Handle both UUID and string role names
            try:
                # Try as role name string
                if user.role.name == current_step_execution.workflow_step.approver_role:
                    return True
            except:
                pass

            try:
                # Try as role UUID
                role = Role.objects.get(id=current_step_execution.workflow_step.approver_role)
                if user.role.name == role.name:
                    return True
            except (Role.DoesNotExist, ValueError):
                pass

        # Check for active delegation
        from django.utils import timezone
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
        elif hasattr(obj, 'purpose_of_claim') and obj.purpose_of_claim:
            purpose = obj.purpose_of_claim
        elif hasattr(obj, 'title') and obj.title:
            purpose = obj.title
        else:
            purpose = f'{item_type_name} Request'

        return {
            'id': str(obj.id),
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

    # 5. Expense Claims
    if not item_type or item_type == 'claim':
        claims = ExpenseClaim.objects.filter(
            status__in=approval_statuses
        ).order_by('-created_at')

        for claim in claims:
            # Only include if user is authorized to approve
            if can_user_approve(claim, 'claims'):
                item = format_item(claim, 'Claim')
                item['amount'] = float(getattr(claim, 'total_amount', 0) or 0)
                item['documentNumber'] = getattr(claim, 'request_number', '')
                all_items.append(item)

    # Sort all items by submission date (newest first)
    all_items.sort(key=lambda x: x['submittedAt'] or '', reverse=True)

    # Apply pagination
    total_count = len(all_items)
    paginated_items = all_items[offset:offset + limit]

    return Response({
        'items': paginated_items,
        'totalCount': total_count,
        'totalPages': (total_count + limit - 1) // limit,  # Ceiling division
        'currentPage': page,
    })
