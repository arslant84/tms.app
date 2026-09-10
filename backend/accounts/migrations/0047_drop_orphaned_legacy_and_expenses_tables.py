"""
ERD fix roadmap, Phase 4 (docs/erd-fix-roadmap.md, Issues 1 and 2).

Drops two groups of tables confirmed to have zero references anywhere in
the current application code:

1. Four pre-Django tables (`users`, `travel_requests`, `audit_logs`,
   `alembic_version`) left over from before this backend was migrated from
   FastAPI/SQLAlchemy to Django (git commit `0d276763`, "Migrate backend
   from FastAPI to Django while maintaining Angular frontend"). `users` and
   `travel_requests` are dead duplicates of `accounts_user` and
   `trf_travelrequest`; `alembic_version` is Alembic/SQLAlchemy migration
   bookkeeping this project hasn't used since that migration.

2. Four tables belonging to the `expenses` Django app, which was deleted
   entirely in commit `394d3658` ("fixes on notification and dashboard
   layout") - the app's model/view/serializer code was removed, but its
   migrations were never reverted first, so the tables (and their
   `django_migrations` history rows) were simply left behind with no
   owning app.

Attached to `accounts` (not a dedicated app - none of these tables belong
to any current app) since it's the most foundational app in this project.

A full pg_dump backup of the database was taken immediately before this
migration was written/applied (see backups/ in the repo root, gitignored)
specifically so this could be restored wholesale if anything unexpected
turns up. This migration's own reverse is deliberately a documented no-op:
recreating the exact legacy pre-Django schema (down to its original
constraints/sequences) is out of scope, and restoring from that backup is
the real rollback mechanism for this step - not something a reverse
migration can usefully automate.
"""

from django.db import migrations

LEGACY_TABLES = ["audit_logs", "travel_requests", "users", "alembic_version"]
EXPENSES_TABLES = [
    "expenses_claimsapprovalstep",
    "expenses_expenseclaim_items",
    "expenses_expenseitem",
    "expenses_expenseclaim",
]


def drop_orphaned_tables(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        for table in LEGACY_TABLES + EXPENSES_TABLES:
            cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
        # Clean up the stale expenses migration history rows too, so
        # `showmigrations`/`makemigrations` stop referencing an app that no
        # longer exists in INSTALLED_APPS.
        cursor.execute("DELETE FROM django_migrations WHERE app = %s;", ["expenses"])


def noop_reverse(apps, schema_editor):
    # Irreversible by design - see the module docstring. Restore from the
    # pg_dump backup taken alongside this migration if these tables are
    # ever needed again.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0046_grant_system_admin_department_focal_permissions"),
    ]

    operations = [
        migrations.RunPython(drop_orphaned_tables, noop_reverse),
    ]
