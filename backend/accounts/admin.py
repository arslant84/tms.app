import os
import subprocess

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.db import transaction
from django.http import FileResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    AdminActionLog,
    ApplicationSetting,
    BulkImportJob,
    DatabaseBackup,
    Department,
    Permission,
    Role,
    RolePermission,
    User,
)


class CustomUserCreationForm(UserCreationForm):
    """Custom form for creating users with email as username"""

    class Meta:
        model = User
        fields = (
            "email",
            "name",
            "role",
            "department",
            "staff_id",
            "phone",
            "gender",
            "is_admin",
            "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make password fields optional for admin creation
        self.fields["password1"].required = False
        self.fields["password2"].required = False

    def save(self, commit=True):
        user = super().save(commit=False)
        # Set a default password if none provided
        password = self.cleaned_data.get("password1")
        if password:
            user.set_password(password)
        else:
            # Set unusable password - user must reset via email
            user.set_unusable_password()

        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """Custom form for changing user data"""

    class Meta:
        model = User
        fields = (
            "email",
            "name",
            "role",
            "department",
            "staff_id",
            "phone",
            "gender",
            "is_admin",
            "is_active",
            "status",
            "profile_photo",
        )


class BulkUserImportForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV file",
        help_text=(
            "Header row required: staff_number,name,email,password,department. "
            "The password column may be left blank per-row — those users "
            "get an unusable password and must reset it via the login "
            "screen's forgot-password flow. The department column may also "
            "be left blank and must match an existing department's name."
        ),
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model"""

    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = (
        "email",
        "name",
        "role",
        "department",
        "staff_id",
        "is_admin",
        "is_active",
        "status",
        "mfa_status",
        "mfa_reset_button",
    )
    list_filter = (
        "is_admin",
        "is_active",
        "role",
        "department",
        "status",
        "mfa_enabled",
    )
    actions = ["reset_mfa_action"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal Info",
            {"fields": ("name", "staff_id", "phone", "gender", "profile_photo")},
        ),
        ("Organization", {"fields": ("role", "department")}),
        (
            "Permissions",
            {"fields": ("is_admin", "is_active", "is_staff", "is_superuser", "status")},
        ),
        (
            "Privacy Consent",
            {
                "fields": (
                    "privacy_consent",
                    "privacy_consent_date",
                    "privacy_policy_version",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "last_login_at", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "name",
                    "password1",
                    "password2",
                    "role",
                    "department",
                    "staff_id",
                    "phone",
                    "gender",
                    "is_admin",
                    "is_active",
                ),
            },
        ),
    )

    search_fields = ("email", "name", "staff_id", "department__name")
    ordering = ("email",)
    filter_horizontal = ()

    @admin.display(description="MFA", boolean=True, ordering="mfa_enabled")
    def mfa_status(self, obj):
        return obj.mfa_enabled

    @admin.display(description="")
    def mfa_reset_button(self, obj):
        if not obj.mfa_enabled:
            return "—"
        url = reverse("admin:accounts_user_reset_mfa", args=[obj.pk])
        return format_html(
            '<a class="button" style="background:#ffc107;color:#000" href="{}">Reset MFA</a>',
            url,
        )

    def _reset_mfa_for_user(self, request, user):
        user.mfa_enabled = False
        user.mfa_secret = None
        user.save(update_fields=["mfa_enabled", "mfa_secret"])
        AdminActionLog.log_action(
            user=request.user,
            action_type="mfa_admin_reset",
            description=f"MFA reset by admin ({request.user.email}) for user: {user.email}",
            entity_type="User",
            entity_id=str(user.id),
            request=request,
        )

    @admin.action(description="Reset MFA for selected users")
    def reset_mfa_action(self, request, queryset):
        reset_count = 0
        for user in queryset.filter(mfa_enabled=True):
            self._reset_mfa_for_user(request, user)
            reset_count += 1

        if reset_count:
            self.message_user(
                request,
                f"MFA reset for {reset_count} user(s). They will need to set it up again.",
                messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                "No selected users had MFA enabled.",
                messages.WARNING,
            )

    def reset_mfa_view(self, request, user_id):
        user = self.get_object(request, user_id)
        if user is None:
            self.message_user(request, "User not found.", messages.ERROR)
            return HttpResponseRedirect(reverse("admin:accounts_user_changelist"))

        if not self.has_change_permission(request, user):
            self.message_user(
                request, "You don't have permission to do that.", messages.ERROR
            )
            return HttpResponseRedirect(reverse("admin:accounts_user_changelist"))

        if not user.mfa_enabled:
            self.message_user(
                request, f"{user.email} does not have MFA enabled.", messages.WARNING
            )
            return HttpResponseRedirect(reverse("admin:accounts_user_changelist"))

        if request.method == "POST":
            self._reset_mfa_for_user(request, user)
            self.message_user(
                request,
                f"MFA has been reset for {user.email}. They will need to set it up again.",
                messages.SUCCESS,
            )
            return HttpResponseRedirect(reverse("admin:accounts_user_changelist"))

        context = {
            **self.admin_site.each_context(request),
            "title": "Reset MFA",
            "target_user": user,
            "opts": self.model._meta,
        }
        return render(request, "admin/accounts/reset_mfa_confirmation.html", context)

    def save_model(self, request, obj, form, change):
        obj._update_request = request
        super().save_model(request, obj, form, change)
        if not change:
            AdminActionLog.log_action(
                user=request.user,
                action_type="user_created",
                description=f"User account created: {obj.email} ({obj.name})",
                entity_type="User",
                entity_id=str(obj.id),
                request=request,
            )

    def delete_model(self, request, obj):
        AdminActionLog.log_action(
            user=request.user,
            action_type="user_deleted",
            description=f"User account deleted: {obj.email} ({obj.name})",
            entity_type="User",
            entity_id=str(obj.id),
            request=request,
        )
        obj._deletion_logged = True
        super().delete_model(request, obj)

    # ── Bulk CSV import ────────────────────────────────────────────────────

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "bulk-import/",
                self.admin_site.admin_view(self.bulk_import_users_view),
                name="accounts_bulk_import_users",
            ),
            path(
                "bulk-import/job/<uuid:job_id>/",
                self.admin_site.admin_view(self.bulk_import_job_status_view),
                name="accounts_bulk_import_job_status",
            ),
            path(
                "<int:user_id>/reset-mfa/",
                self.admin_site.admin_view(self.reset_mfa_view),
                name="accounts_user_reset_mfa",
            ),
        ]
        return custom + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["bulk_import_url"] = reverse("admin:accounts_bulk_import_users")
        return super().changelist_view(request, extra_context=extra_context)

    def bulk_import_users_view(self, request):
        if request.method == "POST":
            form = BulkUserImportForm(request.POST, request.FILES)
            if form.is_valid():
                uploaded_file = request.FILES["csv_file"]
                try:
                    csv_content = uploaded_file.read().decode("utf-8-sig")
                except UnicodeDecodeError:
                    messages.error(request, "File is not valid UTF-8 text.")
                    context = {
                        **self.admin_site.each_context(request),
                        "title": "Bulk Import Users (CSV)",
                        "form": form,
                        "opts": self.model._meta,
                    }
                    return render(
                        request, "admin/accounts/bulk_import_users.html", context
                    )

                x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
                ip_address = (
                    x_forwarded_for.split(",")[0].strip()
                    if x_forwarded_for
                    else request.META.get("REMOTE_ADDR")
                )

                job = BulkImportJob.objects.create(
                    created_by=request.user,
                    csv_content=csv_content,
                    ip_address=ip_address,
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                )

                from .tasks import process_bulk_user_import

                process_bulk_user_import.delay(str(job.id))

                messages.info(
                    request,
                    "Your CSV is being processed in the background. "
                    "This page will refresh automatically until the import is complete.",
                )
                return HttpResponseRedirect(
                    reverse("admin:accounts_bulk_import_job_status", args=[job.id])
                )
        else:
            form = BulkUserImportForm()

        context = {
            **self.admin_site.each_context(request),
            "title": "Bulk Import Users (CSV)",
            "form": form,
            "opts": self.model._meta,
        }
        return render(request, "admin/accounts/bulk_import_users.html", context)

    def bulk_import_job_status_view(self, request, job_id):
        job = BulkImportJob.objects.get(pk=job_id)
        context = {
            **self.admin_site.each_context(request),
            "title": "Bulk Import — Job Status",
            "job": job,
            "opts": self.model._meta,
        }
        return render(request, "admin/accounts/bulk_import_job_status.html", context)


class RolePermissionInline(admin.TabularInline):
    """Inline for managing role permissions"""

    model = RolePermission
    extra = 1
    verbose_name = "Permission"
    verbose_name_plural = "Permissions"


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin interface for Role model"""

    list_display = ("name", "description", "permission_count", "created_at")
    search_fields = ("name", "description")
    ordering = ("name",)
    inlines = [RolePermissionInline]

    def permission_count(self, obj):
        return obj.permissions.count()

    permission_count.short_description = "Permissions"


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Admin interface for Permission model"""

    list_display = ("name", "description", "role_count", "created_at")
    search_fields = ("name", "description")
    ordering = ("name",)

    def role_count(self, obj):
        return obj.role_set.count()

    role_count.short_description = "Roles Using"


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    """Admin interface for RolePermission model"""

    list_display = ("role", "permission", "created_at")
    list_filter = ("role", "permission")
    search_fields = ("role__name", "permission__name")
    ordering = ("role", "permission")


@admin.register(ApplicationSetting)
class ApplicationSettingAdmin(admin.ModelAdmin):
    """Admin interface for Application Settings"""

    list_display = (
        "setting_key",
        "setting_value",
        "setting_type",
        "is_public",
        "updated_at",
    )
    list_filter = ("setting_type", "is_public")
    search_fields = ("setting_key", "setting_value", "description")
    ordering = ("setting_key",)

    fieldsets = (
        (None, {"fields": ("setting_key", "setting_value", "setting_type")}),
        ("Details", {"fields": ("description", "is_public")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ("created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        """Make setting_key readonly on edit"""
        if obj:  # Editing an existing object
            return self.readonly_fields + ("setting_key",)
        return self.readonly_fields


@admin.register(AdminActionLog)
class AdminActionLogAdmin(admin.ModelAdmin):
    """Admin interface for Audit Logs (Security Audit Trail)"""

    list_display = (
        "created_at",
        "user_email",
        "action_type",
        "entity_type",
        "entity_id",
        "ip_address",
    )
    list_filter = ("action_type", "created_at", "user")
    search_fields = (
        "user__email",
        "entity_type",
        "entity_id",
        "description",
        "ip_address",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Action Details",
            {
                "fields": (
                    "user",
                    "action_type",
                    "entity_type",
                    "entity_id",
                    "description",
                )
            },
        ),
        ("Request Details", {"fields": ("ip_address", "user_agent")}),
        ("Timestamp", {"fields": ("created_at",)}),
    )

    readonly_fields = (
        "user",
        "action_type",
        "entity_type",
        "entity_id",
        "description",
        "ip_address",
        "user_agent",
        "created_at",
    )

    def user_email(self, obj):
        return obj.user.email if obj.user else "System/Unknown"

    user_email.short_description = "User"
    user_email.admin_order_field = "user__email"

    def has_add_permission(self, request):
        # Prevent manual creation of audit logs
        return False

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of audit logs for security
        return False

    # ── Staging Data Reset ────────────────────────────────────────────────
    # Lets a superuser wipe every submitted request and notification so
    # testers can start a staging environment from a clean slate. Gated on
    # settings.ALLOW_DATA_RESET (env: ALLOW_DATA_RESET) - refuses to run
    # entirely unless that's explicitly set, so this can never fire against
    # an environment (production included) that didn't opt in.

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "reset-staging-data/",
                self.admin_site.admin_view(self.reset_staging_data_view),
                name="accounts_reset_staging_data",
            ),
        ]
        return custom + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["reset_staging_data_url"] = reverse(
            "admin:accounts_reset_staging_data"
        )
        return super().changelist_view(request, extra_context=extra_context)

    @staticmethod
    def _staging_reset_counts():
        """Current row counts for everything reset_staging_data_view deletes."""
        from accommodation.models import AccommodationRequest
        from notifications.models import NotificationBatch, UserNotification
        from transport.models import TransportRequest
        from trf.models import TravelRequest
        from visa.models import VisaApplication
        from workflows.models import WorkflowInstance

        return {
            "Travel requests (TSR)": TravelRequest.objects.count(),
            "Transport requests": TransportRequest.objects.count(),
            "Visa applications": VisaApplication.objects.count(),
            "Accommodation requests": AccommodationRequest.objects.count(),
            "Workflow instances": WorkflowInstance.objects.count(),
            "Notifications": UserNotification.objects.count(),
            "Notification batches": NotificationBatch.objects.count(),
        }

    @staticmethod
    @transaction.atomic
    def _run_staging_reset():
        """
        Delete every submitted request and notification.

        Deleting each request queryset (rather than truncating tables)
        deliberately goes through the ORM so workflows/signals.py's
        pre_delete handler fires per row and cleans up the matching
        WorkflowInstance (and its CASCADE-linked step executions/
        delegations/audit logs) and any UserNotification whose action_url
        points at that request - the same cleanup a normal single-request
        delete gets, just for everything at once. The explicit
        WorkflowInstance/UserNotification/NotificationBatch deletes at the
        end are belt-and-suspenders for anything that cleanup doesn't catch
        (e.g. notifications with no action_url match) rather than the
        primary mechanism.
        """
        from accommodation.models import AccommodationRequest
        from notifications.models import NotificationBatch, UserNotification
        from transport.models import TransportRequest
        from trf.models import TravelRequest
        from visa.models import VisaApplication
        from workflows.models import WorkflowInstance

        counts = AdminActionLogAdmin._staging_reset_counts()

        TravelRequest.objects.all().delete()
        TransportRequest.objects.all().delete()
        VisaApplication.objects.all().delete()
        AccommodationRequest.objects.all().delete()
        WorkflowInstance.objects.all().delete()
        UserNotification.objects.all().delete()
        NotificationBatch.objects.all().delete()

        return counts

    def reset_staging_data_view(self, request):
        if not request.user.is_superuser:
            messages.error(request, "Only superusers can reset staging data.")
            return HttpResponseRedirect(
                reverse("admin:accounts_adminactionlog_changelist")
            )

        if not settings.ALLOW_DATA_RESET:
            messages.error(
                request,
                "Staging data reset is disabled. Set ALLOW_DATA_RESET=true in "
                "this environment's .env to enable it - never on production.",
            )
            return HttpResponseRedirect(
                reverse("admin:accounts_adminactionlog_changelist")
            )

        if request.method == "POST":
            form = StagingResetForm(request.POST)
            if form.is_valid():
                counts = self._run_staging_reset()
                summary = "; ".join(f"{label}: {n}" for label, n in counts.items())

                AdminActionLog.log_action(
                    user=request.user,
                    action_type="staging_data_reset",
                    description=f"Staging data reset - deleted {summary}",
                    entity_type="StagingReset",
                    request=request,
                )

                messages.success(
                    request, f"Staging data reset complete. Deleted: {summary}."
                )
                return HttpResponseRedirect(
                    reverse("admin:accounts_adminactionlog_changelist")
                )
        else:
            form = StagingResetForm()

        context = {
            **self.admin_site.each_context(request),
            "title": "Reset Staging Data",
            "form": form,
            "counts": self._staging_reset_counts(),
            "opts": AdminActionLog._meta,
        }
        return render(
            request, "admin/accounts/reset_staging_data_confirmation.html", context
        )


# ──────────────────────────────────────────────────────────────────────────────
# Database Backup & Restore (CTRL-0000001040, 1382)
# ──────────────────────────────────────────────────────────────────────────────


class StagingResetForm(forms.Form):
    confirm_text = forms.CharField(
        label='Type "RESET" to confirm',
        help_text="Case-sensitive. This cannot be undone.",
    )

    def clean_confirm_text(self):
        value = self.cleaned_data["confirm_text"]
        if value != "RESET":
            raise forms.ValidationError('You must type "RESET" exactly to proceed.')
        return value


class RestoreForm(forms.Form):
    backup_file = forms.FileField(
        label="Backup file (.dump)",
        help_text="Upload a pg_dump backup file previously created by this system.",
    )
    confirm = forms.BooleanField(
        label="I understand this will permanently overwrite all current data",
        required=True,
    )


@admin.register(DatabaseBackup)
class DatabaseBackupAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "created_by",
        "status_badge",
        "size_display",
        "created_at",
        "download_btn",
    )
    readonly_fields = (
        "created_at",
        "created_by",
        "filename",
        "file_size",
        "status",
        "notes",
    )
    list_filter = ("status",)

    def has_add_permission(self, request):
        return False  # created via the "Create Backup" button only

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "create/",
                self.admin_site.admin_view(self.create_backup_view),
                name="accounts_create_backup",
            ),
            path(
                "<int:pk>/download/",
                self.admin_site.admin_view(self.download_backup_view),
                name="accounts_download_backup",
            ),
            path(
                "restore/",
                self.admin_site.admin_view(self.restore_backup_view),
                name="accounts_restore_backup",
            ),
        ]
        return custom + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["create_backup_url"] = reverse("admin:accounts_create_backup")
        extra_context["restore_backup_url"] = reverse("admin:accounts_restore_backup")
        return super().changelist_view(request, extra_context=extra_context)

    # ── column helpers ──────────────────────────────────────────────────────

    def status_badge(self, obj):
        colours = {
            DatabaseBackup.STATUS_COMPLETED: "green",
            DatabaseBackup.STATUS_FAILED: "red",
            DatabaseBackup.STATUS_CREATING: "orange",
        }
        colour = colours.get(obj.status, "grey")
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            colour,
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"

    def size_display(self, obj):
        if obj.file_size is None:
            return "—"
        for unit in ("B", "KB", "MB", "GB"):
            if obj.file_size < 1024:
                return f"{obj.file_size:.1f} {unit}"
            obj.file_size /= 1024
        return f"{obj.file_size:.1f} TB"

    size_display.short_description = "Size"

    def download_btn(self, obj):
        if obj.status != DatabaseBackup.STATUS_COMPLETED:
            return "—"
        url = reverse("admin:accounts_download_backup", args=[obj.pk])
        return format_html('<a class="button" href="{}">⬇ Download</a>', url)

    download_btn.short_description = "Download"

    # ── views ───────────────────────────────────────────────────────────────

    def create_backup_view(self, request):
        backup_dir = settings.BACKUP_DIR
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tms_backup_{timestamp}.dump"
        filepath = backup_dir / filename

        record = DatabaseBackup.objects.create(
            created_by=request.user,
            filename=filename,
            status=DatabaseBackup.STATUS_CREATING,
            notes="Manual backup via admin panel.",
        )

        db = settings.DATABASES["default"]
        env = {**os.environ, "PGPASSWORD": db.get("PASSWORD", "")}

        try:
            subprocess.run(
                [
                    settings.PG_DUMP_BIN,
                    "-h",
                    db.get("HOST", "localhost"),
                    "-p",
                    str(db.get("PORT", 5432)),
                    "-U",
                    db.get("USER", "postgres"),
                    "-Fc",
                    "-f",
                    str(filepath),
                    db.get("NAME", ""),
                ],
                env=env,
                check=True,
                capture_output=True,
            )
            record.file_size = filepath.stat().st_size
            record.status = DatabaseBackup.STATUS_COMPLETED
            record.save(update_fields=["file_size", "status"])
            messages.success(
                request, f'Backup "{filename}" created ({record.file_size:,} bytes).'
            )
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode(errors="replace") if exc.stderr else str(exc)
            record.status = DatabaseBackup.STATUS_FAILED
            record.notes = stderr
            record.save(update_fields=["status", "notes"])
            messages.error(request, f"Backup failed: {stderr}")
        except Exception as exc:
            record.status = DatabaseBackup.STATUS_FAILED
            record.notes = str(exc)
            record.save(update_fields=["status", "notes"])
            messages.error(request, f"Backup failed: {exc}")

        return HttpResponseRedirect(reverse("admin:accounts_databasebackup_changelist"))

    def download_backup_view(self, request, pk):
        backup = DatabaseBackup.objects.get(pk=pk)
        filepath = settings.BACKUP_DIR / backup.filename
        if not filepath.exists():
            messages.error(request, "Backup file not found on disk.")
            return HttpResponseRedirect(
                reverse("admin:accounts_databasebackup_changelist")
            )
        response = FileResponse(
            open(filepath, "rb"), content_type="application/octet-stream"
        )
        response["Content-Disposition"] = f'attachment; filename="{backup.filename}"'
        return response

    def restore_backup_view(self, request):
        if not request.user.is_superuser:
            messages.error(request, "Only superusers can perform a restore.")
            return HttpResponseRedirect(
                reverse("admin:accounts_databasebackup_changelist")
            )

        if request.method == "POST":
            form = RestoreForm(request.POST, request.FILES)
            if form.is_valid():
                uploaded = request.FILES["backup_file"]
                timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
                restore_path = (
                    settings.BACKUP_DIR / f"restore_{timestamp}_{uploaded.name}"
                )
                with open(restore_path, "wb") as f:
                    for chunk in uploaded.chunks():
                        f.write(chunk)

                db = settings.DATABASES["default"]
                env = {**os.environ, "PGPASSWORD": db.get("PASSWORD", "")}

                # Auto-snapshot current state before overwriting
                pre_filename = f"pre_restore_auto_{timestamp}.dump"
                pre_path = settings.BACKUP_DIR / pre_filename
                try:
                    subprocess.run(
                        [
                            settings.PG_DUMP_BIN,
                            "-h",
                            db.get("HOST", "localhost"),
                            "-p",
                            str(db.get("PORT", 5432)),
                            "-U",
                            db.get("USER", "postgres"),
                            "-Fc",
                            "-f",
                            str(pre_path),
                            db.get("NAME", ""),
                        ],
                        env=env,
                        check=True,
                        capture_output=True,
                    )
                    DatabaseBackup.objects.create(
                        created_by=request.user,
                        filename=pre_filename,
                        file_size=pre_path.stat().st_size,
                        status=DatabaseBackup.STATUS_COMPLETED,
                        notes="Auto-snapshot created before restore operation.",
                    )
                except Exception as exc:
                    messages.warning(
                        request,
                        f"Pre-restore snapshot failed ({exc}). Proceeding anyway.",
                    )

                try:
                    subprocess.run(
                        [
                            settings.PG_RESTORE_BIN,
                            "-h",
                            db.get("HOST", "localhost"),
                            "-p",
                            str(db.get("PORT", 5432)),
                            "-U",
                            db.get("USER", "postgres"),
                            "-d",
                            db.get("NAME", ""),
                            "--clean",
                            "--if-exists",
                            str(restore_path),
                        ],
                        env=env,
                        check=True,
                        capture_output=True,
                    )
                    messages.success(
                        request,
                        "Database restored successfully. "
                        "Your session has been cleared — please log in again.",
                    )
                    return HttpResponseRedirect("/admin/login/")
                except subprocess.CalledProcessError as exc:
                    stderr = (
                        exc.stderr.decode(errors="replace") if exc.stderr else str(exc)
                    )
                    messages.error(
                        request,
                        f"Restore failed: {stderr}. "
                        f'A pre-restore snapshot was saved as "{pre_filename}".',
                    )
        else:
            form = RestoreForm()

        context = {
            **self.admin_site.each_context(request),
            "title": "Restore Database from Backup",
            "form": form,
            "opts": DatabaseBackup._meta,
        }
        return render(request, "admin/accounts/restore_backup.html", context)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_active", "created_at"]
    search_fields = ["name", "code", "description"]
    list_filter = ["is_active"]
    ordering = ["name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(BulkImportJob)
class BulkImportJobAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "status",
        "created_by",
        "created_count",
        "skipped_count",
        "error_count",
        "created_at",
    ]
    search_fields = ["id", "task_id", "created_by__email"]
    list_filter = ["status", "created_at"]
    ordering = ["-created_at"]
    readonly_fields = [
        "id",
        "created_by",
        "created_at",
        "csv_content",
        "ip_address",
        "user_agent",
        "created_count",
        "skipped_count",
        "error_count",
        "result_detail",
        "task_id",
        "status",
    ]

    def has_add_permission(self, request):
        return False
