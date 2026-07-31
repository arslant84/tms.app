"""
Blanket re-application of migration 0009's fix, same reasoning as 0011/0012/0015:
enhanced-workflow-config.component.ts's saveWorkflow() hardcoded
can_skip: false for every step it creates or updates (the admin form has no
per-step toggle for it), so any workflow created or edited through that
screen since 0009 ran - regardless of module - drifted back to can_skip=False.
Found 2026-07-31 via a freshly created "TSR - Overseas" workflow (Line
Manager/HOD/CEO steps) whose "Skip this approver" option never appeared.

This time the actual root cause is fixed too (saveWorkflow() now sends
can_skip: true), so this should be the last time this specific migration
needs re-applying - see docs/TSR_SUBMODULE_WORKFLOW_ROADMAP.md.
"""

from django.db import migrations


def enable_can_skip(apps, schema_editor):
    WorkflowStep = apps.get_model("workflows", "WorkflowStep")
    updated_count = WorkflowStep.objects.filter(can_skip=False).update(can_skip=True)
    print(f"  Updated {updated_count} workflow step(s) to can_skip=True")


def reverse_noop(apps, schema_editor):
    # Reversing this is a no-op - we don't know which steps were False before
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0015_fix_accommodation_can_skip"),
    ]

    operations = [
        migrations.RunPython(enable_can_skip, reverse_noop),
    ]
