#!/usr/bin/env python
"""Check all view_all permissions and which roles have them"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tms_project.settings')
django.setup()

from accounts.models import Permission, Role

print("="*80)
print("VIEW ALL PERMISSIONS AUDIT")
print("="*80)

# Get all "view_all" and "view_admin" permissions
view_all_perms = Permission.objects.filter(name__icontains='view_all').order_by('name')
view_admin_perms = Permission.objects.filter(name__icontains='view_admin').order_by('name')

print("\n📋 View All Permissions (for seeing all requests across departments):")
if view_all_perms.exists():
    for p in view_all_perms:
        print(f"  - {p.name}: {p.description}")
        roles = p.role_set.all()
        if roles.exists():
            print(f"    Granted to: {', '.join([r.name for r in roles])}")
        else:
            print(f"    ⚠️  NOT granted to any role!")
else:
    print("  ⚠️  No 'view_all' permissions found!")

print("\n📋 View Admin Module Permissions (for accessing admin interfaces):")
if view_admin_perms.exists():
    for p in view_admin_perms:
        print(f"  - {p.name}: {p.description}")
        roles = p.role_set.all()
        if roles.exists():
            print(f"    Granted to: {', '.join([r.name for r in roles])}")
        else:
            print(f"    ⚠️  NOT granted to any role!")
else:
    print("  ⚠️  No 'view_admin' permissions found!")

# Check Transport Admin specifically
print("\n" + "="*80)
print("TRANSPORT ADMIN ANALYSIS")
print("="*80)

try:
    transport_admin = Role.objects.get(name='Transport Admin')
    perms = list(transport_admin.permissions.values_list('name', flat=True))

    print(f"\nTransport Admin has {len(perms)} permissions:")

    view_perms = [p for p in perms if 'view' in p.lower()]
    admin_perms = [p for p in perms if 'admin' in p.lower()]

    print(f"\nView permissions ({len(view_perms)}):")
    for p in sorted(view_perms):
        print(f"  - {p}")

    # Check if they have the right permissions
    has_view_all_transport = 'view_all_transport' in perms
    has_view_admin_transport = 'view_admin_transport' in perms

    print(f"\n✅ Has view_all_transport: {has_view_all_transport}")
    print(f"✅ Has view_admin_transport: {has_view_admin_transport}")

    if has_view_all_transport:
        print("  → Should see ALL transport requests")
    else:
        print("  ⚠️  Should NOT see all transport requests (only own)")

except Role.DoesNotExist:
    print("❌ Transport Admin role not found!")

# Check other admin roles
print("\n" + "="*80)
print("OTHER ADMIN ROLES ANALYSIS")
print("="*80)

admin_roles = ['Ticketing Admin', 'Visa Clerk', 'Accommodation Admin', 'Finance Clerk']
for role_name in admin_roles:
    try:
        role = Role.objects.get(name=role_name)
        perms = list(role.permissions.values_list('name', flat=True))
        view_all_perms = [p for p in perms if 'view_all' in p]

        print(f"\n{role_name}:")
        if view_all_perms:
            print(f"  ✅ View all permissions: {', '.join(view_all_perms)}")
        else:
            print(f"  ⚠️  No 'view_all' permissions (will only see own requests)")

    except Role.DoesNotExist:
        print(f"\n{role_name}: ❌ Not found")

print("\n" + "="*80)
print("RECOMMENDATIONS")
print("="*80)
print("""
The backend views are currently using hardcoded role names:
  ❌ if user.role.name == 'Transport Admin':

They should instead check permissions:
  ✅ if user.role.permissions.filter(name='view_all_transport').exists():

This way:
1. Any role can be granted view_all permissions
2. Works in any language
3. More flexible and maintainable
4. Consistent with permission-based access control
""")
