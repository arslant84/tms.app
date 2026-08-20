"""
Tests for the install_cron management command (Fix 9 follow-up:
docs/APP_WIDE_GAPS_FIX_ROADMAP.md).

Mocks python-crontab's CronTab entirely - these tests must not touch the
real OS crontab, which would be unsafe to run in CI or on a developer
machine (and doesn't exist in a meaningful form on Windows at all).
"""

from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command


@pytest.fixture
def mock_crontab():
    mock_cron = MagicMock()
    mock_job = MagicMock()
    mock_cron.new.return_value = mock_job

    mock_crontab_class = MagicMock(return_value=mock_cron)

    with patch.dict("sys.modules", {"crontab": MagicMock(CronTab=mock_crontab_class)}):
        yield mock_cron, mock_job


@pytest.mark.django_db
class TestInstallCron:
    def test_install_creates_four_jobs_and_writes(self, mock_crontab):
        mock_cron, mock_job = mock_crontab

        call_command("install_cron")

        assert mock_cron.new.call_count == 4
        assert mock_job.setall.call_count == 4
        mock_cron.write.assert_called_once()

    def test_install_removes_existing_tagged_jobs_first(self, mock_crontab):
        mock_cron, _ = mock_crontab

        call_command("install_cron")

        # 4 current jobs + 1 legacy tag (send_step_reminders, retired - see
        # LEGACY_JOB_NAMES) cleaned up so a server that already has the
        # stale entry actually gets it removed on the next install.
        assert mock_cron.remove_all.call_count == 5
        tags = {
            call.kwargs.get("comment") for call in mock_cron.remove_all.call_args_list
        }
        assert any("backup_db" in tag for tag in tags)
        assert any("disable_inactive_accounts" in tag for tag in tags)
        assert any("cleanup_expired_data" in tag for tag in tags)
        assert any("check_uptime" in tag for tag in tags)
        assert any("send_step_reminders" in tag for tag in tags)

    def test_dry_run_does_not_write(self, mock_crontab):
        mock_cron, _ = mock_crontab

        call_command("install_cron", "--dry-run")

        mock_cron.write.assert_not_called()

    def test_remove_does_not_create_new_jobs(self, mock_crontab):
        mock_cron, _ = mock_crontab

        call_command("install_cron", "--remove")

        mock_cron.new.assert_not_called()
        mock_cron.write.assert_called_once()

    def test_remove_dry_run_does_not_write(self, mock_crontab):
        mock_cron, _ = mock_crontab

        call_command("install_cron", "--remove", "--dry-run")

        mock_cron.write.assert_not_called()

    def test_schedules_match_crontab_example(self, mock_crontab):
        """The installed schedule must match backend/scripts/crontab.example
        exactly, so the two documented sources of truth don't drift apart."""
        mock_cron, mock_job = mock_crontab

        call_command("install_cron")

        installed_schedules = [call.args[0] for call in mock_job.setall.call_args_list]
        assert installed_schedules == [
            "0 2 * * *",
            "0 3 * * 0",
            "0 4 1 * *",
            "*/5 * * * *",
        ]
