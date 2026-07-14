"""
Data migration: encrypt any plaintext values remaining in EncryptedTextField columns.

Migration 0009 changed the field types but did not re-encrypt existing rows.
This migration reads every row through the ORM (which triggers get_prep_value
and therefore Fernet encryption) and writes it back.
"""

from django.db import migrations
from utils.encryption import decrypt_value, encrypt_value


def is_already_encrypted(value):
    """Return True if the value looks like a Fernet token (starts with gAAAAA)."""
    if not value:
        return True
    try:
        # Fernet tokens are base64url and always start with this prefix
        return value.startswith("gAAAAA")
    except AttributeError:
        return True


def encrypt_existing_rows(apps, schema_editor):
    TrfAdvanceBankDetail = apps.get_model("trf", "TrfAdvanceBankDetail")
    TrfPassportDetail = apps.get_model("trf", "TrfPassportDetail")

    for obj in TrfAdvanceBankDetail.objects.all():
        changed = False
        if obj.account_number and not is_already_encrypted(obj.account_number):
            obj.account_number = encrypt_value(obj.account_number)
            changed = True
        if obj.account_name and not is_already_encrypted(obj.account_name):
            obj.account_name = encrypt_value(obj.account_name)
            changed = True
        if changed:
            TrfAdvanceBankDetail.objects.filter(pk=obj.pk).update(
                account_number=obj.account_number,
                account_name=obj.account_name,
            )

    for obj in TrfPassportDetail.objects.all():
        if obj.passport_number and not is_already_encrypted(obj.passport_number):
            encrypted = encrypt_value(obj.passport_number)
            TrfPassportDetail.objects.filter(pk=obj.pk).update(
                passport_number=encrypted,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("trf", "0009_alter_trfadvancebankdetail_account_name_and_more"),
    ]

    operations = [
        migrations.RunPython(
            encrypt_existing_rows,
            migrations.RunPython.noop,  # no reverse — ciphertext stays if rolled back
        ),
    ]
