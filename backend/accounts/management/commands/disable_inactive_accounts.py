"""
Inactive account auto-disable — CTRL-0000001019.

Disables active user accounts that have not logged in for more than the
configured inactivity threshold (default: 90 days). Superusers are excluded
to avoid locking out break-glass accounts.

Run periodically (e.g. weekly via cron or Task Scheduler):

    python manage.py disable_inactive_accounts
    python manage.py disable_inactive_accounts --dry-run
    python manage.py disable_inactive_accounts --days 60
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

DEFAULT_INACTIVITY_DAYS = 90


class Command(BaseCommand):
    help = 'Disable active accounts that have not logged in within the inactivity threshold (CTRL-0000001019).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report which accounts would be disabled without making changes.',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=DEFAULT_INACTIVITY_DAYS,
            help=f'Inactivity threshold in days (default: {DEFAULT_INACTIVITY_DAYS}).',
        )

    def handle(self, *args, **options):
        from accounts.models import User, AdminActionLog

        dry_run = options['dry_run']
        days = options['days']
        cutoff = timezone.now() - timedelta(days=days)

        self.stdout.write(
            self.style.WARNING(
                f"{'[DRY RUN] ' if dry_run else ''}Inactivity threshold: {days} days | "
                f"Cutoff: {cutoff.date()}"
            )
        )

        # Accounts that are still active but haven't logged in since the cutoff.
        # Also include accounts that have never logged in and were created before the cutoff.
        # Superusers are excluded to protect break-glass accounts.
        candidates = User.objects.filter(
            is_active=True,
            is_superuser=False,
        ).filter(
            # Either last login is older than cutoff, or never logged in and account is old enough
            last_login_at__lt=cutoff
        ) | User.objects.filter(
            is_active=True,
            is_superuser=False,
            last_login_at__isnull=True,
            date_joined__lt=cutoff,
        )

        # Deduplicate (union can produce duplicates)
        candidates = candidates.distinct()
        count = candidates.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('No inactive accounts found.'))
            return

        self.stdout.write(f"  Accounts to disable: {count}")
        for user in candidates:
            last = user.last_login_at.date() if user.last_login_at else 'never'
            self.stdout.write(f"    - {user.email} (last login: {last})")

        if not dry_run:
            for user in candidates:
                user.is_active = False
                user.status = 'Inactive'
                user.save(update_fields=['is_active', 'status'])
                AdminActionLog.log_action(
                    user=None,
                    action_type='user_deactivated',
                    description=(
                        f'Account auto-disabled due to inactivity (>{days} days without login): '
                        f'{user.email}'
                    ),
                    entity_type='User',
                    entity_id=str(user.id),
                )

            self.stdout.write(self.style.SUCCESS(f"  Disabled {count} inactive accounts."))
            logger.info(f'disable_inactive_accounts: disabled {count} accounts (threshold={days} days)')
        else:
            self.stdout.write(self.style.WARNING(f"  [DRY RUN] Would disable {count} accounts."))
