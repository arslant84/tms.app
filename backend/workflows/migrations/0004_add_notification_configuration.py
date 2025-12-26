# Manual migration to add notification configuration
# Deletes old table and creates fresh

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_refactor_permissions'),
        ('notifications', '0003_cleanup_unused_event_types'),
        ('workflows', '0003_add_approver_permission'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Create new model from scratch
        migrations.CreateModel(
            name='WorkflowStepNotificationConfig',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('trigger_event', models.CharField(choices=[('step_created', 'When Step is Created (Approval Requested)'), ('step_approved', 'When Step is Approved'), ('step_rejected', 'When Step is Rejected'), ('step_delegated', 'When Step is Delegated'), ('step_escalated', 'When Step is Escalated'), ('step_skipped', 'When Step is Skipped')], default='step_created', help_text='Event that triggers this notification', max_length=50)),
                ('recipient_type', models.CharField(choices=[('approver', 'Step Approver'), ('requestor', 'Original Requestor'), ('next_approver', 'Next Step Approver'), ('previous_approvers', 'All Previous Approvers'), ('role', 'Specific Role(s)'), ('user', 'Specific User(s)'), ('department_head', 'Department Head'), ('all_approvers', 'All Approvers in Workflow')], default='approver', help_text='Who should receive this notification (TO field)', max_length=50)),
                ('cc_requestor', models.BooleanField(default=False, help_text='CC the original requestor')),
                ('cc_previous_approvers', models.BooleanField(default=False, help_text='CC all previous approvers in the workflow')),
                ('cc_next_approver', models.BooleanField(default=False, help_text='CC the next approver in workflow')),
                ('send_in_app', models.BooleanField(default=True, help_text='Send as in-app notification')),
                ('send_email', models.BooleanField(default=True, help_text='Send as email notification')),
                ('send_push', models.BooleanField(default=False, help_text='Send as push notification (future feature)')),
                ('custom_subject', models.CharField(blank=True, help_text='Custom email subject (optional, overrides template)', max_length=500, null=True)),
                ('custom_message', models.TextField(blank=True, help_text='Custom email message (optional, overrides template)', null=True)),
                ('is_active', models.BooleanField(default=True, help_text='Whether this configuration is active')),
                ('priority', models.CharField(choices=[('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')], default='normal', help_text='Notification priority level', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bcc_roles', models.ManyToManyField(blank=True, help_text='Roles to BCC (for audit/compliance)', related_name='workflow_notification_bcc', to='accounts.role')),
                ('bcc_users', models.ManyToManyField(blank=True, help_text='Users to BCC', related_name='workflow_notification_bcc', to=settings.AUTH_USER_MODEL)),
                ('cc_roles', models.ManyToManyField(blank=True, help_text='Additional roles to CC', related_name='workflow_notification_cc', to='accounts.role')),
                ('cc_users', models.ManyToManyField(blank=True, help_text='Additional users to CC', related_name='workflow_notification_cc', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(blank=True, help_text='User who created this configuration', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_workflow_notification_configs', to=settings.AUTH_USER_MODEL)),
                ('notification_template', models.ForeignKey(blank=True, help_text='Email template to use (optional, uses default if not set)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='workflow_configs', to='notifications.notificationtemplate')),
                ('recipient_roles', models.ManyToManyField(blank=True, help_text="Roles to notify (if recipient_type='role')", related_name='workflow_notification_to', to='accounts.role')),
                ('recipient_users', models.ManyToManyField(blank=True, help_text="Specific users to notify (if recipient_type='user')", related_name='workflow_notification_to', to=settings.AUTH_USER_MODEL)),
                ('workflow_step', models.ForeignKey(help_text='Workflow step this notification configuration applies to', on_delete=django.db.models.deletion.CASCADE, related_name='notification_configs', to='workflows.workflowstep')),
            ],
            options={
                'db_table': 'workflow_step_notification_configs',
                'ordering': ['workflow_step', 'trigger_event'],
                'indexes': [
                    models.Index(fields=['workflow_step', 'trigger_event', 'is_active'], name='workflow_st_workflo_9067f0_idx'),
                    models.Index(fields=['is_active'], name='workflow_st_is_acti_1ac893_idx'),
                ],
            },
        ),
    ]
