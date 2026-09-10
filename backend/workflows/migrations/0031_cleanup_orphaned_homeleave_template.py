"""
Clean up the orphaned "TSR - Home Leave Approval Workflow" WorkflowTemplate
(entity_type="travelrequest_homeleave").

Home Leave Passage was removed entirely from the app (2026-08-31, see
`bddf6586` and ARCHITECTURE.md's "Home Leave Passage removed entirely"
note): TravelRequest.WORKFLOW_ENTITY_TYPE_MAP has no "Home Leave" key, the
frontend TRF wizard's travel-type union doesn't offer it, and nothing else
in the codebase can produce a TravelRequest whose workflow_entity_type
property ever resolves to "travelrequest_homeleave". The template was left
behind as an orphaned, already-inactive row instead of being deleted at the
time.

WorkflowTemplate -> WorkflowInstance is on_delete=CASCADE, so deleting a
template with real historical WorkflowInstance rows against it (from back
when Home Leave Passage was live) would silently destroy that approval
history. This migration only deletes the template outright when nothing
references it; if any WorkflowInstance rows exist, it leaves the row alone
(already correctly is_active=False) and just makes the orphaned status
explicit in its name/description, so it stops reading as ambiguous "why is
this still Inactive" - config in the admin Configured Workflows list.
"""

from django.db import migrations

ENTITY_TYPE = "travelrequest_homeleave"
ORPHANED_NAME = "TSR - Home Leave Approval Workflow (orphaned - Home Leave Passage removed 2026-08-31)"
ORPHANED_DESCRIPTION = (
    "Home Leave Passage was removed entirely from the application on "
    "2026-08-31. No code path can ever route a request to this template - "
    "TravelRequest.WORKFLOW_ENTITY_TYPE_MAP has no 'Home Leave' key and the "
    "frontend no longer offers it as a travel type. Kept (not deleted) "
    "because real historical WorkflowInstance records still reference it; "
    "deleting the template would cascade-delete that approval history."
)


def cleanup_or_annotate_orphaned_template(apps, schema_editor):
    WorkflowTemplate = apps.get_model("workflows", "WorkflowTemplate")
    WorkflowInstance = apps.get_model("workflows", "WorkflowInstance")

    template = WorkflowTemplate.objects.filter(entity_type=ENTITY_TYPE).first()
    if not template:
        return

    has_history = WorkflowInstance.objects.filter(workflow_template=template).exists()
    if has_history:
        template.name = ORPHANED_NAME
        template.description = ORPHANED_DESCRIPTION
        template.is_active = False
        template.save(update_fields=["name", "description", "is_active"])
    else:
        template.delete()


def noop_reverse(apps, schema_editor):
    # Irreversible by design: whether the forward pass deleted the row or
    # just renamed it depends on data present at migrate time in each
    # environment, so there's nothing generic to restore here.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0030_seed_fully_arranged_notifications"),
    ]

    operations = [
        migrations.RunPython(cleanup_or_annotate_orphaned_template, noop_reverse),
    ]
