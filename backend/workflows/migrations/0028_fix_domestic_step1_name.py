"""
0026_seed_approval_stage_notifications fixed Domestic TSR's first step's
approver_role from Department Focal to Line Manager, but left step_name as
the free-text label "Step 1: Department Focal Approval" - a cosmetic
mismatch between who the step is actually assigned to and what the
Workflow Configuration screen displays it as. Matches the label format
Overseas/External Parties already use for their own Line Manager step.
"""

from django.db import migrations


def fix_step_name(apps, schema_editor):
    WorkflowStep = apps.get_model("workflows", "WorkflowStep")
    WorkflowStep.objects.filter(
        workflow_template__entity_type="travelrequest_domestic",
        step_order=1,
        step_name="Step 1: Department Focal Approval",
    ).update(step_name="Step 1: Line Manager Approval")


def reverse_step_name(apps, schema_editor):
    WorkflowStep = apps.get_model("workflows", "WorkflowStep")
    WorkflowStep.objects.filter(
        workflow_template__entity_type="travelrequest_domestic",
        step_order=1,
        step_name="Step 1: Line Manager Approval",
    ).update(step_name="Step 1: Department Focal Approval")


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0027_seed_post_approval_fulfillment_notifications"),
    ]

    operations = [
        migrations.RunPython(fix_step_name, reverse_step_name),
    ]
