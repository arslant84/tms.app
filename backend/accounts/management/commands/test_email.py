"""
Management command to test email configuration.
Tests SMTP connectivity and sends a test email.

Usage:
    python manage.py test_email recipient@example.com
    python manage.py test_email recipient@example.com --show-config
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.conf import settings
from accounts.models import ApplicationSetting
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test email configuration and send a test email'

    def add_arguments(self, parser):
        parser.add_argument(
            'recipient',
            type=str,
            help='Email address to send test email to'
        )
        parser.add_argument(
            '--show-config',
            action='store_true',
            help='Display current email configuration'
        )
        parser.add_argument(
            '--html',
            action='store_true',
            help='Send HTML test email'
        )

    def handle(self, *args, **options):
        recipient = options['recipient']
        show_config = options['show_config']
        use_html = options['html']

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== EMAIL CONFIGURATION TEST ===\n'))

        # Display current configuration
        if show_config:
            self._display_configuration()

        # Check if email notifications are enabled
        email_enabled = ApplicationSetting.get_setting('enable_email_notifications', True)
        if not email_enabled:
            self.stdout.write(
                self.style.WARNING('⚠️  Email notifications are DISABLED globally in settings')
            )
            return

        # Send test email
        self.stdout.write('\n📧 Sending test email...')
        self.stdout.write(f'   To: {recipient}')
        self.stdout.write(f'   From: {settings.DEFAULT_FROM_EMAIL}')

        try:
            subject = '✅ TMS Email Configuration Test'

            if use_html:
                plain_message = 'Test email from TMS - If you can read this, your email configuration is working!'
                html_message = """
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px; }
                        .content { background-color: #f9f9f9; padding: 20px; border-radius: 5px; margin-top: 20px; }
                        .success { color: #4CAF50; font-weight: bold; }
                        .footer { margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>✅ Email Test Successful</h1>
                        </div>
                        <div class="content">
                            <p class="success">Congratulations!</p>
                            <p>Your TMS email configuration is working correctly.</p>
                            <p><strong>SMTP Configuration:</strong></p>
                            <ul>
                                <li>Host: {host}</li>
                                <li>Port: {port}</li>
                                <li>TLS: {tls}</li>
                                <li>From: {from_email}</li>
                            </ul>
                            <p>You can now receive workflow notifications, approval requests, and system alerts.</p>
                        </div>
                        <div class="footer">
                            <p>This is an automated test email from TMS (Travel Management System)</p>
                        </div>
                    </div>
                </body>
                </html>
                """.format(
                    host=settings.EMAIL_HOST,
                    port=settings.EMAIL_PORT,
                    tls='Enabled' if settings.EMAIL_USE_TLS else 'Disabled',
                    from_email=settings.DEFAULT_FROM_EMAIL
                )

                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient],
                    fail_silently=False,
                    html_message=html_message
                )
            else:
                message = """
Test Email from TMS (Travel Management System)

✅ SUCCESS! Your email configuration is working correctly.

SMTP Configuration:
- Host: {host}
- Port: {port}
- TLS: {tls}
- From: {from_email}

You can now receive:
- Workflow notifications
- Approval requests
- System alerts
- Status updates

If you received this email, your SMTP settings are properly configured.
                """.format(
                    host=settings.EMAIL_HOST,
                    port=settings.EMAIL_PORT,
                    tls='Enabled' if settings.EMAIL_USE_TLS else 'Disabled',
                    from_email=settings.DEFAULT_FROM_EMAIL
                )

                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient],
                    fail_silently=False
                )

            self.stdout.write(self.style.SUCCESS('\n✅ Test email sent successfully!\n'))
            self.stdout.write('   Check the recipient inbox (and spam folder)')
            self.stdout.write('\n' + '='*50 + '\n')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Failed to send test email!\n'))
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}\n'))

            # Provide troubleshooting hints
            self.stdout.write(self.style.WARNING('Troubleshooting Tips:'))
            self.stdout.write('  1. Verify SMTP host and port are correct')
            self.stdout.write('  2. Check username and password are valid')
            self.stdout.write('  3. Ensure firewall allows outbound SMTP connections')
            self.stdout.write('  4. Some providers (Gmail) require app-specific passwords')
            self.stdout.write('  5. Check if TLS/SSL settings match your SMTP server requirements')
            self.stdout.write('\n' + '='*50 + '\n')

            raise CommandError(f'Email sending failed: {str(e)}')

    def _display_configuration(self):
        """Display current email configuration from database and Django settings"""

        self.stdout.write(self.style.MIGRATE_LABEL('\n📋 Database SMTP Settings:'))
        self.stdout.write('-' * 50)

        db_settings = {
            'smtp_host': 'SMTP Host',
            'smtp_port': 'SMTP Port',
            'smtp_use_tls': 'Use TLS',
            'smtp_use_ssl': 'Use SSL',
            'smtp_username': 'Username',
            'default_from_email': 'From Email',
            'enable_email_notifications': 'Notifications Enabled'
        }

        for key, label in db_settings.items():
            value = ApplicationSetting.get_setting(key)
            if value is not None:
                # Hide password
                if 'password' in key:
                    display_value = '***HIDDEN***'
                else:
                    display_value = value
                self.stdout.write(f'   {label:.<30} {display_value}')

        self.stdout.write(self.style.MIGRATE_LABEL('\n⚙️  Django Active EMAIL Settings:'))
        self.stdout.write('-' * 50)
        self.stdout.write(f'   EMAIL_BACKEND:................ {settings.EMAIL_BACKEND}')
        self.stdout.write(f'   EMAIL_HOST:................... {settings.EMAIL_HOST}')
        self.stdout.write(f'   EMAIL_PORT:................... {settings.EMAIL_PORT}')
        self.stdout.write(f'   EMAIL_USE_TLS:................ {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'   EMAIL_USE_SSL:................ {settings.EMAIL_USE_SSL}')
        self.stdout.write(f'   EMAIL_HOST_USER:.............. {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'   DEFAULT_FROM_EMAIL:........... {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'   EMAIL_TIMEOUT:................ {settings.EMAIL_TIMEOUT} seconds')
        self.stdout.write('')
