"""
One-time data migration: brings every active TSR/Visa/Transport workflow
template's approval-stage configuration (step roles + notification configs)
in line with docs/TMS_Responsibility_Matrix.xlsx, using the existing
WorkflowStep / WorkflowStepNotificationConfig models only - nothing here is
hardcoded in application code. After this runs, every value it sets is
plain data, editable the same way as anything else through the existing
Workflow Configuration / Notification Config admin screens.

What this fixes, per module (see the matrix's per-sheet "System
Notification / Next Step" column):

1. Domestic TSR's first approval step is currently assigned the
   "Department Focal" role. The matrix (and Overseas/External Parties,
   which already have this right) wants Line Manager first, then HOD.
   Department Focal is not an approver anywhere in the matrix - it only
   receives the final completion notice, handled separately by
   trf.services.notify_department_focal_if_ready().

2. The 'approval' event (fires every time *any* step approves, not just
   the last one) has always pointed at the 'workflow_completed' template
   for every step - "fully approved and processed" wording that's wrong
   on an intermediate step. This repoints every non-final step's
   'approval' config to the new 'step_approved' template (added in
   notifications/0012) and leaves the final step's 'approval' config
   pointing at 'workflow_completed', which is correct there.

3. Bug fix: several templates *also* have a 'workflow_completed' event
   config on top of 'approval' on the same (final) step - both fire on
   the same event with near-identical content, so the requester gets two
   emails. WorkflowNotifications.notify_workflow_completed() already
   skips its own default send when the final step has a configured
   'approval' notification (see workflows/notifications.py), so once
   every final step has that (per point 2), the separate 'workflow_completed'
   event config is redundant everywhere - not just on the templates where
   it was actually duplicating today. Removed globally.

4. 'workflow_cancelled' needs a config on *every* step (a request can be
   cancelled while any step is pending - see notify_workflow_cancelled(),
   which looks up the config by whichever step is currently active), but
   Domestic, External Parties and Visa are missing it on some or all
   steps. Filled in everywhere it's missing.

5. Visa's first step is missing a 'workflow_started' config entirely, so
   the requester currently gets no "your request has been submitted"
   email for Visa specifically. Added.

'assignment'/'delegation'/'rejection' were already present and correct on
every step of every template - not touched.

Idempotent: safe to re-run (get_or_create / filter-then-create throughout).
"""

from django.db import migrations


def seed_approval_stage_notifications(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    WorkflowStep = apps.get_model("workflows", "WorkflowStep")
    WorkflowStepNotificationConfig = apps.get_model(
        "workflows", "WorkflowStepNotificationConfig"
    )
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")

    workflow_completed_template = NotificationTemplate.objects.filter(
        name="workflow_completed"
    ).first()
    step_approved_template = NotificationTemplate.objects.filter(
        name="step_approved"
    ).first()
    workflow_cancelled_template = NotificationTemplate.objects.filter(
        name="workflow_cancelled"
    ).first()
    workflow_started_template = NotificationTemplate.objects.filter(
        name="workflow_started"
    ).first()

    if not (
        workflow_completed_template
        and step_approved_template
        and workflow_cancelled_template
        and workflow_started_template
    ):
        # Required templates missing (e.g. running against a DB that never
        # had the earlier seed migrations applied) - nothing safe to do.
        return

    # --- 1. Fix Domestic's first-step role: Department Focal -> Line Manager ---
    line_manager_role = Role.objects.filter(name="Line Manager").first()
    if line_manager_role:
        WorkflowStep.objects.filter(
            workflow_template__entity_type="travelrequest_domestic",
            step_order=1,
        ).update(approver_role=str(line_manager_role.id))

    # --- 2-5. Per-template step notification config cleanup ---
    for step in WorkflowStep.objects.filter(
        is_active=True, workflow_template__is_active=True
    ).select_related("workflow_template"):
        template = step.workflow_template
        last_step_order = (
            WorkflowStep.objects.filter(workflow_template=template, is_active=True)
            .order_by("-step_order")
            .values_list("step_order", flat=True)
            .first()
        )
        is_last_step = step.step_order == last_step_order

        # (2) 'approval' event: step_approved for intermediate steps,
        # workflow_completed for the final one.
        approval_template = (
            workflow_completed_template if is_last_step else step_approved_template
        )
        WorkflowStepNotificationConfig.objects.update_or_create(
            workflow_step=step,
            event_type="approval",
            defaults={
                "notification_template": approval_template,
                "recipient_types": ["requester"],
                "custom_recipients": [],
                "is_active": True,
                "send_email": True,
                "send_system_notification": True,
                "priority": "normal",
            },
        )

        # (3) Remove the redundant 'workflow_completed' event config - the
        # 'approval' config above already covers the final step, and a
        # separate 'workflow_completed' config on top of it double-sends.
        WorkflowStepNotificationConfig.objects.filter(
            workflow_step=step, event_type="workflow_completed"
        ).delete()

        # (4) Every step needs 'workflow_cancelled' - cancellation can
        # happen while any step is the active one.
        WorkflowStepNotificationConfig.objects.get_or_create(
            workflow_step=step,
            event_type="workflow_cancelled",
            defaults={
                "notification_template": workflow_cancelled_template,
                "recipient_types": ["requester"],
                "custom_recipients": [],
                "is_active": True,
                "send_email": True,
                "send_system_notification": True,
                "priority": "normal",
            },
        )

        # (5) First step needs 'workflow_started'.
        if step.step_order == 1:
            WorkflowStepNotificationConfig.objects.get_or_create(
                workflow_step=step,
                event_type="workflow_started",
                defaults={
                    "notification_template": workflow_started_template,
                    "recipient_types": ["requester"],
                    "custom_recipients": [],
                    "is_active": True,
                    "send_email": True,
                    "send_system_notification": True,
                    "priority": "normal",
                },
            )


def reverse_noop(apps, schema_editor):
    # Deliberate data correction, not meant to be un-applied - reverting the
    # role fix and template reassignments would just restore the bugs this
    # migration fixes. No-op so `migrate` can still step back past this one
    # without erroring.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0025_workflowstep_is_active"),
        ("notifications", "0012_add_step_approved_template"),
        ("accounts", "0008_populate_roles_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_approval_stage_notifications, reverse_noop),
    ]
