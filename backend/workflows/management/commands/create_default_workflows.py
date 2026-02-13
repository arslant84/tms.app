"""
Management command to create default workflow templates for all modules.
Usage: python manage.py create_default_workflows
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from workflows.models import WorkflowTemplate, WorkflowStep
from accounts.models import User


class Command(BaseCommand):
    help = 'Creates default workflow templates for all modules (TRF, Claims, Visa, Transport, Accommodation)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing workflows before creating new ones',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('Deleting existing workflows...'))
            WorkflowTemplate.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing workflows deleted'))

        self.stdout.write(self.style.SUCCESS('Creating default workflow templates...'))

        # Get or create an admin user for created_by field
        admin_user = User.objects.filter(is_staff=True).first()

        # Create workflows
        with transaction.atomic():
            self.create_trf_workflow(admin_user)
            self.create_claims_workflow(admin_user)
            self.create_visa_workflow(admin_user)
            self.create_transport_workflow(admin_user)
            self.create_accommodation_workflow(admin_user)

        self.stdout.write(self.style.SUCCESS('✅ Successfully created all default workflows!'))
        self.stdout.write(self.style.SUCCESS(''))
        self.stdout.write(self.style.SUCCESS('Created workflows:'))
        for template in WorkflowTemplate.objects.all():
            step_count = template.steps.count()
            self.stdout.write(f'  - {template.name} ({template.entity_type}): {step_count} steps')

    def create_trf_workflow(self, created_by):
        """Create TRF (Travel Request Form) workflow"""
        self.stdout.write('Creating TRF workflow...')

        template = WorkflowTemplate.objects.create(
            name='TRF Standard Approval Workflow',
            description='Standard approval workflow for Travel Request Forms (TRF)',
            entity_type='travelrequest',
            is_active=True,
            allow_parallel_steps=False,
            auto_approve_on_condition=False,
            created_by=created_by
        )

        # Step 1: Department Focal
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=1,
            step_name='Department Focal Approval',
            step_description='Department Focal reviews and approves the travel request',
            approver_role='Department Focal',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=48,
            escalation_hours=36
        )

        # Step 2: Line Manager
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=2,
            step_name='Line Manager Approval',
            step_description='Line Manager reviews and approves the travel request',
            approver_role='Line Manager',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=48,
            escalation_hours=36
        )

        # Step 3: HOD
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=3,
            step_name='HOD Approval',
            step_description='Head of Department reviews and approves the travel request',
            approver_role='HOD',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=72,
            escalation_hours=60
        )

        # Step 4: Travel Desk (Final Processing)
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=4,
            step_name='Travel Desk Processing',
            step_description='Travel Desk processes the approved request',
            approver_role='Travel Desk',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=96,
            escalation_hours=72
        )

        self.stdout.write(self.style.SUCCESS(f'  ✓ Created TRF workflow with 4 steps'))

    def create_claims_workflow(self, created_by):
        """Create Expense Claims workflow"""
        self.stdout.write('Creating Expense Claims workflow...')

        template = WorkflowTemplate.objects.create(
            name='Expense Claims Standard Approval Workflow',
            description='Standard approval workflow for Expense Claims',
            entity_type='expenseclaim',
            is_active=True,
            allow_parallel_steps=False,
            auto_approve_on_condition=False,
            created_by=created_by
        )

        # Step 1: Department Focal
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=1,
            step_name='Department Focal Approval',
            step_description='Department Focal reviews expenses for accuracy',
            approver_role='Department Focal',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=48,
            escalation_hours=36
        )

        # Step 2: Line Manager
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=2,
            step_name='Line Manager Approval',
            step_description='Line Manager approves the expense claim',
            approver_role='Line Manager',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=48,
            escalation_hours=36
        )

        # Step 3: Finance (Final Processing)
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=3,
            step_name='Finance Processing',
            step_description='Finance department processes the payment',
            approver_role='Finance',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=120,  # 5 days
            escalation_hours=96  # 4 days
        )

        self.stdout.write(self.style.SUCCESS(f'  ✓ Created Claims workflow with 3 steps'))

    def create_visa_workflow(self, created_by):
        """Create Visa Application workflow"""
        self.stdout.write('Creating Visa Application workflow...')

        template = WorkflowTemplate.objects.create(
            name='Visa Application Standard Approval Workflow',
            description='Standard approval workflow for Visa Applications',
            entity_type='visaapplication',
            is_active=True,
            allow_parallel_steps=False,
            auto_approve_on_condition=False,
            created_by=created_by
        )

        # Step 1: Department Focal
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=1,
            step_name='Department Focal Approval',
            step_description='Department Focal verifies visa application details',
            approver_role='Department Focal',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=48,
            escalation_hours=36
        )

        # Step 2: Line Manager
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=2,
            step_name='Line Manager Approval',
            step_description='Line Manager approves the visa application',
            approver_role='Line Manager',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=48,
            escalation_hours=36
        )

        # Step 3: HOD
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=3,
            step_name='HOD Approval',
            step_description='Head of Department approves the visa application',
            approver_role='HOD',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=72,
            escalation_hours=60
        )

        # Step 4: Visa Admin (Final Processing)
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=4,
            step_name='Visa Admin Processing',
            step_description='Visa Admin processes the application with embassy',
            approver_role='Visa Admin',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=240,  # 10 days (embassy processing can be slow)
            escalation_hours=192  # 8 days
        )

        self.stdout.write(self.style.SUCCESS(f'  ✓ Created Visa workflow with 4 steps'))

    def create_transport_workflow(self, created_by):
        """Create Transport Request workflow"""
        self.stdout.write('Creating Transport Request workflow...')

        template = WorkflowTemplate.objects.create(
            name='Transport Request Standard Approval Workflow',
            description='Standard approval workflow for Transport Requests',
            entity_type='transportrequest',
            is_active=True,
            allow_parallel_steps=False,
            auto_approve_on_condition=False,
            created_by=created_by
        )

        # Step 1: Department Focal
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=1,
            step_name='Department Focal Approval',
            step_description='Department Focal reviews transport requirements',
            approver_role='Department Focal',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=24,
            escalation_hours=18
        )

        # Step 2: Line Manager
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=2,
            step_name='Line Manager Approval',
            step_description='Line Manager approves the transport request',
            approver_role='Line Manager',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=24,
            escalation_hours=18
        )

        # Step 3: HOD
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=3,
            step_name='HOD Approval',
            step_description='Head of Department approves the transport request',
            approver_role='HOD',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=48,
            escalation_hours=36
        )

        # Step 4: Transport Admin (Final Processing)
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=4,
            step_name='Transport Admin Processing',
            step_description='Transport Admin arranges vehicle and driver',
            approver_role='Transport Admin',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=72,
            escalation_hours=48
        )

        self.stdout.write(self.style.SUCCESS(f'  ✓ Created Transport workflow with 4 steps'))

    def create_accommodation_workflow(self, created_by):
        """Create Accommodation Request workflow"""
        self.stdout.write('Creating Accommodation Request workflow...')

        template = WorkflowTemplate.objects.create(
            name='Accommodation Request Standard Approval Workflow',
            description='Standard approval workflow for Accommodation Requests (subset of TRF)',
            entity_type='travelrequest',  # Accommodation is part of TRF
            is_active=False,  # Inactive since TRF workflow handles this
            allow_parallel_steps=False,
            auto_approve_on_condition=False,
            created_by=created_by
        )

        # Step 1: Department Focal
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=1,
            step_name='Department Focal Approval',
            step_description='Department Focal reviews accommodation needs',
            approver_role='Department Focal',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=48,
            escalation_hours=36
        )

        # Step 2: Line Manager
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=2,
            step_name='Line Manager Approval',
            step_description='Line Manager approves the accommodation request',
            approver_role='Line Manager',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=48,
            escalation_hours=36
        )

        # Step 3: HOD
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=3,
            step_name='HOD Approval',
            step_description='Head of Department approves the accommodation request',
            approver_role='HOD',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=72,
            escalation_hours=60
        )

        # Step 4: Accommodation Admin
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=4,
            step_name='Accommodation Admin Processing',
            step_description='Accommodation Admin arranges booking',
            approver_role='Accommodation Admin',
            is_required=True,
            can_skip=False,
            requires_comments=False,
            sla_hours=96,
            escalation_hours=72
        )

        self.stdout.write(self.style.SUCCESS(f'  ✓ Created Accommodation workflow with 4 steps (inactive)'))
