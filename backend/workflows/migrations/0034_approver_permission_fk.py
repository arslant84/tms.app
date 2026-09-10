"""
ERD fix roadmap, Phase 3 (docs/erd-fix-roadmap.md, Issue 5).

Adds a real DB-level FK from workflows_workflowstep.approver_permission to
accounts_permission.name, so a typo/renamed permission can no longer
silently orphan a workflow step's approver assignment. `approver_role`
(the older, now-`[DEPRECATED]` field per its own help_text in
workflows/models.py) is deliberately left as a plain column, matching the
roadmap's decision not to add a FK to a field being phased out.

Audited before adding this (both live data and the test suite, per the
lesson from the two reverted Phase 1 constraints):
- All 14 existing workflows_workflowstep rows have approver_permission =
  NULL (none use empty string), so the FK has zero existing violations - a
  NULL FK column is always valid regardless of the constraint.
- accounts_permission.name already has a UNIQUE constraint
  (accounts_permission_name_key), so it's a valid FK target.
- No test anywhere sets approver_permission to a value that wouldn't
  correspond to a real Permission row (grepped tests/ for
  "approver_permission=" - zero matches; the field is currently unused in
  both real data and the test suite, likely because adoption of the
  preferred approver_permission field over the deprecated approver_role
  hasn't happened yet, not because of any bug).
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0033_add_status_check_constraints"),
        ("accounts", "0046_grant_system_admin_department_focal_permissions"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE workflows_workflowstep
                ADD CONSTRAINT workflows_workflowstep_approver_permission_fkey
                FOREIGN KEY (approver_permission)
                REFERENCES accounts_permission (name)
                ON DELETE SET NULL
                ON UPDATE CASCADE
                DEFERRABLE INITIALLY DEFERRED;
            """,
            reverse_sql="""
                ALTER TABLE workflows_workflowstep
                DROP CONSTRAINT workflows_workflowstep_approver_permission_fkey;
            """,
        ),
    ]
