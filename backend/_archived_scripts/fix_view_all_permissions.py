#!/usr/bin/env python
"""Create missing view_all permissions and grant to admin roles"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tms_project.settings')
django.setup()

from accounts.models import Permission, Role
import uuid

print("="*80)
print("FIXING VIEW_ALL PERMISSIONS")
print("="*80)

# Define the permissions that should exist
needed_permissions = [
    {
        'name': 'view_all_trf',
        'description': 'Can view all TRFs across departments.',
        'roles': ['System Administrator', 'Ticketing Admin']  # Ticketing Admin needs to see all TRFs to book flights
    },
    {
        'name': 'view_all_transport',
        'description': 'Can view all transport requests across departments.',
        'roles': ['System Administrator', 'Transport Admin']
    },
    {
        'name': 'view_all_visa',
        'description': 'Can view all visa requests across departments.',
        'roles': ['System Administrator', 'Visa Clerk']
    },
    {
        'name': 'view_all_accommodation',
        'description': 'Can view all accommodation requests across departments.',
        'roles': ['System Administrator', 'Accommodation Admin']
    },
    {
        'name': 'view_all_claims',
        'description': 'Can view all Claims across departments.',
        'roles': ['System Administrator', 'Finance Clerk', 'HOD']
    },
]

# Create/update permissions and grant to roles
for perm_data in needed_permissions:
    print(f"\nProcessing permission: {perm_data['name']}")

    # Get or create permission
    perm, created = Permission.objects.get_or_create(
        name=perm_data['name'],
        defaults={
            'id': uuid.uuid4(),
            'description': perm_data['description']
        }
    )

    if created:
        print(f"  ✅ Created permission: {perm.name}")
    else:
        print(f"  ℹ️  Permission already exists: {perm.name}")
        # Update description if changed
        if perm.description != perm_data['description']:
            perm.description = perm_data['description']
            perm.save()
            print(f"  ✅ Updated description")

    # Grant to roles
    for role_name in perm_data['roles']:
        try:
            role = Role.objects.get(name=role_name)

            if not role.permissions.filter(id=perm.id).exists():
                role.permissions.add(perm)
                print(f"  ✅ Granted to {role_name}")
            else:
                print(f"  ℹ️  {role_name} already has this permission")

        except Role.DoesNotExist:
            print(f"  ⚠️  Role '{role_name}' not found, skipping")

# Verify the results
print("\n" + "="*80)
print("VERIFICATION")
print("="*80)

for perm_data in needed_permissions:
    perm = Permission.objects.get(name=perm_data['name'])
    roles = perm.role_set.all()
    print(f"\n{perm.name}:")
    print(f"  Granted to: {', '.join([r.name for r in roles])}")

print("\n" + "="*80)
print("✅ VIEW_ALL PERMISSIONS FIXED!")
print("="*80)
print("""
Next step: Update backend views to use these permissions instead of hardcoded role names.

Example:
  OLD: if user.role.name == 'Transport Admin':
  NEW: if user.role.permissions.filter(name='view_all_transport').exists():
""")
