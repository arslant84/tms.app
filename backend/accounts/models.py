import json
import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


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
    permissions = models.ManyToManyField(Permission, through="RolePermission")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("role", "permission")


class Department(models.Model):
    """
    Department model for organizing users into departments.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text="Short code for the department (e.g., IT, HR)",
    )
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.password_last_changed = timezone.now()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_admin", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        # Create an admin role if it doesn't exist
        admin_role, created = Role.objects.get_or_create(name="Admin")
        extra_fields.setdefault("role", admin_role)

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(_("email address"), unique=True)
    name = models.CharField(max_length=255)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=50, default="Active")  # Matches syntra schema
    staff_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    position = models.CharField(
        max_length=255, blank=True, null=True, help_text="Job title / position"
    )
    profile_photo = models.TextField(
        blank=True, null=True
    )  # Changed to TextField for base64 images
    gender = models.CharField(max_length=10, blank=True, null=True)
    last_login_at = models.DateTimeField(blank=True, null=True)
    password_change_required = models.BooleanField(
        default=False, help_text="User must change password on next login"
    )
    password_reset_token = models.CharField(
        max_length=64, blank=True, null=True, help_text="Token for password reset"
    )
    password_reset_token_expires = models.DateTimeField(
        blank=True, null=True, help_text="Expiry time for reset token"
    )

    # MFA fields — CTRL-0000001024 / CTRL-0000001063
    mfa_enabled = models.BooleanField(
        default=False, help_text="Whether TOTP MFA is enabled for this account"
    )
    mfa_secret = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="TOTP secret (base32). Null until MFA is set up.",
    )

    # Password age tracking — CTRL-0000001025 / CTRL-0000001061
    password_last_changed = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp of last password change. Used to enforce 30-day expiry for privileged accounts.",
    )

    # Access review tracking — CTRL-0000001018
    last_access_review = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp of last formal access review by an administrator.",
    )
    last_access_review_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_users",
        help_text="Administrator who last reviewed this account access.",
    )

    # Privacy consent fields — CTRL-0000001000 / CTRL-0000001001 / CTRL-0000001003
    privacy_consent = models.BooleanField(
        default=False, help_text="User accepted the privacy policy at registration"
    )
    privacy_consent_date = models.DateTimeField(
        blank=True, null=True, help_text="Timestamp when privacy consent was given"
    )
    privacy_policy_version = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Version of the privacy policy accepted",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return self.email

    @property
    def first_name(self):
        names = self.name.split()
        return names[0] if names else ""

    @property
    def last_name(self):
        names = self.name.split()
        return " ".join(names[1:]) if len(names) > 1 else ""


class ApplicationSetting(models.Model):
    """
    Application-wide settings that can be configured dynamically.
    Matches the source project structure for system configuration.
    """

    SETTING_TYPES = (
        ("string", "String"),
        ("boolean", "Boolean"),
        ("number", "Number"),
        ("json", "JSON"),
    )

    setting_key = models.CharField(max_length=255, unique=True, db_index=True)
    setting_value = models.TextField()
    setting_type = models.CharField(
        max_length=20, choices=SETTING_TYPES, default="string"
    )
    description = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(
        default=False,
        help_text="Whether this setting can be accessed without authentication",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["setting_key"]
        verbose_name = "Application Setting"
        verbose_name_plural = "Application Settings"

    def __str__(self):
        return f"{self.setting_key} = {self.setting_value}"

    def get_value(self):
        """Get the setting value in its proper type"""
        if self.setting_type == "boolean":
            return self.setting_value.lower() in ("true", "1", "yes")
        elif self.setting_type == "number":
            try:
                return (
                    float(self.setting_value)
                    if "." in self.setting_value
                    else int(self.setting_value)
                )
            except ValueError:
                return 0
        elif self.setting_type == "json":
            try:
                return json.loads(self.setting_value)
            except json.JSONDecodeError:
                return {}
        return self.setting_value

    def set_value(self, value):
        """Set the setting value from a Python object"""
        if self.setting_type == "boolean":
            self.setting_value = "true" if value else "false"
        elif self.setting_type == "number":
            self.setting_value = str(value)
        elif self.setting_type == "json":
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
    def set_setting(key, value, setting_type="string", description="", is_public=False):
        """Helper method to set a setting value"""
        setting, created = ApplicationSetting.objects.get_or_create(
            setting_key=key,
            defaults={
                "setting_type": setting_type,
                "description": description,
                "is_public": is_public,
            },
        )
        setting.set_value(value)
        return setting


class AdminActionLog(models.Model):
    """
    Audit log for user actions and security-relevant events.
    Tracks actions by all users for compliance, security monitoring, and incident response.
    Note: Despite the name 'AdminActionLog', this tracks actions by all users, not just admins.
    """

    ACTION_TYPES = (
        ("user_created", "User Account Created"),
        ("user_deleted", "User Account Deleted"),
        ("user_deactivated", "User Account Deactivated"),
        ("user_activated", "User Account Activated"),
        ("user_role_changed", "User Role Changed"),
        ("user_permissions_changed", "User Permissions Changed"),
        ("password_reset_admin", "Password Reset by Admin"),
        ("password_change_forced", "Forced Password Change"),
        ("password_changed", "Password Changed"),
        ("login_success", "Successful Login"),
        ("login_failed", "Failed Login Attempt"),
        ("logout", "User Logout"),
        ("role_created", "Role Created"),
        ("role_deleted", "Role Deleted"),
        ("role_permissions_modified", "Role Permissions Modified"),
        ("settings_change", "Application Settings Changed"),
        ("approval_override", "Approval Workflow Override"),
        ("permission_override", "Permission Override"),
        ("data_modification", "Direct Data Modification"),
        ("mfa_enabled", "MFA Enabled"),
        ("mfa_disabled", "MFA Disabled"),
        ("mfa_failed", "MFA Verification Failed"),
        ("privacy_consent_given", "Privacy Consent Given"),
        ("access_review", "Access Review Completed"),
        ("password_expired", "Password Expired — Change Forced"),
        ("workflow_step_approved", "Workflow Step Approved"),
        ("workflow_step_rejected", "Workflow Step Rejected"),
        ("workflow_bulk_approve", "Bulk Workflow Approval"),
        ("workflow_bulk_reject", "Bulk Workflow Rejection"),
        ("other", "Other Action"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="User who performed the action",
    )
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    entity_type = models.CharField(
        max_length=255,
        blank=True,
        help_text="Type of entity affected (e.g., User, Role, Permission)",
    )
    entity_id = models.CharField(
        max_length=255, blank=True, help_text="ID of the affected entity"
    )
    description = models.TextField(help_text="Description of the action taken")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["action_type", "-created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]

    def __str__(self):
        user_email = self.user.email if self.user else "System/Unknown"
        return f"{user_email} - {self.get_action_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    @staticmethod
    def log_action(
        user, action_type, description, entity_type="", entity_id="", request=None
    ):
        """
        Helper method to create an audit log entry.

        Args:
            user: User object who performed the action (can be None for system actions)
            action_type: Type of action from ACTION_TYPES choices
            description: Human-readable description of the action
            entity_type: Optional type of entity affected (e.g., 'User', 'Role')
            entity_id: Optional ID of the affected entity
            request: Optional HttpRequest object to extract IP and user agent

        Returns:
            AdminActionLog instance
        """
        log_data = {
            "user": user,
            "action_type": action_type,
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id else "",
            "description": description,
        }

        # Extract IP address and user agent from request if available
        if request:
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for:
                log_data["ip_address"] = x_forwarded_for.split(",")[0].strip()
            else:
                log_data["ip_address"] = request.META.get("REMOTE_ADDR")
            log_data["user_agent"] = request.META.get("HTTP_USER_AGENT", "")[
                :500
            ]  # Limit length

        instance = AdminActionLog.objects.create(**log_data)

        # Forward every audit event to the SIEM log file (CTRL-0000001356)
        try:
            from utils.siem_logger import log_security_event

            log_security_event(
                action_type=action_type,
                description=description,
                user=user,
                ip_address=log_data.get("ip_address"),
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id else "",
            )
        except Exception:
            pass  # Never let SIEM logging break the audit trail itself

        return instance


class DatabaseBackup(models.Model):
    """
    Tracks pg_dump backup files created by backup_db management command (CTRL-0000001040).
    """

    STATUS_CREATING = "creating"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_CREATING, "Creating"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_CREATING
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Database Backup"
        verbose_name_plural = "Database Backups"

    def __str__(self):
        return f"Backup {self.created_at:%Y-%m-%d %H:%M} ({self.get_status_display()})"
