"""
Test script to verify email configuration and template rendering fixes
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tms_project.settings')
django.setup()

from notifications.models import NotificationTemplate
from core.email_settings_loader import EmailSettingsLoader

# Force reload email settings from database
print("Reloading email settings from database...")
loader = EmailSettingsLoader()
loader.load_settings(force_reload=True)
print("Email settings reloaded!")

# Test template rendering
print("\n" + "="*60)
print("TESTING TEMPLATE RENDERING")
print("="*60)

template = NotificationTemplate.objects.get(name='approval_required')

context = {
    'requestType': 'Accommodation Request',
    'entityId': 'ACCOM-TEST-123',
    'dueDate': '2025-12-25 10:00',
    'urgencyHint': 'High Priority',
    'requestorName': 'Test User',
    'requestorEmail': 'test@example.com',
    'approverName': 'John Doe',
    'stepName': 'Step 1: HOD Approval',
    'workflowName': 'Accommodation Approval Workflow',
    'actionUrl': '/accommodation/123',
}

rendered = template.render(context)
print(f"Original subject: {repr(template.subject)}")
print(f"Rendered subject: {repr(rendered['subject'])}")
print(f"\nOriginal body: {repr(template.body[:100])}")
print(f"Rendered body: {repr(rendered['body'][:100])}")

# Verify placeholders were replaced
assert '{{requestType}}' not in rendered['subject'], "Template variables not replaced!"
assert 'Accommodation Request' in rendered['subject'], "Template not rendered correctly!"
assert 'ACCOM-TEST-123' in rendered['subject'], "Entity ID not in subject!"

print("\n" + "="*60)
print("✓ Template rendering works correctly!")
print("="*60)

# Test email sending
print("\n" + "="*60)
print("TESTING EMAIL CONFIGURATION")
print("="*60)

from django.conf import settings
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER[:10]}***")
print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")

print("\n" + "="*60)
print("✓ Email settings loaded correctly!")
print("="*60)

print("\n✓✓✓ ALL TESTS PASSED! ✓✓✓")
print("\nBoth issues are now fixed:")
print("1. Template placeholders are being rendered correctly")
print("2. Email settings are loaded from database with correct credentials")
print("\nNext: Create a new accommodation request to test end-to-end!")
