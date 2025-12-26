# Generated manually to remove timezone setting

from django.db import migrations


def remove_timezone_setting(apps, schema_editor):
    """Remove timezone setting from ApplicationSettings"""
    ApplicationSetting = apps.get_model('accounts', 'ApplicationSetting')

    # Delete the timezone setting
    ApplicationSetting.objects.filter(setting_key='timezone').delete()


def restore_timezone_setting(apps, schema_editor):
    """Restore timezone setting on migration reversal"""
    ApplicationSetting = apps.get_model('accounts', 'ApplicationSetting')

    ApplicationSetting.objects.get_or_create(
        setting_key='timezone',
        defaults={
            'setting_value': 'UTC',
            'setting_type': 'string',
            'description': 'Default timezone for the application',
            'is_public': True
        }
    )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_remove_email_settings_from_db'),
    ]

    operations = [
        migrations.RunPython(remove_timezone_setting, restore_timezone_setting),
    ]
