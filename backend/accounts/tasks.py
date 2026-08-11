import csv
import io
import logging

from celery import shared_task
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction

logger = logging.getLogger("accounts")


def _normalize_name(name):
    return " ".join(name.split()).casefold()


@shared_task(bind=True, max_retries=0)
def process_bulk_user_import(self, job_id):
    """
    Background task: process a BulkImportJob created by the admin bulk-import view.

    All heavy work (user creation, password hashing, per-row audit logging) runs
    here in the Celery worker instead of in the gunicorn request thread, eliminating
    the 30-second worker timeout that caused 502 errors on large CSV uploads.
    """
    from .models import AdminActionLog, BulkImportJob, Department, User

    try:
        job = BulkImportJob.objects.get(pk=job_id)
    except BulkImportJob.DoesNotExist:
        logger.error("BulkImportJob %s not found", job_id)
        return

    job.status = BulkImportJob.STATUS_PROCESSING
    job.task_id = self.request.id or ""
    job.save(update_fields=["status", "task_id"])

    try:
        created, skipped, errors, unmatched_departments = _run_import(job)

        job.status = BulkImportJob.STATUS_COMPLETED
        job.created_count = len(created)
        job.skipped_count = len(skipped)
        job.error_count = len(errors)
        job.result_detail = {
            "created": created,
            "skipped": skipped,
            "errors": errors,
            "unmatched_departments": unmatched_departments,
        }
        job.save(update_fields=["status", "created_count", "skipped_count", "error_count", "result_detail"])

        if created:
            AdminActionLog.objects.create(
                user=job.created_by,
                action_type="user_created",
                description=(
                    f"Bulk CSV import: created {len(created)} user(s), "
                    f"skipped {len(skipped)} duplicate(s), "
                    f"{len(errors)} error(s)."
                ),
                entity_type="User",
                ip_address=job.ip_address,
                user_agent=job.user_agent or "",
            )
            try:
                from utils.siem_logger import log_security_event
                log_security_event(
                    action_type="user_created",
                    description=f"Bulk CSV import completed: {len(created)} created, {len(skipped)} skipped, {len(errors)} errors.",
                    user=job.created_by,
                    ip_address=job.ip_address,
                    entity_type="User",
                )
            except Exception:
                pass

        logger.info("BulkImportJob %s completed: %d created, %d skipped, %d errors",
                    job_id, len(created), len(skipped), len(errors))

    except Exception as exc:
        logger.exception("BulkImportJob %s failed: %s", job_id, exc)
        job.status = BulkImportJob.STATUS_FAILED
        job.result_detail = {"errors": [str(exc)]}
        job.save(update_fields=["status", "result_detail"])
        raise


def _run_import(job):
    from .models import Department, User

    reader = csv.DictReader(io.StringIO(job.csv_content))
    if reader.fieldnames:
        reader.fieldnames = [
            (f or "").strip().lower().replace(" ", "_") for f in reader.fieldnames
        ]

    existing_names = set(
        _normalize_name(n) for n in User.objects.values_list("name", flat=True)
    )
    existing_emails = set(User.objects.values_list("email", flat=True))
    existing_staff_ids = set(
        sid for sid in User.objects.values_list("staff_id", flat=True) if sid
    )
    departments_by_name = {
        dept_name.strip().casefold(): dept_id
        for dept_id, dept_name in Department.objects.values_list("id", "name")
    }

    created, skipped, errors, unmatched_departments = [], [], [], []

    for i, row in enumerate(reader, start=2):
        name = (row.get("name") or "").strip()
        email = (row.get("email") or "").strip().lower()
        staff_number = (row.get("staff_number") or "").strip()
        password = (row.get("password") or "").strip()
        department_name = (row.get("department") or "").strip()

        if not name or not email:
            errors.append(f"row {i}: missing name or email")
            continue

        try:
            validate_email(email)
        except ValidationError:
            errors.append(f"row {i}: invalid email '{email}'")
            continue

        normalized_name = _normalize_name(name)
        if normalized_name in existing_names:
            skipped.append(f"row {i}: '{name}' (name already exists)")
            continue
        if email in existing_emails:
            skipped.append(f"row {i}: '{name}' (email already exists)")
            continue
        if staff_number and staff_number in existing_staff_ids:
            skipped.append(f"row {i}: '{name}' (staff number already exists)")
            continue

        department_id = None
        if department_name:
            department_id = departments_by_name.get(department_name.casefold())
            if department_id is None:
                unmatched_departments.append(f"row {i}: '{department_name}'")

        user = User(
            email=email,
            name=name,
            staff_id=staff_number or None,
            department_id=department_id,
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        try:
            with transaction.atomic():
                user.save()
                _log_user_created(job, user, email, name)
        except IntegrityError:
            skipped.append(f"row {i}: '{name}' (already exists in database)")
            continue

        existing_names.add(normalized_name)
        existing_emails.add(email)
        if staff_number:
            existing_staff_ids.add(staff_number)
        created.append(email)

    return created, skipped, errors, unmatched_departments


def _log_user_created(job, user, email, name):
    from .models import AdminActionLog
    AdminActionLog.objects.create(
        user=job.created_by,
        action_type="user_created",
        description=f"User account created via bulk import: {email} ({name})",
        entity_type="User",
        entity_id=str(user.id),
        ip_address=job.ip_address,
        user_agent=job.user_agent or "",
    )
    try:
        from utils.siem_logger import log_security_event
        log_security_event(
            action_type="user_created",
            description=f"User account created via bulk import: {email} ({name})",
            user=job.created_by,
            ip_address=job.ip_address,
            entity_type="User",
            entity_id=str(user.id),
        )
    except Exception:
        pass
