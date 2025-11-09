from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import json
import uuid


class Permission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    permissions = models.ManyToManyField(Permission, through='RolePermission')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('role', 'permission')


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_admin', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        # Create an admin role if it doesn't exist
        admin_role, created = Role.objects.get_or_create(name='Admin')
        extra_fields.setdefault('role', admin_role)

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)
    name = models.CharField(max_length=255)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.CharField(max_length=100, blank=True)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=50, default='Active')  # Matches syntra schema
    staff_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    profile_photo = models.TextField(blank=True, null=True)  # Changed to TextField for base64 images
    gender = models.CharField(max_length=10, blank=True, null=True)
    last_login_at = models.DateTimeField(blank=True, null=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    
    def __str__(self):
        return self.email
    
    @property
    def first_name(self):
        names = self.name.split()
        return names[0] if names else ''
    
    @property
    def last_name(self):
        names = self.name.split()
        return ' '.join(names[1:]) if len(names) > 1 else ''


class ApplicationSetting(models.Model):
    """
    Application-wide settings that can be configured dynamically.
    Matches the source project structure for system configuration.
    """
    SETTING_TYPES = (
        ('string', 'String'),
        ('boolean', 'Boolean'),
        ('number', 'Number'),
        ('json', 'JSON'),
    )

    setting_key = models.CharField(max_length=255, unique=True, db_index=True)
    setting_value = models.TextField()
    setting_type = models.CharField(max_length=20, choices=SETTING_TYPES, default='string')
    description = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(default=False, help_text='Whether this setting can be accessed without authentication')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['setting_key']
        verbose_name = 'Application Setting'
        verbose_name_plural = 'Application Settings'

    def __str__(self):
        return f"{self.setting_key} = {self.setting_value}"

    def get_value(self):
        """Get the setting value in its proper type"""
        if self.setting_type == 'boolean':
            return self.setting_value.lower() in ('true', '1', 'yes')
        elif self.setting_type == 'number':
            try:
                return float(self.setting_value) if '.' in self.setting_value else int(self.setting_value)
            except ValueError:
                return 0
        elif self.setting_type == 'json':
            try:
                return json.loads(self.setting_value)
            except json.JSONDecodeError:
                return {}
        return self.setting_value

    def set_value(self, value):
        """Set the setting value from a Python object"""
        if self.setting_type == 'boolean':
            self.setting_value = 'true' if value else 'false'
        elif self.setting_type == 'number':
            self.setting_value = str(value)
        elif self.setting_type == 'json':
            self.setting_value = json.dumps(value)
        else:
            self.setting_value = str(value)
        self.save()

    @staticmethod
    def get_setting(key, default=None):
        """Helper method to get a setting value by key"""
        try:
            setting = ApplicationSetting.objects.get(setting_key=key)
            return setting.get_value()
        except ApplicationSetting.DoesNotExist:
            return default

    @staticmethod
    def set_setting(key, value, setting_type='string', description='', is_public=False):
        """Helper method to set a setting value"""
        setting, created = ApplicationSetting.objects.get_or_create(
            setting_key=key,
            defaults={
                'setting_type': setting_type,
                'description': description,
                'is_public': is_public
            }
        )
        setting.set_value(value)
        return setting


class AdminActionLog(models.Model):
    """
    Audit log for administrative override actions.
    Tracks when admins bypass normal workflows or permissions.
    """
    ACTION_TYPES = (
        ('approval_override', 'Approval Workflow Override'),
        ('permission_override', 'Permission Override'),
        ('data_modification', 'Direct Data Modification'),
        ('settings_change', 'Settings Change'),
        ('user_modification', 'User Account Modification'),
        ('other', 'Other Administrative Action'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='admin_actions')
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    entity_type = models.CharField(max_length=255, help_text='Type of entity affected (e.g., TransportRequest, TravelRequest)')
    entity_id = models.CharField(max_length=255, help_text='ID of the affected entity')
    description = models.TextField(help_text='Description of the action taken')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Admin Action Log'
        verbose_name_plural = 'Admin Action Logs'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['admin', '-created_at']),
            models.Index(fields=['action_type', '-created_at']),
        ]

    def __str__(self):
        return f"{self.admin.email if self.admin else 'Unknown'} - {self.action_type} - {self.created_at}"

    @staticmethod
    def log_action(admin, action_type, entity_type, entity_id, description, request=None):
        """Helper method to create an audit log entry"""
        log_data = {
            'admin': admin,
            'action_type': action_type,
            'entity_type': entity_type,
            'entity_id': str(entity_id),
            'description': description,
        }

        # Extract IP address and user agent from request if available
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                log_data['ip_address'] = x_forwarded_for.split(',')[0]
            else:
                log_data['ip_address'] = request.META.get('REMOTE_ADDR')
            log_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')

        return AdminActionLog.objects.create(**log_data)
