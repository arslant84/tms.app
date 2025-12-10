from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q

from .models import VisaApplication, VisaApprovalStep, VisaDocument
from .serializers import (
    VisaApplicationListSerializer,
    VisaApplicationDetailSerializer,
    VisaApplicationCreateUpdateSerializer,
    VisaApprovalStepSerializer,
    VisaDocumentSerializer
)
from workflows.router import WorkflowRouter
from utils.request_id_generator import generate_request_id
from datetime import datetime
class VisaApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet for visa applications with different serializers for list/detail/create"""
    queryset = VisaApplication.objects.all().select_related('user').prefetch_related(
        'visaapprovalstep_set', 'visadocument_set'
    ).order_by('-created_at')
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        Override to show proper request_number in error messages
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field or 'pk'
        lookup_value = self.kwargs[lookup_url_kwarg]

        # Try to determine if it's a numeric ID or request_number
        if str(lookup_value).isdigit():
            filter_kwargs = {'pk': int(lookup_value)}
        else:
            filter_kwargs = {'request_number': lookup_value}

        queryset = self.filter_queryset(self.get_queryset())

        try:
            obj = queryset.get(**filter_kwargs)
        except VisaApplication.DoesNotExist:
            from rest_framework.exceptions import NotFound

            # Try to fetch from full queryset to get request_number for better error message
            try:
                obj = VisaApplication.objects.get(**filter_kwargs)
                request_identifier = obj.request_number or f"ID #{obj.id}"
                raise NotFound(f'Visa application {request_identifier} not found or you do not have permission to access it')
            except VisaApplication.DoesNotExist:
                raise NotFound(f'Visa application not found with identifier: {lookup_value}')

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def get_queryset(self):
        """
        Filter visa applications based on user permissions

        Context-aware filtering:
        - Approval actions (approve/reject): Allow access to all applications (authorization checked in WorkflowEngine)
        - admin_view=true: Show all/department visas if user has appropriate permissions (Admin Module)
        - Otherwise: Show only user's own visa applications (Personal Requests view)
        """
        user = self.request.user
        queryset = self.queryset

        # For approval actions, allow access to applications pending the user's approval
        if self.action in ['approve', 'reject']:
            print(f"✅ Approval action: Allowing access to all visa applications (authorization checked in WorkflowEngine)")
            return queryset  # No filtering - authorization handled by WorkflowEngine

        # Check if this is an admin view (Visa Admin module)
        admin_view = self.request.query_params.get('admin_view', 'false').lower() == 'true'

        # Permission-based filtering
        if admin_view and user.role:
            # Admin module context - check permissions
            can_view_all = user.role.permissions.filter(name='view_all_visa').exists()

            if can_view_all:
                print(f"✅ Admin view: User {user.username} (role: {user.role.name}) has 'view_all_visa' permission - showing all visa applications")
                pass  # No filtering - show all
            elif user.role.permissions.filter(name__in=['approve_visa', 'view_pending_approvals']).exists():
                # Department-level approvers
                if user.department:
                    queryset = queryset.filter(user__department=user.department)
                    print(f"✅ Admin view: Approver - showing department visa applications")
                else:
                    queryset = queryset.filter(user=user)
                    print(f"⚠️ Admin view: Approver but no department - showing only own")
            else:
                # No admin permissions - show only own
                queryset = queryset.filter(user=user)
                print(f"⚠️ Admin view: User lacks permission - showing only own visa applications")
        else:
            # Personal requests view - always show only user's own applications
            queryset = queryset.filter(user=user)
            print(f"✅ Personal view: User {user.username} - showing only own visa applications")

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return VisaApplicationListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return VisaApplicationCreateUpdateSerializer
        return VisaApplicationDetailSerializer

    def perform_create(self, serializer):
        """Set user and submitted_date when creating visa application"""
        from django.utils import timezone

        # Get the status from validated data
        status_value = serializer.validated_data.get('status', 'Draft')

        # Set submitted_date if status is not Draft
        extra_kwargs = {}
        if status_value != 'Draft':
            extra_kwargs['submitted_date'] = timezone.now()

        # Generate request number if submitting (not Draft)
        if status_value not in ['Draft']:
            try:
                # Extract context from destination field
                destination = serializer.validated_data.get('destination', '')
                context = destination if destination else 'VIS'  # Let generate_request_id handle validation

                print(f"🔍 Extracted context for Visa Application: {context}")

                # Generate unique request number (will auto-validate and limit context to 5 chars)
                request_number = generate_request_id('VIS', context)
                extra_kwargs['request_number'] = request_number
                print(f"✅ Generated request number: {request_number}")
            except Exception as e:
                print(f"❌ Error generating request number: {str(e)}")
                import traceback
                traceback.print_exc()

        # Save the visa application
        visa_application = serializer.save(user=self.request.user, **extra_kwargs)

        # Start workflow if status is submitted (not Draft)
        if status_value in ['Pending', 'Pending Department Focal', 'Pending Line Manager', 'Pending HOD', 'Submitted']:
            try:
                workflow_instance = WorkflowRouter.start_workflow_for_request(
                    entity=visa_application,
                    entity_type='visaapplication',
                    initiated_by=self.request.user
                )

                if workflow_instance:
                    # Reload the visa application to get the updated status from workflow
                    visa_application.refresh_from_db()
                    print(f"✅ Workflow started for Visa Application #{visa_application.id}: Workflow Instance #{workflow_instance.id}")
                    print(f"✅ Status updated to: {visa_application.status}")
                else:
                    print(f"⚠️ No active workflow configured for visaapplication - using legacy approval system")
            except Exception as e:
                print(f"❌ Error starting workflow for Visa Application #{visa_application.id}: {str(e)}")
                # Don't fail the request creation if workflow fails
                pass

    def perform_update(self, serializer):
        """Update submitted_date when status changes from Draft and start workflow"""
        from django.utils import timezone

        instance = serializer.instance
        old_status = instance.status
        new_status = serializer.validated_data.get('status', old_status)

        # Set submitted_date if changing from Draft and not already set
        extra_kwargs = {}
        if old_status == 'Draft' and new_status != 'Draft' and not instance.submitted_date:
            extra_kwargs['submitted_date'] = timezone.now()

        # Generate request number if transitioning from Draft and doesn't have one
        if old_status == 'Draft' and new_status not in ['Draft'] and not instance.request_number:
            try:
                # Extract context from destination field
                destination = serializer.validated_data.get('destination', instance.destination)
                context = destination if destination else 'VIS'  # Let generate_request_id handle validation

                print(f"🔍 Extracted context for Visa Application #{instance.id}: {context}")

                # Generate unique request number (will auto-validate and limit context to 5 chars)
                request_number = generate_request_id('VIS', context)
                extra_kwargs['request_number'] = request_number
                print(f"✅ Generated request number: {request_number}")
            except Exception as e:
                print(f"❌ Error generating request number: {str(e)}")
                import traceback
                traceback.print_exc()
                # Fallback to simple format
                extra_kwargs['request_number'] = f"VIS-{datetime.now().strftime('%Y%m%d-%H%M')}-VIS-{instance.id}"
                print(f"⚠️ Using fallback request number: {extra_kwargs['request_number']}")

        # Save the visa application
        visa_application = serializer.save(**extra_kwargs)

        # Start workflow if transitioning from Draft to submitted status
        if old_status == 'Draft' and new_status in ['Pending', 'Pending Department Focal', 'Pending Line Manager', 'Pending HOD', 'Submitted']:
            try:
                workflow_instance = WorkflowRouter.start_workflow_for_request(
                    entity=visa_application,
                    entity_type='visaapplication',
                    initiated_by=self.request.user
                )

                if workflow_instance:
                    visa_application.refresh_from_db()
                    print(f"✅ Workflow started for Visa Application #{visa_application.id}: Workflow Instance #{workflow_instance.id}")
                else:
                    print(f"⚠️ No active workflow configured for visaapplication")
            except Exception as e:
                print(f"❌ Error starting workflow for Visa Application #{visa_application.id}: {str(e)}")
                pass

    @action(detail=False, methods=['get'], url_path='pending-approvals')
    def pending_approvals(self, request):
        """Get visa applications pending approval"""
        queryset = self.queryset.filter(
            status__in=['Pending Department Focal', 'Pending Manager', 'Pending HOD', 'Pending Visa Clerk']
        )
        serializer = VisaApplicationListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='my-applications')
    def my_applications(self, request):
        """Get current user's visa applications"""
        queryset = self.queryset.filter(user=request.user)
        serializer = VisaApplicationListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """Approve a visa application using WorkflowEngine"""
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType

        visa = self.get_object()
        step_role = request.data.get('step_role')
        comments = request.data.get('comments', '')

        try:
            # Get the workflow instance for this visa
            content_type = ContentType.objects.get_for_model(visa)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=visa.id,
                status='in_progress'
            ).first()

            if workflow_instance:
                # Find the current pending step
                current_step = workflow_instance.step_executions.filter(
                    status='pending'
                ).order_by('workflow_step__step_order').first()

                if current_step:
                    # Use workflow engine to process approval
                    result = WorkflowEngine.process_action(
                        step_execution_id=current_step.id,
                        action='approve',
                        actioned_by=request.user,
                        comments=comments
                    )

                    # Reload to get updated status
                    visa.refresh_from_db()

                    # Update legacy approval step for backward compatibility
                    approval_step, created = VisaApprovalStep.objects.get_or_create(
                        visa=visa,
                        step_role=step_role,
                        defaults={
                            'step_name': f'{step_role} Approval',
                            'status': 'Approved',
                            'comments': comments
                        }
                    )
                    if not created:
                        approval_step.status = 'Approved'
                        approval_step.comments = comments
                        approval_step.save()

                    serializer = VisaApplicationDetailSerializer(visa)
                    return Response(serializer.data)
                else:
                    return Response(
                        {'error': 'No pending approval step found'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Fallback to legacy approval logic
                print(f"⚠️ No workflow instance found for Visa #{visa.id}, using legacy approval")

                approval_step, created = VisaApprovalStep.objects.get_or_create(
                    visa=visa,
                    step_role=step_role,
                    defaults={
                        'step_name': f'{step_role} Approval',
                        'status': 'Approved',
                        'comments': comments
                    }
                )

                if not created:
                    approval_step.status = 'Approved'
                    approval_step.comments = comments
                    approval_step.save()

                status_map = {
                    'Department Focal': 'Pending HOD',
                    'HOD': 'Approved'
                }
                visa.status = status_map.get(step_role, visa.status)
                visa.save()

                serializer = VisaApplicationDetailSerializer(visa)
                return Response(serializer.data)

        except Exception as e:
            print(f"❌ Error in approve workflow: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Failed to process approval: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """Reject a visa application using WorkflowEngine"""
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType

        visa = self.get_object()
        step_role = request.data.get('step_role')
        comments = request.data.get('comments', '')

        try:
            content_type = ContentType.objects.get_for_model(visa)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=visa.id,
                status='in_progress'
            ).first()

            if workflow_instance:
                current_step = workflow_instance.step_executions.filter(
                    status='pending'
                ).order_by('workflow_step__step_order').first()

                if current_step:
                    result = WorkflowEngine.process_action(
                        step_execution_id=current_step.id,
                        action='reject',
                        actioned_by=request.user,
                        comments=comments
                    )

                    visa.refresh_from_db()

                    approval_step, created = VisaApprovalStep.objects.get_or_create(
                        visa=visa,
                        step_role=step_role,
                        defaults={
                            'step_name': f'{step_role} Approval',
                            'status': 'Rejected',
                            'comments': comments
                        }
                    )
                    if not created:
                        approval_step.status = 'Rejected'
                        approval_step.comments = comments
                        approval_step.save()

                    serializer = VisaApplicationDetailSerializer(visa)
                    return Response(serializer.data)
            else:
                # Fallback to legacy rejection
                approval_step, created = VisaApprovalStep.objects.get_or_create(
                    visa=visa,
                    step_role=step_role,
                    defaults={
                        'step_name': f'{step_role} Approval',
                        'status': 'Rejected',
                        'comments': comments
                    }
                )

                if not created:
                    approval_step.status = 'Rejected'
                    approval_step.comments = comments
                    approval_step.save()

                visa.status = 'Rejected'
                visa.save()

                serializer = VisaApplicationDetailSerializer(visa)
                return Response(serializer.data)

        except Exception as e:
            print(f"❌ Error in reject workflow: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Failed to process rejection: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VisaApprovalStepViewSet(viewsets.ModelViewSet):
    """ViewSet for visa approval steps"""
    queryset = VisaApprovalStep.objects.all().order_by('step_date')
    serializer_class = VisaApprovalStepSerializer
    permission_classes = [IsAuthenticated]


class VisaDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for visa documents"""
    queryset = VisaDocument.objects.all().order_by('-uploaded_at')
    serializer_class = VisaDocumentSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='by-visa/(?P<visa_id>[^/.]+)')
    def by_visa(self, request, visa_id=None):
        """Get all documents for a specific visa application"""
        documents = self.queryset.filter(visa_id=visa_id)
        serializer = self.get_serializer(documents, many=True)
        return Response(serializer.data)
