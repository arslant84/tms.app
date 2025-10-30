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
class VisaApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet for visa applications with different serializers for list/detail/create"""
    queryset = VisaApplication.objects.all().select_related('user').prefetch_related(
        'visaapprovalstep_set', 'visadocument_set'
    ).order_by('-created_at')
    permission_classes = [IsAuthenticated]

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
        """Approve a visa application step"""
        visa = self.get_object()
        step_role = request.data.get('step_role')
        comments = request.data.get('comments', '')

        # Create or update approval step
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

        # Update visa status based on approval workflow
        # This is simplified - you may want more complex logic
        status_map = {
            'Department Focal': 'Pending Manager',
            'Manager': 'Pending HOD',
            'HOD': 'Pending Visa Clerk',
            'Visa Clerk': 'Processing'
        }
        visa.status = status_map.get(step_role, visa.status)
        visa.save()

        serializer = VisaApplicationDetailSerializer(visa)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """Reject a visa application"""
        visa = self.get_object()
        step_role = request.data.get('step_role')
        comments = request.data.get('comments', '')

        # Create or update approval step
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
