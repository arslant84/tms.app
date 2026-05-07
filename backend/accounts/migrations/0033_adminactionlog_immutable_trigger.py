"""
Migration: make AdminActionLog rows immutable (UPDATE blocked at DB level).

Satisfies CTRL-0000001603 — logs must be protected against tampering.
A PostgreSQL trigger raises an exception if any code attempts to UPDATE
an existing audit log row. INSERT and DELETE remain permitted so that:
  - New log entries can be written (INSERT).
  - The DBA can purge old entries after the legal retention period (DELETE).

The trigger does NOT prevent deletion because authorised cleanup (e.g. after
7-year retention) is a legitimate operation performed by the DBA — it only
protects against in-place modification of individual records.
"""

from django.db import migrations


TRIGGER_FUNCTION_SQL = """
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

TRIGGER_SQL = """
CREATE TRIGGER audit_log_immutable
BEFORE UPDATE ON accounts_adminactionlog
FOR EACH ROW EXECUTE FUNCTION accounts_audit_log_prevent_update();
"""

DROP_TRIGGER_SQL = "DROP TRIGGER IF EXISTS audit_log_immutable ON accounts_adminactionlog;"
DROP_FUNCTION_SQL = "DROP FUNCTION IF EXISTS accounts_audit_log_prevent_update();"


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0032_user_password_last_changed_access_review"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[TRIGGER_FUNCTION_SQL, TRIGGER_SQL],
            reverse_sql=[DROP_TRIGGER_SQL, DROP_FUNCTION_SQL],
        ),
    ]
