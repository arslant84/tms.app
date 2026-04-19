"""
Ensure all WorkflowSteps for the combinedrequest template
have can_skip=True so the approver-selection UI shows
the Skip option.  Travel Desk (step 4) is intentionally
kept as skippable=True as well — admins can restrict it
via the workflow admin UI if needed.
"""

from django.db import migrations


def enable_skip_for_combined(apps, schema_editor):
    WorkflowTemplate = apps.get_model('workflows', 'WorkflowTemplate')
    WorkflowStep = apps.get_model('workflows', 'WorkflowStep')

    template = WorkflowTemplate.objects.filter(
        entity_type__iexact='combinedrequest',
        is_active=True
    ).first()

    if not template:
        print("  No active combinedrequest workflow template found — skipping")
        return

    updated = WorkflowStep.objects.filter(
        workflow_template=template,
        can_skip=False
    ).update(can_skip=True)

    print(f"  Updated {updated} combinedrequest workflow step(s) to can_skip=True")


def reverse_noop(apps, schema_editor):
    # Reversing this is a no-op — we don't know which steps were False before
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('workflows', '0010_alter_workflowstep_can_skip_and_more'),
    ]

    operations = [
        migrations.RunPython(enable_skip_for_combined, reverse_noop),
    ]
