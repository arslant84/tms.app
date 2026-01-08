"""
Test complete notification flow with email sending
"""
import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tms_project.settings')
django.setup()

from notifications.models import UserNotification, NotificationTemplate
from notifications.services import NotificationService
from accounts.models import User

# Email settings are now loaded from .env file automatically
print("Email settings loaded from .env file\n")

# Get a test user (the HOD who should receive accommodation notifications)
test_user = User.objects.filter(email='tekayev@outlook.com').first()

if not test_user:
    print("ERROR: Test user not found!")
    exit(1)

print(f"Test user: {test_user.email}")
print(f"User has notification preferences: {hasattr(test_user, 'notification_preferences')}\n")

# Get the approval_required template
template = NotificationTemplate.objects.get(name='approval_required')

# Build context like the workflow would
context = {
    'requestType': 'Accommodation Request',
    'entityId': 'ACCOM-20251223-TEST',
    'dueDate': '2025-12-25 10:00',
    'urgencyHint': 'Please review soon',
    'requestorName': 'Test Requester',
    'requestorEmail': 'requester@test.com',
    'approverName': test_user.get_full_name() if hasattr(test_user, 'get_full_name') else test_user.email,
    'stepName': 'Step 1: HOD Approval',
    'workflowName': 'Accommodation Approval Workflow',
    'actionUrl': '/accommodation/18',
}

# Render template
print("Rendering template...")
rendered = template.render(context)
print(f"Subject rendered: {len(rendered['subject'])} chars")
print(f"Body rendered: {len(rendered['body'])} chars")
print(f"Template variables replaced: {'{{' not in rendered['subject']}\n")

# Create notification with email
print("Creating notification with email...")
notification = NotificationService.create_notification(
    user=test_user,
    title=rendered['subject'],
    message=rendered['body'],
    priority='high',
    action_url='/accommodation/18',
    send_email=True  # This will send email!
)

print(f"Notification created: ID={notification.id}")

# Wait a bit for async email sending
print("Waiting for async email to send...")
time.sleep(5)

# Check notification status
notification.refresh_from_db()
print(f"\nNotification status:")
print(f"  Email sent at: {notification.email_sent_at}")
print(f"  Email error: {notification.email_error}")

if notification.email_sent_at:
    print("\n✓✓✓ SUCCESS! Email was sent successfully!")
elif notification.email_error:
    print(f"\n✗✗✗ ERROR: {notification.email_error}")
else:
    print("\n⚠ Email may still be sending (async)...")

print(f"\nCheck the email inbox for: {test_user.email}")
