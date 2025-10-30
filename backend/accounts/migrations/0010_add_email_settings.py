# Generated manually to add email configuration settings

from django.db import migrations


def add_email_settings(apps, schema_editor):
    """Add email configuration settings"""
    ApplicationSetting = apps.get_model('accounts', 'ApplicationSetting')

    email_settings = [
        {
            'setting_key': 'smtp_host',
            'setting_value': 'smtp-relay.brevo.com',
            'setting_type': 'string',
            'description': 'SMTP server hostname for sending emails',
            'is_public': False
        },
        {
            'setting_key': 'smtp_port',
            'setting_value': '587',
            'setting_type': 'number',
            'description': 'SMTP server port (usually 587 for TLS or 465 for SSL)',
            'is_public': False
        },
        {
            'setting_key': 'smtp_use_tls',
            'setting_value': 'true',
            'setting_type': 'boolean',
            'description': 'Use TLS encryption for SMTP connection',
            'is_public': False
        },
        {
            'setting_key': 'smtp_use_ssl',
            'setting_value': 'false',
            'setting_type': 'boolean',
            'description': 'Use SSL encryption for SMTP connection',
            'is_public': False
        },
        {
            'setting_key': 'smtp_username',
            'setting_value': '8994af002@smtp-brevo.com',
            'setting_type': 'string',
            'description': 'SMTP authentication username',
            'is_public': False
        },
        {
            'setting_key': 'smtp_password',
            'setting_value': 'JfadTIjcZABH0xXY',
            'setting_type': 'string',
            'description': 'SMTP authentication password (stored encrypted in production)',
            'is_public': False
        },
        {
            'setting_key': 'default_from_email',
            'setting_value': 'SynTra TMS <no-reply@pctsb-travel.site>',
            'setting_type': 'string',
            'description': 'Default "From" email address for system emails',
            'is_public': False
        },
        {
            'setting_key': 'server_email',
            'setting_value': 'SynTra TMS <no-reply@pctsb-travel.site>',
            'setting_type': 'string',
            'description': 'Email address for server error notifications',
            'is_public': False
        },
        {
            'setting_key': 'email_admin',
            'setting_value': 'no-reply@pctsb-travel.site',
            'setting_type': 'string',
            'description': 'Admin email address for system notifications',
            'is_public': False
        },
        {
            'setting_key': 'brevo_api_key',
            'setting_value': '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',
            'setting_type': 'string',
            'description': 'Brevo API key for advanced email features (optional)',
            'is_public': False
        }
    ]

    for setting_data in email_settings:
        ApplicationSetting.objects.get_or_create(
            setting_key=setting_data['setting_key'],
            defaults={
                'setting_value': setting_data['setting_value'],
                'setting_type': setting_data['setting_type'],
                'description': setting_data['description'],
                'is_public': setting_data['is_public']
            }
        )


def remove_email_settings(apps, schema_editor):
    """Remove email settings on migration reversal"""
    ApplicationSetting = apps.get_model('accounts', 'ApplicationSetting')

    email_setting_keys = [
        'smtp_host',
        'smtp_port',
        'smtp_use_tls',
        'smtp_use_ssl',
        'smtp_username',
        'smtp_password',
        'default_from_email',
        'server_email',
        'email_admin',
        'brevo_api_key'
    ]

    ApplicationSetting.objects.filter(setting_key__in=email_setting_keys).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_change_profile_photo_to_text'),
    ]

    operations = [
        migrations.RunPython(add_email_settings, remove_email_settings),
    ]
