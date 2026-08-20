"""
Management command to populate default WorkflowStepNotificationConfig records
for all existing workflow steps that don't have notification configs.

This makes the current default notification behavior visible and editable in the UI.
"""

from django.core.management.base import BaseCommand
from notifications.models import NotificationTemplate
from workflows.models import WorkflowStep, WorkflowStepNotificationConfig


class Command(BaseCommand):
    help = "Populate default notification configs for existing workflow steps"

    # Mapping of event types to their default configuration
    DEFAULT_CONFIGS = {
        "assignment": {
            "template_name": "approval_required",
            "recipient_types": ["current_approver"],
            "priority": "high",
            "description": "Notify the approver when step is assigned",
        },
        "approval": {
            "template_name": "workflow_completed",  # or step_assigned for intermediate
            "recipient_types": ["requester"],
            "priority": "normal",
            "description": "Notify the requester when step is approved",
        },
        "rejection": {
            "template_name": "workflow_rejected",
            "recipient_types": ["requester"],
            "priority": "urgent",
            "description": "Notify the requester when request is rejected",
        },
        "delegation": {
            "template_name": "delegation_confirmed",
            "recipient_types": ["current_approver"],
            "priority": "high",
            "description": "Notify the new assignee when step is delegated",
        },
        "workflow_completed": {
            "template_name": "workflow_completed",
            "recipient_types": ["requester"],
            "priority": "high",
            "description": "Notify the requester when all approvals are complete",
        },
        "workflow_cancelled": {
            "template_name": "workflow_cancelled",
            "recipient_types": ["requester"],
            "priority": "normal",
            "description": "Notify the requester when the workflow is cancelled",
        },
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating",
        )
        parser.add_argument(
            "--workflow-id",
            type=str,
            help="Only process a specific workflow template ID",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        workflow_id = options.get("workflow_id")

        # Get all workflow steps
        steps = WorkflowStep.objects.select_related("workflow_template")
        if workflow_id:
            steps = steps.filter(workflow_template_id=workflow_id)

        self.stdout.write(f"Found {steps.count()} workflow steps to process")

        # Load notification templates
        templates = {}
        for template_name in set(
            cfg["template_name"] for cfg in self.DEFAULT_CONFIGS.values()
        ):
            try:
                templates[template_name] = NotificationTemplate.objects.get(
                    name=template_name
                )
            except NotificationTemplate.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"Template '{template_name}' not found - will skip configs using it"
                    )
                )

        created_count = 0
        skipped_count = 0

        for step in steps:
            self.stdout.write(
                f"\nProcessing: {step.workflow_template.name} - {step.step_name}"
            )

            for event_type, config in self.DEFAULT_CONFIGS.items():
                # Check if config already exists
                existing = WorkflowStepNotificationConfig.objects.filter(
                    workflow_step=step, event_type=event_type
                ).exists()

                if existing:
                    self.stdout.write(f"  [{event_type}] Already configured - skipping")
                    skipped_count += 1
                    continue

                # Get template
                template = templates.get(config["template_name"])
                if not template:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [{event_type}] Template not found - skipping"
                        )
                    )
                    skipped_count += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [{event_type}] Would create config with template '{config['template_name']}'"
                        )
                    )
                else:
                    WorkflowStepNotificationConfig.objects.create(
                        workflow_step=step,
                        event_type=event_type,
                        notification_template=template,
                        recipient_types=config["recipient_types"],
                        custom_recipients=[],
                        is_active=True,
                        send_email=True,
                        send_system_notification=True,
                        priority=config["priority"],
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [{event_type}] Created config with template '{config['template_name']}'"
                        )
                    )

                created_count += 1

        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: Would create {created_count} configs")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Created {created_count} notification configs")
            )
        self.stdout.write(
            f"Skipped {skipped_count} (already exist or template missing)"
        )
