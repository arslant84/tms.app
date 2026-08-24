"""
Regression coverage for the DB-backed SMTP settings never actually applying.

core/email_settings_loader.py's ensure_email_settings_loaded() pulls SMTP
host/port/credentials/from-address out of ApplicationSetting into live
Django settings - but nothing in the codebase ever called it, so an admin
configuring custom SMTP settings via the System Settings screen had no
effect: NotificationService.send_email_notification() always used the
static .env/settings.py values instead. Confirmed live in production: a
custom from_email was configured in ApplicationSetting and never took
effect.

Fix: send_email_notification() now calls ensure_email_settings_loaded()
before reading settings.EMAIL_HOST/DEFAULT_FROM_EMAIL/etc.
"""

from unittest.mock import patch

import pytest
from accounts.models import ApplicationSetting
from core.email_settings_loader import _email_settings_loader
from notifications.models import UserNotification
from notifications.services import NotificationService


@pytest.fixture(autouse=True)
def reset_email_settings_loader():
    """The loader caches itself as a process-lifetime singleton
    (EmailSettingsLoader._loaded) so it only hits the DB once per process -
    that's correct for production but means the cached state leaks between
    tests unless reset."""
    _email_settings_loader._loaded = False
    yield
    _email_settings_loader._loaded = False


@pytest.mark.django_db
class TestEmailSettingsLoaderWiring:
    def test_send_email_notification_loads_db_smtp_settings(self, regular_user):
        """A from_email configured in ApplicationSetting must actually reach
        the outgoing email - not silently fall back to the .env default."""
        ApplicationSetting.set_setting(
            "from_email",
            "Custom Sender <custom@example.com>",
            setting_type="string",
        )

        notification = UserNotification.objects.create(
            user=regular_user,
            title="Test",
            message="Test message",
        )

        with patch("notifications.services.send_mail") as mock_send_mail:
            NotificationService.send_email_notification(notification)

        assert mock_send_mail.call_count == 1
        assert (
            mock_send_mail.call_args.kwargs["from_email"]
            == "Custom Sender <custom@example.com>"
        )

    def test_loader_is_called_before_reading_email_settings(self, regular_user):
        """Whether or not any ApplicationSetting rows exist, the loader must
        run on every send - it's what makes a *later* admin config change
        (or a fresh DB) take effect without a process restart."""
        notification = UserNotification.objects.create(
            user=regular_user,
            title="Test",
            message="Test message",
        )

        with patch(
            "core.email_settings_loader.EmailSettingsLoader.load_settings"
        ) as mock_load, patch("notifications.services.send_mail"):
            NotificationService.send_email_notification(notification)

        mock_load.assert_called_once()
