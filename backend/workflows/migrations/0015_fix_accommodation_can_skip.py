"""
Ensure all WorkflowSteps for the active accommodation template have
can_skip=True, matching every other entity type (transportrequest,
travelrequest, visaapplication, combinedrequest all already True).

Found 2026-07-29 while closing out docs/APP_WIDE_GAPS_FIX_ROADMAP.md's
remaining gaps: accommodation's single step had drifted to can_skip=False
(edited via the workflow admin UI, same as every prior occurrence of this
drift). This is the third time this exact drift has been found and fixed -
0011 for combinedrequest, 0012 for travelrequest, this one for
accommodation - following the identical pattern each time.
"""

from django.db import migrations


def enable_skip_for_accommodation(apps, schema_editor):
    WorkflowTemplate = apps.get_model("workflows", "WorkflowTemplate")
    WorkflowStep = apps.get_model("workflows", "WorkflowStep")

    template = WorkflowTemplate.objects.filter(
        entity_type__iexact="accommodation", is_active=True
    ).first()

    if not template:
        print("  No active accommodation workflow template found — skipping")
        return

    updated = WorkflowStep.objects.filter(
        workflow_template=template, can_skip=False
    ).update(can_skip=True)

    print(f"  Updated {updated} accommodation workflow step(s) to can_skip=True")


def reverse_noop(apps, schema_editor):
    # Reversing this is a no-op — we don't know which steps were False before
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0014_workflowstepexecution_reminder_sent_at"),
    ]

    operations = [
        migrations.RunPython(enable_skip_for_accommodation, reverse_noop),
    ]
