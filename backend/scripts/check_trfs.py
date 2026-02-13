#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tms_project.settings')
django.setup()

from trf.models import TravelRequest

print("=" * 50)
print("TRF Database Check")
print("=" * 50)

total = TravelRequest.objects.count()
print(f"\nTotal TRFs in database: {total}")

if total > 0:
    print("\nRecent TRFs:")
    print("-" * 50)
    for trf in TravelRequest.objects.all().order_by('-created_at')[:10]:
        print(f"ID: {trf.id}")
        print(f"  Requestor: {trf.requestor_name}")
        print(f"  Status: {trf.status}")
        print(f"  Travel Type: {trf.travel_type}")
        print(f"  Created: {trf.created_at}")
        print(f"  Submitted: {trf.submitted_at}")
        print("-" * 50)
else:
    print("\nNo TRFs found in database!")

print("\n" + "=" * 50)
