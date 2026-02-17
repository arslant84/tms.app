# Manual migration to fix UUID primary key
# The table is empty so we can safely drop and recreate it

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('workflows', '0007_alter_workflowstepnotificationconfig_id'),
        ('notifications', '0001_initial'),
    ]

    operations = [
        # Drop the existing table
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS workflows_workflowstepnotificationconfig CASCADE;',
            reverse_sql='SELECT 1;'  # No reverse - this is a fix
        ),
        
        # Recreate the table with UUID primary key
        migrations.CreateModel(
            name='WorkflowStepNotificationConfig',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_type', models.CharField(choices=[('assignment', 'On Step Assignment'), ('approval', 'On Step Approval'), ('rejection', 'On Step Rejection'), ('escalation', 'On Step Escalation'), ('reminder', 'Reminder Notification'), ('delegation', 'On Step Delegation'), ('workflow_completed', 'When All Approvals Complete'), ('workflow_cancelled', 'When Workflow Cancelled')], default='assignment', help_text='Workflow event that triggers this notification', max_length=50)),
                ('recipient_types', models.JSONField(default=list, help_text="List of recipient types (e.g., ['current_approver', 'requester'])")),
                ('custom_recipients', models.JSONField(blank=True, default=list, help_text='List of custom email addresses')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this notification configuration is active')),
                ('send_email', models.BooleanField(default=True, help_text='Send as email notification')),
                ('send_system_notification', models.BooleanField(default=True, help_text='Send as in-app system notification')),
                ('priority', models.CharField(choices=[('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')], default='normal', help_text='Notification priority level', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('notification_template', models.ForeignKey(help_text='Template to use for this notification', on_delete=django.db.models.deletion.CASCADE, related_name='workflow_step_configs', to='notifications.notificationtemplate')),
                ('workflow_step', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notification_configs', to='workflows.workflowstep')),
            ],
            options={
                'verbose_name': 'Workflow Step Notification Configuration',
                'verbose_name_plural': 'Workflow Step Notification Configurations',
                'ordering': ['workflow_step', 'event_type'],
            },
        ),
    ]
