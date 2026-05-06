import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0031_user_mfa_enabled_user_mfa_secret_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="password_last_changed",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp of last password change. Used to enforce 30-day expiry for privileged accounts.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="last_access_review",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp of last formal access review by an administrator.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="last_access_review_by",
            field=models.ForeignKey(
                blank=True,
                help_text="Administrator who last reviewed this account access.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviewed_users",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="adminactionlog",
            name="action_type",
            field=models.CharField(
                choices=[
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
                    ("other", "Other Action"),
                ],
                max_length=50,
            ),
        ),
    ]
