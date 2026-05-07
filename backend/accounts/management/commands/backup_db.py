"""
Database backup management command — CTRL-0000001040.

Creates a pg_dump backup in PostgreSQL custom format (.dump).
Intended to be run on a schedule (e.g. daily via cron or Task Scheduler):

    python manage.py backup_db
    python manage.py backup_db --dry-run

Cron example (daily at 02:00):
    0 2 * * * /path/to/venv/bin/python /path/to/backend/manage.py backup_db

Each successful backup is recorded in the DatabaseBackup table.
Validate a backup with: python manage.py validate_backup <filename>
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
import subprocess
import os


class Command(BaseCommand):
    help = 'Create a pg_dump backup of the database (CTRL-0000001040). Intended for scheduled execution.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be backed up without creating the file.',
        )

    def handle(self, *args, **options):
        from accounts.models import DatabaseBackup

        backup_dir = settings.BACKUP_DIR
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f'tms_backup_{timestamp}.dump'
        filepath = backup_dir / filename

        db = settings.DATABASES['default']

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f'[DRY RUN] Would create: {filepath}')
            )
            return

        record = DatabaseBackup.objects.create(
            created_by=None,
            filename=filename,
            status=DatabaseBackup.STATUS_CREATING,
            notes='Scheduled automatic backup.',
        )

        env = {**os.environ, 'PGPASSWORD': db.get('PASSWORD', '')}

        try:
            subprocess.run(
                [
                    'pg_dump',
                    '-h', db.get('HOST', 'localhost'),
                    '-p', str(db.get('PORT', 5432)),
                    '-U', db.get('USER', 'postgres'),
                    '-Fc',
                    '-f', str(filepath),
                    db.get('NAME', ''),
                ],
                env=env,
                check=True,
                capture_output=True,
            )
            size = filepath.stat().st_size
            record.file_size = size
            record.status = DatabaseBackup.STATUS_COMPLETED
            record.save(update_fields=['file_size', 'status'])
            self.stdout.write(
                self.style.SUCCESS(f'Backup created: {filename} ({size:,} bytes)')
            )

        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode(errors='replace') if exc.stderr else str(exc)
            record.status = DatabaseBackup.STATUS_FAILED
            record.notes = stderr
            record.save(update_fields=['status', 'notes'])
            self.stderr.write(self.style.ERROR(f'Backup failed: {stderr}'))
