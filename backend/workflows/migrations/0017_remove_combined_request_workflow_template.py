"""
Remove the WorkflowTemplate (and its WorkflowSteps, cascade) for
entity_type='combinedrequest'. The Combined Request module has been fully
deleted per user request - see
docs/COMBINED_REQUEST_MODULE_REMOVAL_ROADMAP.md. Any in-flight
WorkflowInstance/WorkflowStepExecution rows referencing this template are
already orphaned since the combined_request app and its models are gone.
"""

from django.db import migrations


def remove_combined_request_template(apps, schema_editor):
    WorkflowTemplate = apps.get_model("workflows", "WorkflowTemplate")
    WorkflowTemplate.objects.filter(entity_type__iexact="combinedrequest").delete()


def reverse_noop(apps, schema_editor):
    # Reversing this is a no-op - the template's steps/config are not restored.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0016_enable_can_skip_for_all_steps_again"),
    ]

    operations = [
        migrations.RunPython(remove_combined_request_template, reverse_noop),
    ]
