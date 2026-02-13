# Make deprecated fields nullable
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transport', '0002_transport_redesign_to_match_react'),
    ]

    operations = [
        # Make all deprecated fields nullable
        migrations.AlterField(
            model_name='transportrequest',
            name='_deprecated_title',
            field=models.CharField(max_length=255, blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='transportrequest',
            name='_deprecated_transport_type',
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='transportrequest',
            name='_deprecated_number_of_passengers',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='transportrequest',
            name='_deprecated_passenger_names',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='transportrequest',
            name='_deprecated_vehicle_type',
            field=models.CharField(max_length=100, blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='transportrequest',
            name='_deprecated_special_requirements',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='transportrequest',
            name='_deprecated_estimated_cost',
            field=models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='transportrequest',
            name='_deprecated_currency',
            field=models.CharField(max_length=3, blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='transportrequest',
            name='_deprecated_additional_data',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
