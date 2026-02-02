#!/usr/bin/env python
"""Delete all test notifications"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tms_project.settings')
django.setup()

from notifications.models import UserNotification

# Delete all notifications
count = UserNotification.objects.count()
UserNotification.objects.all().delete()

print(f"✅ Deleted {count} test notifications")
print("✅ Notification system is now clean!")
