from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from .models import User, Role, Permission, RolePermission, ApplicationSetting, AdminActionLog


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
    """Admin interface for Admin Action Logs (Security Audit Trail)"""

    list_display = ('created_at', 'admin_email', 'action_type', 'entity_type', 'entity_id', 'ip_address')
    list_filter = ('action_type', 'created_at', 'admin')
    search_fields = ('admin__email', 'entity_type', 'entity_id', 'description', 'ip_address')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Action Details', {
            'fields': ('admin', 'action_type', 'entity_type', 'entity_id', 'description')
        }),
        ('Request Details', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )

    readonly_fields = ('admin', 'action_type', 'entity_type', 'entity_id', 'description',
                       'ip_address', 'user_agent', 'created_at')

    def admin_email(self, obj):
        return obj.admin.email if obj.admin else 'Unknown'
    admin_email.short_description = 'Admin User'
    admin_email.admin_order_field = 'admin__email'

    def has_add_permission(self, request):
        # Prevent manual creation of audit logs
        return False

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of audit logs for security
        return False
