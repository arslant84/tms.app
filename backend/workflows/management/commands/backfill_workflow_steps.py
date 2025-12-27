from django.core.management.base import BaseCommand
from django.utils import timezone
from workflows.models import WorkflowInstance, WorkflowStepExecution
from datetime import timedelta


class Command(BaseCommand):
    help = 'Backfill step execution records for workflows that are missing them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--workflow-id',
            type=int,
            help='Backfill specific workflow by ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        workflow_id = options.get('workflow_id')

        # Find workflows that need backfilling
        if workflow_id:
            workflows = WorkflowInstance.objects.filter(id=workflow_id)
        else:
            # Find all workflows with no step executions
            workflows = WorkflowInstance.objects.filter(
                step_executions__isnull=True
            ).distinct()

        total = workflows.count()
        self.stdout.write(f"\nFound {total} workflows needing step execution backfill\n")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made\n"))

        backfilled = 0
        skipped = 0

        for workflow in workflows:
            if workflow.step_executions.count() > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping Workflow {workflow.id} - already has {workflow.step_executions.count()} steps"
                    )
                )
                skipped += 1
                continue

            # Get workflow template steps
            if not workflow.workflow_template:
                self.stdout.write(
                    self.style.ERROR(
                        f"Skipping Workflow {workflow.id} - no workflow template"
                    )
                )
                skipped += 1
                continue

            template_steps = workflow.workflow_template.steps.all().order_by('step_order')
            
            if not template_steps.exists():
                self.stdout.write(
                    self.style.ERROR(
                        f"Skipping Workflow {workflow.id} - template has no steps"
                    )
                )
                skipped += 1
                continue

            self.stdout.write(
                f"\nBackfilling Workflow {workflow.id} (Status: {workflow.status}, Template: {workflow.workflow_template.name})"
            )

            if not dry_run:
                # Create step executions based on workflow status
                step_count = template_steps.count()
                
                for idx, template_step in enumerate(template_steps):
                    # Calculate dates - spread steps evenly between started_at and completed_at
                    if workflow.started_at and workflow.completed_at:
                        total_duration = workflow.completed_at - workflow.started_at
                        step_duration = total_duration / step_count if step_count > 1 else timedelta(0)
                        action_date = workflow.started_at + (step_duration * idx)
                    else:
                        action_date = workflow.started_at or timezone.now()

                    # Determine step status based on workflow status
                    if workflow.status == 'approved':
                        step_status = 'approved'
                    elif workflow.status == 'rejected':
                        # All steps before current are approved, current is rejected, rest are skipped
                        if idx < workflow.current_step_order - 1:
                            step_status = 'approved'
                        elif idx == workflow.current_step_order - 1:
                            step_status = 'rejected'
                        else:
                            step_status = 'skipped'
                    elif workflow.status == 'in_progress':
                        # Steps before current are approved, current is pending, rest are pending
                        if idx < workflow.current_step_order - 1:
                            step_status = 'approved'
                        else:
                            step_status = 'pending'
                            action_date = None  # Pending steps have no action date
                    else:
                        step_status = 'pending'
                        action_date = None

                    step_execution = WorkflowStepExecution.objects.create(
                        workflow_instance=workflow,
                        workflow_step=template_step,
                        status=step_status,
                        action_date=action_date,
                        assigned_to=workflow.initiated_by if step_status == 'pending' else None,
                        actioned_by=workflow.initiated_by if step_status in ['approved', 'rejected'] else None,
                        comments=f"Backfilled - {workflow.status} workflow"
                    )

                    self.stdout.write(
                        f"  ✓ Created step {template_step.step_order}: {template_step.step_name} "
                        f"({step_status})"
                    )

                backfilled += 1
            else:
                for template_step in template_steps:
                    self.stdout.write(
                        f"  Would create: Step {template_step.step_order}: {template_step.step_name}"
                    )

        self.stdout.write("\n" + "="*50)
        self.stdout.write(
            self.style.SUCCESS(
                f"\nBackfill complete!\n"
                f"  Backfilled: {backfilled}\n"
                f"  Skipped: {skipped}\n"
                f"  Total: {total}\n"
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nThis was a dry run. Run without --dry-run to apply changes."
                )
            )
