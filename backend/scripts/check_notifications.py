#!/usr/bin/env python
"""Check notification status and email sending"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tms_project.settings')
django.setup()

from notifications.models import UserNotification
from django.utils import timezone
from datetime import timedelta

# Check recent notifications
recent = UserNotification.objects.filter(
    created_at__gte=timezone.now() - timedelta(days=7)
).order_by('-created_at')

print(f"Recent notifications (last 7 days): {recent.count()}\n")

if recent.count() > 0:
    print("Sample of recent notifications:")
    print("-" * 80)
    for notif in recent[:5]:
        print(f"Title: {notif.title}")
        print(f"User: {notif.user.email}")
        print(f"Created: {notif.created_at}")
        print(f"Email sent: {notif.sent_via_email}")
        if notif.email_sent_at:
            print(f"Email sent at: {notif.email_sent_at}")
        if notif.email_error:
            print(f"Email error: {notif.email_error}")
        print("-" * 80)

# Check email configuration
from accounts.models import ApplicationSetting
from django.conf import settings

print("\n\nDatabase SMTP Settings:")
print("-" * 80)
smtp_keys = ['smtp_host', 'smtp_port', 'smtp_use_tls', 'smtp_username', 'default_from_email', 'enable_email_notifications']
for key in smtp_keys:
    val = ApplicationSetting.get_setting(key)
    print(f"{key}: {val}")

print("\n\nDjango Active EMAIL Settings:")
print("-" * 80)
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
