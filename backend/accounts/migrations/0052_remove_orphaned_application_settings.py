# Generated manually on 2026-09-16

from django.db import migrations

ORPHANED_SETTING_KEYS = [
    # Superseded by 'application_name' (0006_populate_default_settings) — never read by any code
    "app_name",
    "app_description",
    # Superseded by 'session_timeout_minutes' (0006_populate_default_settings)
    "session_timeout",
    # Superseded by 'enable_email_notifications' (0006_populate_default_settings)
    "email_enabled",
    "email_notifications_enabled",
    # Never consulted by any middleware/view/service
    "notifications_enabled",
    "auto_approval_threshold",
    "require_manager_approval",
    "require_finance_approval",
    "maintenance_message",
    # Email/SMTP config is env-var only (see 0013_remove_email_settings_from_db);
    # kept here in case setup_default_settings was re-run after that migration
    "smtp_host",
    "smtp_port",
    "smtp_use_tls",
    "smtp_username",
    "smtp_password",
    "default_from_email",
]


def remove_orphaned_settings(apps, schema_editor):
    ApplicationSetting = apps.get_model("accounts", "ApplicationSetting")
    ApplicationSetting.objects.filter(setting_key__in=ORPHANED_SETTING_KEYS).delete()


def noop_reverse(apps, schema_editor):
    """Irreversible: these rows were dead weight, not worth restoring."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0051_alter_adminactionlog_action_type"),
    ]

    operations = [
        migrations.RunPython(remove_orphaned_settings, noop_reverse),
    ]
