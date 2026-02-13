#!/usr/bin/env python
"""Check Transport Admin permissions and flags"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tms_project.settings')
django.setup()

from accounts.models import User, Role, Permission

print("="*60)
print("CHECKING TRANSPORT ADMIN ACCESS TO USER MANAGEMENT")
print("="*60)

# Get Transport Admin role
try:
    transport_admin_role = Role.objects.get(name='Transport Admin')
    print(f"\n✓ Found role: {transport_admin_role.name}")
    print(f"  Description: {transport_admin_role.description}")

    # Check if role has manage_users permission
    has_manage_users = transport_admin_role.permissions.filter(name='manage_users').exists()
    print(f"\n🔍 Has 'manage_users' permission: {has_manage_users}")

    if has_manage_users:
        print("  ❌ PROBLEM: Transport Admin role has 'manage_users' permission!")
        print("  🔧 This permission should be removed.")

    # List all permissions for this role
    permissions = list(transport_admin_role.permissions.values_list('name', flat=True))
    print(f"\n📋 Total permissions: {len(permissions)}")
    print("\nAll permissions for Transport Admin:")
    for perm in sorted(permissions):
        print(f"  - {perm}")

    # Check for any admin-related permissions
    admin_perms = [p for p in permissions if 'manage' in p.lower() or 'admin' in p.lower() or 'system' in p.lower()]
    if admin_perms:
        print(f"\n⚠️  Found {len(admin_perms)} admin-like permissions:")
        for perm in admin_perms:
            print(f"  - {perm}")

except Role.DoesNotExist:
    print("\n❌ Transport Admin role not found!")

# Check users with Transport Admin role
print("\n" + "="*60)
print("CHECKING USERS WITH TRANSPORT ADMIN ROLE")
print("="*60)

transport_admins = User.objects.filter(role__name='Transport Admin')
print(f"\nFound {transport_admins.count()} users with Transport Admin role:\n")

for user in transport_admins:
    print(f"User: {user.email}")
    print(f"  Name: {user.name}")
    print(f"  is_admin flag: {user.is_admin}")
    print(f"  is_staff flag: {user.is_staff}")
    print(f"  is_superuser flag: {user.is_superuser}")

    if user.is_admin:
        print(f"  ❌ PROBLEM: User has is_admin=True!")
        print(f"  🔧 This flag should be removed: UPDATE accounts_user SET is_admin=false WHERE id={user.id}")

    if user.is_staff:
        print(f"  ⚠️  User has is_staff=True (can access Django admin)")

    if user.is_superuser:
        print(f"  ⚠️  User has is_superuser=True (full Django permissions)")

    print()

# Show fix commands
print("="*60)
print("FIX COMMANDS")
print("="*60)

print("\n1. To remove 'manage_users' permission from Transport Admin role:")
print("-" * 60)
print("""
python manage.py shell <<'EOF'
from accounts.models import Role, Permission

role = Role.objects.get(name='Transport Admin')
perm = Permission.objects.get(name='manage_users')
role.permissions.remove(perm)
print("✓ Removed 'manage_users' permission from Transport Admin role")
EOF
""")

if transport_admins.exists():
    print("\n2. To remove is_admin flag from Transport Admin users:")
    print("-" * 60)
    for user in transport_admins.filter(is_admin=True):
        print(f"""
python manage.py shell <<'EOF'
from accounts.models import User
user = User.objects.get(email='{user.email}')
user.is_admin = False
user.save()
print("✓ Removed is_admin flag from {user.email}")
EOF
""")

print("\n" + "="*60)
print("FRONTEND ACCESS CHECKS")
print("="*60)
print("""
The frontend checks User Management access via:
1. RBAC Service: canAccessAdminMenu(), hasPermission()
2. Checks for:
   - is_admin flag (grants ALL permissions)
   - Role name: 'System Administrator' or 'Admin'
   - Permission: 'manage_users'

To restrict access, ensure:
✓ is_admin = False on the user
✓ Role is NOT 'System Administrator' or 'Admin'
✓ Role does NOT have 'manage_users' permission
""")
