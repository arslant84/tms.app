"""
ERD fix roadmap, Phase 1 (docs/erd-fix-roadmap.md, Issue 13).

Adds DB-level CHECK constraints on workflows_workflowinstance.status and
workflows_workflowstepexecution.status, matching each model's own Django
`choices=` exactly.

This follows migration 0032, which added "completed" as a real declared
choice on WorkflowInstance.status - a first attempt at this constraint
(since reverted) broke tests/visa/test_services.py because
visa/services.py's finalize_visa_workflow_completion() sets exactly that
value to mean "approved AND post-approval processing is also done", and
it was never actually invalid, just undeclared. Audited every direct
`.status = "..."` assignment on both models across the non-test codebase
(workflows/engine.py, workflows/views.py, visa/services.py,
accommodation/services.py) before adding this - the only other
out-of-choices usage found (accommodation/services.py's own "completed"
step-execution/instance assignment) is unreachable dead code guarded by a
bare `except Exception` around an import of a model class that doesn't
exist (`StepExecution` vs. the real `WorkflowStepExecution`), so it never
executes and doesn't affect this constraint.

Deliberately NOT touching trf_travelrequest.status, visa_visaapplication.
status, transport_transportrequest.status, or accommodation_
accommodationrequest.status - see the note in migration 0032's sibling
discussion in docs/erd-fix-roadmap.md: those four are intentionally
dynamic (workflow-engine-driven, no fixed choices by design).
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0032_add_completed_to_workflowinstance_status_choices"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE workflows_workflowinstance
                ADD CONSTRAINT workflows_workflowinstance_status_valid
                CHECK (status IN ('pending', 'in_progress', 'approved', 'rejected', 'cancelled', 'on_hold', 'completed'));
            """,
            reverse_sql="""
                ALTER TABLE workflows_workflowinstance
                DROP CONSTRAINT workflows_workflowinstance_status_valid;
            """,
        ),
        migrations.RunSQL(
            sql="""
                ALTER TABLE workflows_workflowstepexecution
                ADD CONSTRAINT workflows_workflowstepexecution_status_valid
                CHECK (status IN ('waiting', 'pending', 'approved', 'rejected', 'skipped', 'delegated'));
            """,
            reverse_sql="""
                ALTER TABLE workflows_workflowstepexecution
                DROP CONSTRAINT workflows_workflowstepexecution_status_valid;
            """,
        ),
    ]
