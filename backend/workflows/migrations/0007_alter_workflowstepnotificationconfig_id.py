# Generated migration to fix UUID primary key issue

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflows', '0006_alter_workflowstepnotificationconfig_event_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workflowstepnotificationconfig',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
    ]
