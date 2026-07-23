"""
Ensure all WorkflowSteps for the active travelrequest (TRF) template have
can_skip=True, matching every other entity type (accommodation,
transportrequest, visaapplication, combinedrequest all already True).

Found 2026-07-23: TRF was the only entity type where every step disallowed
skipping, so the frontend's "Skip this approver" option (shared across all
5 request apps via ApproverSelectionComponent) never appeared for TRF.
Migration 0009 already tried to set can_skip=True globally, and 0011 had
to re-apply the same fix specifically for combinedrequest after its steps
drifted back to False (edited via the workflow admin UI after 0009 ran) -
this is the same recurring drift, this time for travelrequest.
"""

from django.db import migrations


def enable_skip_for_travelrequest(apps, schema_editor):
    WorkflowTemplate = apps.get_model("workflows", "WorkflowTemplate")
    WorkflowStep = apps.get_model("workflows", "WorkflowStep")

    template = WorkflowTemplate.objects.filter(
        entity_type__iexact="travelrequest", is_active=True
    ).first()

    if not template:
        print("  No active travelrequest workflow template found — skipping")
        return

    updated = WorkflowStep.objects.filter(
        workflow_template=template, can_skip=False
    ).update(can_skip=True)

    print(f"  Updated {updated} travelrequest workflow step(s) to can_skip=True")


def reverse_noop(apps, schema_editor):
    # Reversing this is a no-op — we don't know which steps were False before
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0011_fix_combined_request_can_skip"),
    ]

    operations = [
        migrations.RunPython(enable_skip_for_travelrequest, reverse_noop),
    ]
