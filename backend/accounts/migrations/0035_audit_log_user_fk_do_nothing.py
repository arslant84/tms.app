"""
Migration: allow AdminActionLog.user_id to be SET NULL when the referenced
user is deleted, while keeping all other fields immutable.

The original trigger (0033) blocked every UPDATE unconditionally.
When Django cascades a user DELETE with on_delete=SET_NULL it issues:

    UPDATE accounts_adminactionlog SET user_id = NULL
    WHERE user_id = <deleted-user-id>

The updated trigger permits exactly that operation — user_id changing from
a non-NULL value to NULL while every other column stays identical — and
still rejects any other in-place modification.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

TRIGGER_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION accounts_audit_log_prevent_update()
RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    -- Allow the single permitted mutation: nulling user_id when the
    -- referenced user account is deleted (Django SET_NULL cascade).
    IF (
        OLD.user_id IS NOT NULL AND NEW.user_id IS NULL AND
        OLD.id              = NEW.id              AND
        OLD.action_type     = NEW.action_type     AND
        OLD.entity_type     = NEW.entity_type     AND
        OLD.entity_id       = NEW.entity_id       AND
        OLD.description     = NEW.description     AND
        OLD.ip_address      IS NOT DISTINCT FROM NEW.ip_address AND
        OLD.user_agent      IS NOT DISTINCT FROM NEW.user_agent AND
        OLD.created_at      = NEW.created_at
    ) THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION
        'accounts_adminactionlog rows are immutable. '
        'Audit log entries cannot be modified after creation.';
END;
$$;
"""

# Reverse: restore the original all-blocking trigger function
REVERSE_TRIGGER_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION accounts_audit_log_prevent_update()
RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION
        'accounts_adminactionlog rows are immutable. '
        'Audit log entries cannot be modified after creation.';
END;
$$;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0034_database_backup"),
    ]

    operations = [
        # 1. Revert FK to SET_NULL (the correct Django-level setting).
        migrations.AlterField(
            model_name="adminactionlog",
            name="user",
            field=models.ForeignKey(
                blank=True,
                help_text="User who performed the action",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="audit_logs",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # 2. Update the trigger function to permit user_id → NULL only.
        migrations.RunSQL(
            sql=TRIGGER_FUNCTION_SQL,
            reverse_sql=REVERSE_TRIGGER_FUNCTION_SQL,
        ),
    ]
