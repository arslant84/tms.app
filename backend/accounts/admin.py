from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from django.conf import settings
from django.http import FileResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.contrib import messages
import subprocess
import os
from .models import User, Role, Permission, RolePermission, ApplicationSetting, AdminActionLog, DatabaseBackup


class CustomUserCreationForm(UserCreationForm):
    """Custom form for creating users with email as username"""

    class Meta:
        model = User
        fields = ('email', 'name', 'role', 'department', 'staff_id', 'phone', 'gender', 'is_admin', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make password fields optional for admin creation
        self.fields['password1'].required = False
        self.fields['password2'].required = False

    def save(self, commit=True):
        user = super().save(commit=False)
        # Set a default password if none provided
        password = self.cleaned_data.get('password1')
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
        fields = ('email', 'name', 'role', 'department', 'staff_id', 'phone', 'gender',
                  'is_admin', 'is_active', 'status', 'profile_photo')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model"""

    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ('email', 'name', 'role', 'department', 'staff_id', 'is_admin', 'is_active', 'status')
    list_filter = ('is_admin', 'is_active', 'role', 'department', 'status')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('name', 'staff_id', 'phone', 'gender', 'profile_photo')}),
        ('Organization', {'fields': ('role', 'department')}),
        ('Permissions', {'fields': ('is_admin', 'is_active', 'is_staff', 'is_superuser', 'status')}),
        ('Important dates', {'fields': ('last_login', 'last_login_at', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2', 'role', 'department',
                       'staff_id', 'phone', 'gender', 'is_admin', 'is_active'),
        }),
    )

    search_fields = ('email', 'name', 'staff_id', 'department')
    ordering = ('email',)
    filter_horizontal = ()


class RolePermissionInline(admin.TabularInline):
    """Inline for managing role permissions"""
    model = RolePermission
    extra = 1
    verbose_name = 'Permission'
    verbose_name_plural = 'Permissions'


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin interface for Role model"""

    list_display = ('name', 'description', 'permission_count', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)
    inlines = [RolePermissionInline]

    def permission_count(self, obj):
        return obj.permissions.count()
    permission_count.short_description = 'Permissions'


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Admin interface for Permission model"""

    list_display = ('name', 'description', 'role_count', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)

    def role_count(self, obj):
        return obj.role_set.count()
    role_count.short_description = 'Roles Using'


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    """Admin interface for RolePermission model"""

    list_display = ('role', 'permission', 'created_at')
    list_filter = ('role', 'permission')
    search_fields = ('role__name', 'permission__name')
    ordering = ('role', 'permission')


@admin.register(ApplicationSetting)
class ApplicationSettingAdmin(admin.ModelAdmin):
    """Admin interface for Application Settings"""

    list_display = ('setting_key', 'setting_value', 'setting_type', 'is_public', 'updated_at')
    list_filter = ('setting_type', 'is_public')
    search_fields = ('setting_key', 'setting_value', 'description')
    ordering = ('setting_key',)

    fieldsets = (
        (None, {
            'fields': ('setting_key', 'setting_value', 'setting_type')
        }),
        ('Details', {
            'fields': ('description', 'is_public')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    def get_readonly_fields(self, request, obj=None):
        """Make setting_key readonly on edit"""
        if obj:  # Editing an existing object
            return self.readonly_fields + ('setting_key',)
        return self.readonly_fields


@admin.register(AdminActionLog)
class AdminActionLogAdmin(admin.ModelAdmin):
    """Admin interface for Audit Logs (Security Audit Trail)"""

    list_display = ('created_at', 'user_email', 'action_type', 'entity_type', 'entity_id', 'ip_address')
    list_filter = ('action_type', 'created_at', 'user')
    search_fields = ('user__email', 'entity_type', 'entity_id', 'description', 'ip_address')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Action Details', {
            'fields': ('user', 'action_type', 'entity_type', 'entity_id', 'description')
        }),
        ('Request Details', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )

    readonly_fields = ('user', 'action_type', 'entity_type', 'entity_id', 'description',
                       'ip_address', 'user_agent', 'created_at')

    def user_email(self, obj):
        return obj.user.email if obj.user else 'System/Unknown'
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'

    def has_add_permission(self, request):
        # Prevent manual creation of audit logs
        return False

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of audit logs for security
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Database Backup & Restore (CTRL-0000001040, 1382)
# ──────────────────────────────────────────────────────────────────────────────

class RestoreForm(forms.Form):
    backup_file = forms.FileField(
        label='Backup file (.dump)',
        help_text='Upload a pg_dump backup file previously created by this system.',
    )
    confirm = forms.BooleanField(
        label='I understand this will permanently overwrite all current data',
        required=True,
    )


@admin.register(DatabaseBackup)
class DatabaseBackupAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'created_by', 'status_badge', 'size_display', 'created_at', 'download_btn')
    readonly_fields = ('created_at', 'created_by', 'filename', 'file_size', 'status', 'notes')
    list_filter = ('status',)

    def has_add_permission(self, request):
        return False  # created via the "Create Backup" button only

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('create/', self.admin_site.admin_view(self.create_backup_view), name='accounts_create_backup'),
            path('<int:pk>/download/', self.admin_site.admin_view(self.download_backup_view), name='accounts_download_backup'),
            path('restore/', self.admin_site.admin_view(self.restore_backup_view), name='accounts_restore_backup'),
        ]
        return custom + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['create_backup_url'] = reverse('admin:accounts_create_backup')
        extra_context['restore_backup_url'] = reverse('admin:accounts_restore_backup')
        return super().changelist_view(request, extra_context=extra_context)

    # ── column helpers ──────────────────────────────────────────────────────

    def status_badge(self, obj):
        colours = {
            DatabaseBackup.STATUS_COMPLETED: 'green',
            DatabaseBackup.STATUS_FAILED: 'red',
            DatabaseBackup.STATUS_CREATING: 'orange',
        }
        colour = colours.get(obj.status, 'grey')
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            colour, obj.get_status_display(),
        )
    status_badge.short_description = 'Status'

    def size_display(self, obj):
        if obj.file_size is None:
            return '—'
        for unit in ('B', 'KB', 'MB', 'GB'):
            if obj.file_size < 1024:
                return f'{obj.file_size:.1f} {unit}'
            obj.file_size /= 1024
        return f'{obj.file_size:.1f} TB'
    size_display.short_description = 'Size'

    def download_btn(self, obj):
        if obj.status != DatabaseBackup.STATUS_COMPLETED:
            return '—'
        url = reverse('admin:accounts_download_backup', args=[obj.pk])
        return format_html('<a class="button" href="{}">⬇ Download</a>', url)
    download_btn.short_description = 'Download'

    # ── views ───────────────────────────────────────────────────────────────

    def create_backup_view(self, request):
        backup_dir = settings.BACKUP_DIR
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f'tms_backup_{timestamp}.dump'
        filepath = backup_dir / filename

        record = DatabaseBackup.objects.create(
            created_by=request.user,
            filename=filename,
            status=DatabaseBackup.STATUS_CREATING,
            notes='Manual backup via admin panel.',
        )

        db = settings.DATABASES['default']
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
            record.file_size = filepath.stat().st_size
            record.status = DatabaseBackup.STATUS_COMPLETED
            record.save(update_fields=['file_size', 'status'])
            messages.success(request, f'Backup "{filename}" created ({record.file_size:,} bytes).')
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode(errors='replace') if exc.stderr else str(exc)
            record.status = DatabaseBackup.STATUS_FAILED
            record.notes = stderr
            record.save(update_fields=['status', 'notes'])
            messages.error(request, f'Backup failed: {stderr}')
        except Exception as exc:
            record.status = DatabaseBackup.STATUS_FAILED
            record.notes = str(exc)
            record.save(update_fields=['status', 'notes'])
            messages.error(request, f'Backup failed: {exc}')

        return HttpResponseRedirect(reverse('admin:accounts_databasebackup_changelist'))

    def download_backup_view(self, request, pk):
        backup = DatabaseBackup.objects.get(pk=pk)
        filepath = settings.BACKUP_DIR / backup.filename
        if not filepath.exists():
            messages.error(request, 'Backup file not found on disk.')
            return HttpResponseRedirect(reverse('admin:accounts_databasebackup_changelist'))
        response = FileResponse(open(filepath, 'rb'), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{backup.filename}"'
        return response

    def restore_backup_view(self, request):
        if not request.user.is_superuser:
            messages.error(request, 'Only superusers can perform a restore.')
            return HttpResponseRedirect(reverse('admin:accounts_databasebackup_changelist'))

        if request.method == 'POST':
            form = RestoreForm(request.POST, request.FILES)
            if form.is_valid():
                uploaded = request.FILES['backup_file']
                timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
                restore_path = settings.BACKUP_DIR / f'restore_{timestamp}_{uploaded.name}'
                with open(restore_path, 'wb') as f:
                    for chunk in uploaded.chunks():
                        f.write(chunk)

                db = settings.DATABASES['default']
                env = {**os.environ, 'PGPASSWORD': db.get('PASSWORD', '')}

                # Auto-snapshot current state before overwriting
                pre_filename = f'pre_restore_auto_{timestamp}.dump'
                pre_path = settings.BACKUP_DIR / pre_filename
                try:
                    subprocess.run(
                        ['pg_dump', '-h', db.get('HOST', 'localhost'),
                         '-p', str(db.get('PORT', 5432)),
                         '-U', db.get('USER', 'postgres'),
                         '-Fc', '-f', str(pre_path), db.get('NAME', '')],
                        env=env, check=True, capture_output=True,
                    )
                    DatabaseBackup.objects.create(
                        created_by=request.user,
                        filename=pre_filename,
                        file_size=pre_path.stat().st_size,
                        status=DatabaseBackup.STATUS_COMPLETED,
                        notes='Auto-snapshot created before restore operation.',
                    )
                except Exception as exc:
                    messages.warning(request, f'Pre-restore snapshot failed ({exc}). Proceeding anyway.')

                try:
                    subprocess.run(
                        ['pg_restore', '-h', db.get('HOST', 'localhost'),
                         '-p', str(db.get('PORT', 5432)),
                         '-U', db.get('USER', 'postgres'),
                         '-d', db.get('NAME', ''),
                         '--clean', '--if-exists', str(restore_path)],
                        env=env, check=True, capture_output=True,
                    )
                    messages.success(
                        request,
                        'Database restored successfully. '
                        'Your session has been cleared — please log in again.',
                    )
                    return HttpResponseRedirect('/admin/login/')
                except subprocess.CalledProcessError as exc:
                    stderr = exc.stderr.decode(errors='replace') if exc.stderr else str(exc)
                    messages.error(
                        request,
                        f'Restore failed: {stderr}. '
                        f'A pre-restore snapshot was saved as "{pre_filename}".',
                    )
        else:
            form = RestoreForm()

        context = {
            **self.admin_site.each_context(request),
            'title': 'Restore Database from Backup',
            'form': form,
            'opts': DatabaseBackup._meta,
        }
        return render(request, 'admin/accounts/restore_backup.html', context)
