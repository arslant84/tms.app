"""
Management command to create default workflow templates for all modules.
Usage: python manage.py create_default_workflows
"""

from accounts.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from workflows.models import WorkflowStep, WorkflowTemplate


class Command(BaseCommand):
    help = "Creates default workflow templates for all modules (TRF, Visa, Transport, Accommodation)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing workflows before creating new ones",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write(self.style.WARNING("Deleting existing workflows..."))
            WorkflowTemplate.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Existing workflows deleted"))

        self.stdout.write(self.style.SUCCESS("Creating default workflow templates..."))

        # Get or create an admin user for created_by field
        admin_user = User.objects.filter(is_staff=True).first()

        # Create workflows (each creator skips if entity type already has a workflow)
        with transaction.atomic():
            self.create_trf_workflow(admin_user)
            self.create_visa_workflow(admin_user)
            self.create_transport_workflow(admin_user)

        self.stdout.write(
            self.style.SUCCESS("✅ Successfully created all default workflows!")
        )
        self.stdout.write(self.style.SUCCESS(""))
        self.stdout.write(self.style.SUCCESS("Created workflows:"))
        for template in WorkflowTemplate.objects.all():
            step_count = template.steps.count()
            self.stdout.write(
                f"  - {template.name} ({template.entity_type}): {step_count} steps"
            )

    def _already_exists(self, entity_type: str) -> bool:
        """Return True if an active workflow already exists for this entity type."""
        exists = WorkflowTemplate.objects.filter(
            entity_type=entity_type, is_active=True
        ).exists()
        if exists:
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠ Skipping {entity_type} — active workflow already exists"
                )
            )
        return exists

    def create_trf_workflow(self, created_by):
        """Create TRF (Travel Request Form) workflow"""
        if self._already_exists("travelrequest"):
            return
        self.stdout.write("Creating TRF workflow...")

        template = WorkflowTemplate.objects.create(
            name="TRF Standard Approval Workflow",
            description="Standard approval workflow for Travel Request Forms (TRF)",
            entity_type="travelrequest",
            is_active=True,
            allow_parallel_steps=False,
            auto_approve_on_condition=False,
            created_by=created_by,
        )

        # Step 1: Department Focal
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=1,
            step_name="Department Focal Approval",
            step_description="Department Focal reviews and approves the travel request",
            approver_role="Department Focal",
            is_required=True,
            can_skip=False,
            requires_comments=False,
        )

        # Step 2: Line Manager
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=2,
            step_name="Line Manager Approval",
            step_description="Line Manager reviews and approves the travel request",
            approver_role="Line Manager",
            is_required=True,
            can_skip=False,
            requires_comments=False,
        )

        # Step 3: HOD
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=3,
            step_name="HOD Approval",
            step_description="Head of Department reviews and approves the travel request",
            approver_role="HOD",
            is_required=True,
            can_skip=False,
            requires_comments=False,
        )

        self.stdout.write(self.style.SUCCESS("  ✓ Created TRF workflow with 3 steps"))

    def create_visa_workflow(self, created_by):
        """Create Visa Application workflow"""
        if self._already_exists("visaapplication"):
            return
        self.stdout.write("Creating Visa Application workflow...")

        template = WorkflowTemplate.objects.create(
            name="Visa Application Standard Approval Workflow",
            description="Standard approval workflow for Visa Applications",
            entity_type="visaapplication",
            is_active=True,
            allow_parallel_steps=False,
            auto_approve_on_condition=False,
            created_by=created_by,
        )

        # Step 1: Department Focal
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=1,
            step_name="Department Focal Approval",
            step_description="Department Focal verifies visa application details",
            approver_role="Department Focal",
            is_required=True,
            can_skip=False,
            requires_comments=False,
        )

        # Step 2: Line Manager
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=2,
            step_name="Line Manager Approval",
            step_description="Line Manager approves the visa application",
            approver_role="Line Manager",
            is_required=True,
            can_skip=False,
            requires_comments=False,
        )

        # Step 3: HOD
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=3,
            step_name="HOD Approval",
            step_description="Head of Department approves the visa application",
            approver_role="HOD",
            is_required=True,
            can_skip=False,
            requires_comments=False,
        )

        # Step 4: Visa Admin (Final Processing)
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=4,
            step_name="Visa Admin Processing",
            step_description="Visa Admin processes the application with embassy",
            approver_role="Visa Admin",
            is_required=True,
            can_skip=False,
            requires_comments=False,
        )

        self.stdout.write(self.style.SUCCESS("  ✓ Created Visa workflow with 4 steps"))

    def create_transport_workflow(self, created_by):
        """Create Transport Request workflow"""
        if self._already_exists("transportrequest"):
            return
        self.stdout.write("Creating Transport Request workflow...")

        template = WorkflowTemplate.objects.create(
            name="Transport Request Standard Approval Workflow",
            description="Standard approval workflow for Transport Requests",
            entity_type="transportrequest",
            is_active=True,
            allow_parallel_steps=False,
            auto_approve_on_condition=False,
            created_by=created_by,
        )

        # Step 1: Department Focal
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=1,
            step_name="Department Focal Approval",
            step_description="Department Focal reviews transport requirements",
            approver_role="Department Focal",
            is_required=True,
            can_skip=False,
            requires_comments=False,
        )

        # Step 2: Line Manager
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=2,
            step_name="Line Manager Approval",
            step_description="Line Manager approves the transport request",
            approver_role="Line Manager",
            is_required=True,
            can_skip=False,
            requires_comments=False,
        )

        # Step 3: HOD
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=3,
            step_name="HOD Approval",
            step_description="Head of Department approves the transport request",
            approver_role="HOD",
            is_required=True,
            can_skip=False,
            requires_comments=False,
        )

        # Step 4: Transport Admin (Final Processing)
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=4,
            step_name="Transport Admin Processing",
            step_description="Transport Admin arranges vehicle and driver",
            approver_role="Transport Admin",
            is_required=True,
            can_skip=False,
            requires_comments=False,
        )

        self.stdout.write(
            self.style.SUCCESS("  ✓ Created Transport workflow with 4 steps")
        )

    def create_accommodation_workflow(self, created_by):
        """Create Accommodation Request workflow"""
        self.stdout.write("Creating Accommodation Request workflow...")

        template = WorkflowTemplate.objects.create(
            name="Accommodation Request Standard Approval Workflow",
            description="Standard approval workflow for Accommodation Requests (subset of TRF)",
            entity_type="travelrequest",  # Accommodation is part of TRF
            is_active=False,  # Inactive since TRF workflow handles this
            allow_parallel_steps=False,
            auto_approve_on_condition=False,
            created_by=created_by,
        )

        # Step 1: Department Focal
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=1,
            step_name="Department Focal Approval",
            step_description="Department Focal reviews accommodation needs",
            approver_role="Department Focal",
            is_required=True,
            can_skip=False,
            requires_comments=False,
        )

        # Step 2: Line Manager
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=2,
            step_name="Line Manager Approval",
            step_description="Line Manager approves the accommodation request",
            approver_role="Line Manager",
            is_required=True,
            can_skip=False,
            requires_comments=False,
        )

        # Step 3: HOD
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=3,
            step_name="HOD Approval",
            step_description="Head of Department approves the accommodation request",
            approver_role="HOD",
            is_required=True,
            can_skip=False,
            requires_comments=False,
        )

        # Step 4: Accommodation Admin
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=4,
            step_name="Accommodation Admin Processing",
            step_description="Accommodation Admin arranges booking",
            approver_role="Accommodation Admin",
            is_required=True,
            can_skip=False,
            requires_comments=False,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "  ✓ Created Accommodation workflow with 4 steps (inactive)"
            )
        )
