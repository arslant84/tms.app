# Remove all deprecated fields completely
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transport', '0003_make_deprecated_fields_nullable'),
    ]

    operations = [
        # Remove all deprecated fields
        migrations.RemoveField(
            model_name='transportrequest',
            name='_deprecated_title',
        ),
        migrations.RemoveField(
            model_name='transportrequest',
            name='_deprecated_transport_type',
        ),
        migrations.RemoveField(
            model_name='transportrequest',
            name='_deprecated_number_of_passengers',
        ),
        migrations.RemoveField(
            model_name='transportrequest',
            name='_deprecated_passenger_names',
        ),
        migrations.RemoveField(
            model_name='transportrequest',
            name='_deprecated_vehicle_type',
        ),
        migrations.RemoveField(
            model_name='transportrequest',
            name='_deprecated_special_requirements',
        ),
        migrations.RemoveField(
            model_name='transportrequest',
            name='_deprecated_estimated_cost',
        ),
        migrations.RemoveField(
            model_name='transportrequest',
            name='_deprecated_currency',
        ),
        migrations.RemoveField(
            model_name='transportrequest',
            name='_deprecated_additional_data',
        ),
    ]
