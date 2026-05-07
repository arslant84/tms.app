"""
Backup validation management command — CTRL-0000001382.

Validates a pg_dump backup file by listing its contents with pg_restore --list.
Does NOT touch the live database — safe to run at any time.

Usage:
    python manage.py validate_backup tms_backup_20260507_020000.dump
    python manage.py validate_backup /absolute/path/to/backup.dump
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import subprocess
import os


class Command(BaseCommand):
    help = (
        'Validate a backup file using pg_restore --list. '
        'Pass the filename inside BACKUP_DIR or an absolute path.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_file',
            help='Filename inside BACKUP_DIR (e.g. tms_backup_20260507_020000.dump) or absolute path.',
        )

    def handle(self, *args, **options):
        target = options['backup_file']
        filepath = target if os.path.isabs(target) else str(settings.BACKUP_DIR / target)

        if not os.path.exists(filepath):
            raise CommandError(f'File not found: {filepath}')

        db = settings.DATABASES['default']
        env = {**os.environ, 'PGPASSWORD': db.get('PASSWORD', '')}

        self.stdout.write(f'Validating: {filepath}')

        try:
            result = subprocess.run(
                ['pg_restore', '--list', filepath],
                env=env,
                check=True,
                capture_output=True,
            )
            lines = result.stdout.decode(errors='replace').splitlines()
            object_count = sum(1 for line in lines if line.strip() and not line.startswith(';'))
            self.stdout.write(self.style.SUCCESS(
                f'Backup is valid. Contains {object_count} database objects.'
            ))
            self.stdout.write('Sample entries:')
            for line in lines[:10]:
                self.stdout.write(f'  {line}')
            if len(lines) > 10:
                self.stdout.write(f'  ... and {len(lines) - 10} more.')

        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode(errors='replace') if exc.stderr else str(exc)
            raise CommandError(f'Validation failed: {stderr}')
