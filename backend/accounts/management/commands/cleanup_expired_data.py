"""
Data disposal management command — CTRL-0000001517.

Deletes or anonymises personal data that has exceeded the configured
retention period. Run periodically (e.g. monthly via cron or Task Scheduler):

    python manage.py cleanup_expired_data
    python manage.py cleanup_expired_data --dry-run
    python manage.py cleanup_expired_data --retention-days 1825

Default retention: 2555 days (7 years), overridable via the
ApplicationSetting key 'data_retention_days' or --retention-days argument.

What is cleaned up:
  - TrfPassportDetail rows linked to completed/cancelled requests older
    than the retention period (passport fields blanked, file deleted).
  - TrfAdvanceBankDetail rows linked to same (account fields blanked).
  - AdminActionLog rows older than the retention period.
  - Deactivated User accounts inactive beyond the retention period (deleted).
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = {'Approved', 'Rejected', 'Cancelled', 'Completed'}
DEFAULT_RETENTION_DAYS = 2555  # 7 years


class Command(BaseCommand):
    help = 'Delete or anonymise personal data older than the retention period (CTRL-0000001517).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would be deleted without making any changes.',
        )
        parser.add_argument(
            '--retention-days',
            type=int,
            default=None,
            help='Override the retention period in days (default: ApplicationSetting data_retention_days or 2555).',
        )

    def handle(self, *args, **options):
        from accounts.models import ApplicationSetting, AdminActionLog
        from trf.models import TrfPassportDetail, TrfAdvanceBankDetail, TravelRequest

        dry_run = options['dry_run']

        retention_days = options['retention_days'] or int(
            ApplicationSetting.get_setting('data_retention_days', DEFAULT_RETENTION_DAYS)
        )
        cutoff = timezone.now() - timedelta(days=retention_days)

        self.stdout.write(
            self.style.WARNING(
                f"{'[DRY RUN] ' if dry_run else ''}Retention period: {retention_days} days | Cutoff: {cutoff.date()}"
            )
        )

        # --- 1. Anonymise passport details for terminal requests past cutoff ---
        old_trfs = TravelRequest.objects.filter(
            status__in=TERMINAL_STATUSES,
            created_at__lt=cutoff,
        )
        passport_qs = TrfPassportDetail.objects.filter(trf__in=old_trfs).exclude(passport_number='').exclude(passport_number__isnull=True)
        passport_count = passport_qs.count()
        self.stdout.write(f"  Passport details to anonymise: {passport_count}")
        if not dry_run and passport_count:
            for detail in passport_qs:
                if detail.passport_file:
                    try:
                        detail.passport_file.delete(save=False)
                    except Exception:
                        pass
                detail.passport_number = ''
                detail.full_name = ''
                detail.place_of_birth = ''
                detail.save(update_fields=['passport_number', 'full_name', 'place_of_birth', 'passport_file'])
            self.stdout.write(self.style.SUCCESS(f"  Anonymised {passport_count} passport detail records."))

        # --- 2. Anonymise bank details for terminal requests past cutoff ---
        bank_qs = TrfAdvanceBankDetail.objects.filter(trf__in=old_trfs).exclude(account_number='').exclude(account_number__isnull=True)
        bank_count = bank_qs.count()
        self.stdout.write(f"  Bank details to anonymise: {bank_count}")
        if not dry_run and bank_count:
            bank_qs.update(account_number='', account_name='', branch_address='')
            self.stdout.write(self.style.SUCCESS(f"  Anonymised {bank_count} bank detail records."))

        # --- 3. Delete old audit logs ---
        old_logs_qs = AdminActionLog.objects.filter(created_at__lt=cutoff)
        log_count = old_logs_qs.count()
        self.stdout.write(f"  Audit logs to delete: {log_count}")
        if not dry_run and log_count:
            old_logs_qs.delete()
            self.stdout.write(self.style.SUCCESS(f"  Deleted {log_count} audit log entries."))

        # --- 4. Delete inactive deactivated accounts past cutoff ---
        from accounts.models import User
        inactive_qs = User.objects.filter(
            is_active=False,
            last_login_at__lt=cutoff,
        )
        inactive_count = inactive_qs.count()
        self.stdout.write(f"  Inactive deactivated accounts to delete: {inactive_count}")
        if not dry_run and inactive_count:
            inactive_qs.delete()
            self.stdout.write(self.style.SUCCESS(f"  Deleted {inactive_count} inactive accounts."))

        summary = (
            f"Cleanup {'(dry run) ' if dry_run else ''}complete — "
            f"passports: {passport_count}, bank details: {bank_count}, "
            f"audit logs: {log_count}, accounts: {inactive_count}"
        )
        self.stdout.write(self.style.SUCCESS(summary))
        logger.info(summary)
