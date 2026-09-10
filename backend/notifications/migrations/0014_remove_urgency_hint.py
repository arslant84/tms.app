"""
Removes the "Urgency" line from the 'approval_required' NotificationTemplate
and the 'urgencyHint' entry from its variables_available list.

urgencyHint was rendered by workflows/notification_dispatch.py as
"High priority" if step_execution.workflow_step.is_urgent else "Normal
priority" - but WorkflowStep has no is_urgent field and never has (checked
the full model definition), so getattr(..., "is_urgent", False) always fell
through to its default, and every approval email has always rendered
"Urgency: Normal priority" regardless of the actual request. Not
configurable anywhere - no admin toggle, no per-step/per-request field, no
other code path setting or reading it. Removing the misleading line rather
than wiring up a real is_urgent field, per explicit decision (2026-09-09).
"""

from django.db import migrations

BODY_WITH_URGENCY = (
    "Hi {{approverName}},\n\n"
    "A **{{requestType}}** request (ID: **#{{entityId}}**) from **{{requestorName}}** "
    "requires your approval.\n\n"
    "**Details:**\n"
    "*   **Requestor:** {{requestorName}}\n"
    "*   **Urgency:** {{urgencyHint}}\n\n"
    "Please review the request and take action.\n\n"
    "[Review & Approve]({{actionUrl}})\n\n"
    "Thank you,\n"
    "The TMS Team"
)

BODY_WITHOUT_URGENCY = (
    "Hi {{approverName}},\n\n"
    "A **{{requestType}}** request (ID: **#{{entityId}}**) from **{{requestorName}}** "
    "requires your approval.\n\n"
    "**Details:**\n"
    "*   **Requestor:** {{requestorName}}\n\n"
    "Please review the request and take action.\n\n"
    "[Review & Approve]({{actionUrl}})\n\n"
    "Thank you,\n"
    "The TMS Team"
)


def remove_urgency_hint(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    template = NotificationTemplate.objects.filter(name="approval_required").first()
    if not template:
        return
    template.body = BODY_WITHOUT_URGENCY
    template.variables_available = [
        v for v in template.variables_available if v != "urgencyHint"
    ]
    template.save(update_fields=["body", "variables_available"])


def restore_urgency_hint(apps, schema_editor):
    NotificationTemplate = apps.get_model("notifications", "NotificationTemplate")
    template = NotificationTemplate.objects.filter(name="approval_required").first()
    if not template:
        return
    template.body = BODY_WITH_URGENCY
    if "urgencyHint" not in template.variables_available:
        template.variables_available = [*template.variables_available, "urgencyHint"]
    template.save(update_fields=["body", "variables_available"])


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0013_add_fully_arranged_template"),
    ]

    operations = [
        migrations.RunPython(remove_urgency_hint, restore_urgency_hint),
    ]
