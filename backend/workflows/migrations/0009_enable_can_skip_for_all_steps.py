# Generated migration to enable can_skip for all workflow steps
# This fixes the issue where skipped approvers were being ignored because can_skip was False

from django.db import migrations


def enable_can_skip(apps, schema_editor):
    """
    Set can_skip=True for all workflow steps.
    This allows users to skip approvers when no approver is available for a step.
    """
    WorkflowStep = apps.get_model('workflows', 'WorkflowStep')
    updated_count = WorkflowStep.objects.filter(can_skip=False).update(can_skip=True)
    print(f"  Updated {updated_count} workflow steps to can_skip=True")


def disable_can_skip(apps, schema_editor):
    """
    Reverse: Set can_skip=False for all workflow steps.
    """
    WorkflowStep = apps.get_model('workflows', 'WorkflowStep')
    WorkflowStep.objects.all().update(can_skip=False)


class Migration(migrations.Migration):

    dependencies = [
        ('workflows', '0008_fix_uuid_primary_key'),
    ]

    operations = [
        migrations.RunPython(enable_can_skip, disable_can_skip),
    ]
