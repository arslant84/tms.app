"""
Self-installing crontab for the maintenance jobs documented in
backend/scripts/crontab.example — CTRL-0000001019, CTRL-0000001517.

backend/scripts/crontab.example previously required an operator to
manually copy its contents into `crontab -e` on every new deployment; if
that step was skipped, disable_inactive_accounts (90-day inactivity) and
cleanup_expired_data (7-year retention) - both tied to compliance controls
- would silently never run. This command writes the same three jobs
directly into the current user's crontab via python-crontab, tagged with a
comment so re-running it updates the existing entries instead of
duplicating them.

Run once per deployment (or after moving/re-deploying the repo):

    python manage.py install_cron
    python manage.py install_cron --dry-run
    python manage.py install_cron --remove
"""

import sys
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

JOB_TAG_PREFIX = "tms-app maintenance:"

# (comment suffix, schedule, management command, log filename)
JOBS = [
    ("backup_db", "0 2 * * *", "backup_db", "cron_backup_db.log"),
    (
        "disable_inactive_accounts",
        "0 3 * * 0",
        "disable_inactive_accounts",
        "cron_disable_inactive_accounts.log",
    ),
    (
        "cleanup_expired_data",
        "0 4 1 * *",
        "cleanup_expired_data",
        "cron_cleanup_expired_data.log",
    ),
]


class Command(BaseCommand):
    help = (
        "Idempotently install the backup_db / disable_inactive_accounts / "
        "cleanup_expired_data cron schedule into the current user's crontab "
        "(matching backend/scripts/crontab.example)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be installed/removed without writing the crontab.",
        )
        parser.add_argument(
            "--remove",
            action="store_true",
            help="Remove the previously installed jobs instead of installing them.",
        )

    def handle(self, *args, **options):
        try:
            from crontab import CronTab
        except ImportError:
            self.stderr.write(
                self.style.ERROR(
                    "python-crontab is not installed. Add it to requirements.txt "
                    "and `pip install -r requirements.txt`."
                )
            )
            return

        dry_run = options["dry_run"]
        remove = options["remove"]

        base_dir = Path(settings.BASE_DIR)
        python_path = sys.executable
        log_dir = base_dir / "logs"

        cron = CronTab(user=True)

        for job_name, _schedule, _mgmt_command, _log_file in JOBS:
            tag = f"{JOB_TAG_PREFIX} {job_name}"
            cron.remove_all(comment=tag)

        if remove:
            if dry_run:
                self.stdout.write("Would remove all tms-app maintenance cron jobs.")
            else:
                cron.write()
                self.stdout.write(
                    self.style.SUCCESS("Removed all tms-app maintenance cron jobs.")
                )
            return

        for job_name, schedule, mgmt_command, log_file in JOBS:
            tag = f"{JOB_TAG_PREFIX} {job_name}"
            command_line = (
                f"cd {base_dir} && {python_path} manage.py {mgmt_command} "
                f">> {log_dir / log_file} 2>&1"
            )
            job = cron.new(command=command_line, comment=tag)
            job.setall(schedule)

            if dry_run:
                self.stdout.write(f"Would install: {schedule} {command_line}  # {tag}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run - crontab was not modified."))
            return

        cron.write()
        self.stdout.write(
            self.style.SUCCESS(
                f"Installed {len(JOBS)} maintenance cron job(s) into the crontab "
                f"for the current user. Logs will be written under {log_dir}."
            )
        )
