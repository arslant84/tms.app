from django.core.management.base import BaseCommand
from accounts.models import ApplicationSetting


class Command(BaseCommand):
    help = 'Initialize default application settings'

    def handle(self, *args, **kwargs):
        self.stdout.write('Setting up default application settings...')

        default_settings = [
            # General Settings
            {
                'setting_key': 'app_name',
                'value': 'Travel Management System',
                'setting_type': 'string',
                'description': 'Application name displayed across the system',
                'is_public': True
            },
            {
                'setting_key': 'app_description',
                'value': 'Internal travel and expense management platform',
                'setting_type': 'string',
                'description': 'Short description of the application',
                'is_public': True
            },
            {
                'setting_key': 'support_email',
                'value': 'support@tms.com',
                'setting_type': 'string',
                'description': 'Support contact email',
                'is_public': True
            },
            {
                'setting_key': 'default_currency',
                'value': 'USD',
                'setting_type': 'string',
                'description': 'Default currency for financial calculations',
                'is_public': False
            },
            {
                'setting_key': 'timezone',
                'value': 'UTC',
                'setting_type': 'string',
                'description': 'System timezone',
                'is_public': False
            },
            {
                'setting_key': 'session_timeout',
                'value': 30,
                'setting_type': 'number',
                'description': 'Session timeout in minutes',
                'is_public': False
            },
            {
                'setting_key': 'max_file_upload_size',
                'value': 10,
                'setting_type': 'number',
                'description': 'Maximum file upload size in MB',
                'is_public': False
            },

            # Email Settings
            {
                'setting_key': 'email_enabled',
                'value': True,
                'setting_type': 'boolean',
                'description': 'Enable email notifications system-wide',
                'is_public': False
            },
            {
                'setting_key': 'smtp_host',
                'value': 'smtp.gmail.com',
                'setting_type': 'string',
                'description': 'SMTP server hostname',
                'is_public': False
            },
            {
                'setting_key': 'smtp_port',
                'value': 587,
                'setting_type': 'number',
                'description': 'SMTP server port',
                'is_public': False
            },
            {
                'setting_key': 'smtp_use_tls',
                'value': True,
                'setting_type': 'boolean',
                'description': 'Use TLS for SMTP connection',
                'is_public': False
            },
            {
                'setting_key': 'smtp_username',
                'value': '',
                'setting_type': 'string',
                'description': 'SMTP authentication username',
                'is_public': False
            },
            {
                'setting_key': 'smtp_password',
                'value': '',
                'setting_type': 'string',
                'description': 'SMTP authentication password (encrypted)',
                'is_public': False
            },
            {
                'setting_key': 'default_from_email',
                'value': 'noreply@tms.com',
                'setting_type': 'string',
                'description': 'Default sender email address',
                'is_public': False
            },

            # Notification Settings
            {
                'setting_key': 'notifications_enabled',
                'value': True,
                'setting_type': 'boolean',
                'description': 'Enable in-app notifications',
                'is_public': False
            },
            {
                'setting_key': 'email_notifications_enabled',
                'value': True,
                'setting_type': 'boolean',
                'description': 'Enable email notifications',
                'is_public': False
            },

            # Approval Workflow Settings
            {
                'setting_key': 'auto_approval_threshold',
                'value': 1000,
                'setting_type': 'number',
                'description': 'Auto-approval threshold in USD',
                'is_public': False
            },
            {
                'setting_key': 'require_manager_approval',
                'value': True,
                'setting_type': 'boolean',
                'description': 'Require manager approval for requests',
                'is_public': False
            },
            {
                'setting_key': 'require_finance_approval',
                'value': True,
                'setting_type': 'boolean',
                'description': 'Require finance approval for requests',
                'is_public': False
            },

            # Maintenance Settings
            {
                'setting_key': 'maintenance_mode',
                'value': False,
                'setting_type': 'boolean',
                'description': 'Enable maintenance mode (locks down the system)',
                'is_public': True
            },
            {
                'setting_key': 'maintenance_message',
                'value': 'System is under maintenance. Please check back later.',
                'setting_type': 'string',
                'description': 'Message displayed during maintenance mode',
                'is_public': True
            },
        ]

        created_count = 0
        updated_count = 0

        for setting_data in default_settings:
            setting_key = setting_data.pop('setting_key')
            value = setting_data.pop('value')

            setting, created = ApplicationSetting.objects.get_or_create(
                setting_key=setting_key,
                defaults=setting_data
            )

            if created:
                setting.set_value(value)
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created setting: {setting_key}')
                )
            else:
                # Update description and other metadata, but keep existing value
                for key, val in setting_data.items():
                    setattr(setting, key, val)
                setting.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'- Updated metadata for: {setting_key}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Created {created_count} new settings, '
                f'updated {updated_count} existing settings.'
            )
        )
