from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('combined_request', '0003_add_all_missing_fields_fix_transport_segment'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='combinedrequest',
            name='estimated_cost',
        ),
    ]
