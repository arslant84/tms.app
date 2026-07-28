"""
Approval-reminder notifications for pending workflow steps.

The 'reminder' WorkflowStepNotificationConfig event type has existed since
the model was created and is selectable in the admin UI's notification
config screen, but until this command nothing ever fired it - there was no
periodic check anywhere in the codebase. This closes that gap using the
same "self-installing crontab" pattern already established for
disable_inactive_accounts / cleanup_expired_data (see
backend/accounts/management/commands/install_cron.py) - no Celery/APScheduler
dependency added, matching this project's deliberate choice to not run a
background worker process (see docs/ARCHITECTURE.md §7.3).

A pending step execution gets exactly one reminder, when its SLA due date is
within 24 hours (or already passed) - the same 24-hour "due soon" threshold
the frontend already uses (isOverdueSoon() in approvals-dashboard.component.ts)
- and only if reminder_sent_at is still null. Sending goes through
WorkflowNotifications.trigger_configured_notifications(step_execution, 'reminder'),
the same config-driven dispatch every other event type uses: an admin-configured
WorkflowStepNotificationConfig is used if one exists for that step, otherwise
falls back to a default notification.

Run periodically (e.g. hourly via cron or Task Scheduler):

    python manage.py send_step_reminders
    python manage.py send_step_reminders --dry-run
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

REMINDER_WINDOW_HOURS = 24


class Command(BaseCommand):
    help = (
        "Send a one-shot 'reminder' notification for pending workflow steps "
        "whose SLA due date is within 24 hours (or already passed)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report which step executions would be reminded without sending anything.",
        )

    def handle(self, *args, **options):
        from workflows.models import WorkflowStepExecution
        from workflows.notifications import WorkflowNotifications

        dry_run = options["dry_run"]
        now = timezone.now()
        cutoff = now + timedelta(hours=REMINDER_WINDOW_HOURS)

        candidates = WorkflowStepExecution.objects.filter(
            status="pending",
            sla_due_date__isnull=False,
            sla_due_date__lte=cutoff,
            reminder_sent_at__isnull=True,
        ).select_related(
            "workflow_instance",
            "workflow_instance__workflow_template",
            "workflow_step",
            "assigned_to",
        )

        count = candidates.count()

        self.stdout.write(
            self.style.WARNING(
                f"{'[DRY RUN] ' if dry_run else ''}Reminder window: due within "
                f"{REMINDER_WINDOW_HOURS}h of {now.isoformat()} | Candidates: {count}"
            )
        )

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No pending steps need a reminder."))
            return

        for step_execution in candidates:
            entity_type = step_execution.workflow_instance.workflow_template.entity_type
            self.stdout.write(
                f"  - {entity_type} #{step_execution.workflow_instance.object_id} "
                f"/ step '{step_execution.workflow_step.step_name}' "
                f"due {step_execution.sla_due_date.isoformat()}"
            )

            if not dry_run:
                WorkflowNotifications.trigger_configured_notifications(
                    step_execution, "reminder"
                )
                step_execution.reminder_sent_at = now
                step_execution.save(update_fields=["reminder_sent_at"])

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"[DRY RUN] Would remind {count} step(s).")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Sent reminders for {count} step(s).")
            )
