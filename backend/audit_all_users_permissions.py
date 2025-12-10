#!/usr/bin/env python
"""Audit all users and roles to find permission inconsistencies"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tms_project.settings')
django.setup()

from accounts.models import User, Role, Permission

print("="*80)
print("COMPLETE PERMISSION AUDIT")
print("="*80)

# Get all roles
roles = Role.objects.all().order_by('name')

print(f"\n📊 Found {roles.count()} roles in the system\n")

for role in roles:
    print("="*80)
    print(f"ROLE: {role.name}")
    print("="*80)
    print(f"Description: {role.description}")

    # Get all users with this role
    users = User.objects.filter(role=role)
    print(f"\nUsers with this role: {users.count()}")
    for user in users:
        flags = []
        if user.is_admin:
            flags.append("is_admin=True ⚠️")
        if user.is_staff:
            flags.append("is_staff=True")
        if user.is_superuser:
            flags.append("is_superuser=True ⚠️")

        flag_str = ", ".join(flags) if flags else "No special flags"
        print(f"  - {user.email} ({user.name}) - {flag_str}")

    # Get permissions
    perms = list(role.permissions.values_list('name', flat=True))
    print(f"\nPermissions: {len(perms)}")

    # Categorize permissions
    admin_perms = [p for p in perms if 'manage' in p.lower() or 'system' in p.lower()]
    view_admin_perms = [p for p in perms if 'view_admin' in p.lower()]
    approval_perms = [p for p in perms if 'approve' in p.lower()]
    create_perms = [p for p in perms if 'create' in p.lower()]
    other_perms = [p for p in perms if p not in admin_perms and p not in view_admin_perms and p not in approval_perms and p not in create_perms]

    if admin_perms:
        print(f"\n  🔧 Admin/Management Permissions ({len(admin_perms)}):")
        for p in sorted(admin_perms):
            print(f"    - {p}")

    if view_admin_perms:
        print(f"\n  👁️  View Admin Module Permissions ({len(view_admin_perms)}):")
        for p in sorted(view_admin_perms):
            print(f"    - {p}")

    if approval_perms:
        print(f"\n  ✅ Approval Permissions ({len(approval_perms)}):")
        for p in sorted(approval_perms):
            print(f"    - {p}")

    if create_perms:
        print(f"\n  ➕ Create Permissions ({len(create_perms)}):")
        for p in sorted(create_perms):
            print(f"    - {p}")

    if other_perms:
        print(f"\n  📝 Other Permissions ({len(other_perms)}):")
        for p in sorted(other_perms):
            print(f"    - {p}")

    print()

# Check for problematic patterns
print("\n" + "="*80)
print("PERMISSION AUDIT FINDINGS")
print("="*80)

issues = []

# Check 1: Users with is_admin flag
admin_flagged_users = User.objects.filter(is_admin=True).exclude(role__name__in=['System Administrator', 'Admin'])
if admin_flagged_users.exists():
    issues.append(f"⚠️  {admin_flagged_users.count()} non-admin users have is_admin=True flag")
    for user in admin_flagged_users:
        print(f"  - {user.email} ({user.role.name if user.role else 'No role'}) has is_admin=True")

# Check 2: Roles with manage_users that shouldn't
risky_roles = Role.objects.filter(permissions__name='manage_users').exclude(name__in=['System Administrator', 'Admin'])
if risky_roles.exists():
    issues.append(f"⚠️  {risky_roles.count()} non-admin roles have 'manage_users' permission")
    for role in risky_roles:
        print(f"  - {role.name} has 'manage_users' permission")

# Check 3: Roles with manage_roles that shouldn't
risky_roles2 = Role.objects.filter(permissions__name='manage_roles').exclude(name__in=['System Administrator', 'Admin'])
if risky_roles2.exists():
    issues.append(f"⚠️  {risky_roles2.count()} non-admin roles have 'manage_roles' permission")
    for role in risky_roles2:
        print(f"  - {role.name} has 'manage_roles' permission")

# Check 4: Roles with system_admin that shouldn't
risky_roles3 = Role.objects.filter(permissions__name='system_admin').exclude(name__in=['System Administrator', 'Admin'])
if risky_roles3.exists():
    issues.append(f"⚠️  {risky_roles3.count()} non-admin roles have 'system_admin' permission")
    for role in risky_roles3:
        print(f"  - {role.name} has 'system_admin' permission")

# Check 5: Users with superuser flag
superusers = User.objects.filter(is_superuser=True).exclude(role__name='System Administrator')
if superusers.exists():
    issues.append(f"⚠️  {superusers.count()} non-system-admin users have is_superuser=True")
    for user in superusers:
        print(f"  - {user.email} ({user.role.name if user.role else 'No role'}) has is_superuser=True")

if not issues:
    print("\n✅ No permission issues found!")
else:
    print(f"\n❌ Found {len(issues)} potential issues:")
    for issue in issues:
        print(f"  {issue}")

# Recommendations
print("\n" + "="*80)
print("RECOMMENDATIONS")
print("="*80)

print("""
To ensure proper permission enforcement:

1. ✅ ONLY these roles should have system permissions:
   - System Administrator (system_admin, manage_users, manage_roles)
   - Admin (manage_users, manage_roles)

2. ✅ Module admin roles should ONLY have their module permissions:
   - Transport Admin → view_admin_transport, manage_transport_requests
   - Accommodation Admin → view_admin_accommodation, manage_accommodation_bookings
   - Ticketing Admin → view_admin_flights, manage_flights
   - Visa Clerk → view_admin_visa, process_visa_applications
   - Finance Clerk → view_admin_claims, process_claims

3. ✅ User flags should be set correctly:
   - is_admin = True ONLY for System Administrator and Admin users
   - is_staff = True ONLY if user needs Django admin access
   - is_superuser = True ONLY for System Administrator

4. ✅ Approval roles should have workflow permissions:
   - Department Focal → approve_trf, approve_claims, approve_visa, approve_transport, approve_accommodation
   - Line Manager → approve_trf, approve_claims, approve_visa, approve_transport, approve_accommodation
   - HOD → approve_trf, approve_claims, approve_visa, approve_transport, approve_accommodation
   - Finance Clerk → approve_claims

5. ✅ ALL users should have basic permissions:
   - create_trf, create_claims, create_transport_requests, create_visa_requests, create_accommodation_requests
   - view_own_requests, manage_own_profile, view_dashboard_summary
""")
