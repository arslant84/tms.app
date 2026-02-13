# Generated migration for adding passport_file to VisaApplication

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('visa', '0003_add_request_number_to_visa'),
    ]

    operations = [
        migrations.AddField(
            model_name='visaapplication',
            name='passport_file',
            field=models.FileField(
                blank=True,
                help_text='Uploaded passport scan/photo for visa application',
                null=True,
                upload_to='visa/passports/'
            ),
        ),
    ]
