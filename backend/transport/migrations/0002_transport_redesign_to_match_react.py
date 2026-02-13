# Generated manually - Transport module redesign to match React source
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('transport', '0001_initial'),
    ]

    operations = [
        # Add new fields
        migrations.AddField(
            model_name='transportrequest',
            name='requestor_name',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transportrequest',
            name='staff_id',
            field=models.CharField(default='', max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transportrequest',
            name='position',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transportrequest',
            name='tsr_reference',
            field=models.CharField(blank=True, help_text='TSR Reference if created from TSR', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='transportrequest',
            name='transport_details',
            field=models.JSONField(default=list, help_text='Array of transport detail objects'),
        ),
        migrations.AddField(
            model_name='transportrequest',
            name='confirm_policy',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='transportrequest',
            name='confirm_manager_approval',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='transportrequest',
            name='confirm_terms_and_conditions',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='transportrequest',
            name='booking_details',
            field=models.JSONField(blank=True, help_text='Booking details filled by transport admin', null=True),
        ),

        # Rename department from additional_data (if it exists)
        migrations.RenameField(
            model_name='transportrequest',
            old_name='additional_data',
            new_name='_deprecated_additional_data',
        ),
        migrations.AddField(
            model_name='transportrequest',
            name='department',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),

        # Update status field choices
        migrations.AlterField(
            model_name='transportrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('Draft', 'Draft'),
                    ('Pending Department Focal', 'Pending Department Focal'),
                    ('Pending Line Manager', 'Pending Line Manager'),
                    ('Pending HOD', 'Pending HOD'),
                    ('Approved', 'Approved'),
                    ('Processing with Transport Admin', 'Processing with Transport Admin'),
                    ('Completed', 'Completed'),
                    ('Rejected', 'Rejected'),
                    ('Cancelled', 'Cancelled'),
                ],
                default='Draft',
                max_length=50
            ),
        ),

        # Remove old fields (mark as deprecated first, can be removed in future migration)
        migrations.RenameField(
            model_name='transportrequest',
            old_name='title',
            new_name='_deprecated_title',
        ),
        migrations.RenameField(
            model_name='transportrequest',
            old_name='transport_type',
            new_name='_deprecated_transport_type',
        ),
        migrations.RenameField(
            model_name='transportrequest',
            old_name='number_of_passengers',
            new_name='_deprecated_number_of_passengers',
        ),
        migrations.RenameField(
            model_name='transportrequest',
            old_name='passenger_names',
            new_name='_deprecated_passenger_names',
        ),
        migrations.RenameField(
            model_name='transportrequest',
            old_name='vehicle_type',
            new_name='_deprecated_vehicle_type',
        ),
        migrations.RenameField(
            model_name='transportrequest',
            old_name='special_requirements',
            new_name='_deprecated_special_requirements',
        ),
        migrations.RenameField(
            model_name='transportrequest',
            old_name='estimated_cost',
            new_name='_deprecated_estimated_cost',
        ),
        migrations.RenameField(
            model_name='transportrequest',
            old_name='currency',
            new_name='_deprecated_currency',
        ),
    ]
