#!/usr/bin/env python
"""
Convert existing workflow steps from role-based (UUID) to permission-based assignment.

This script maps role UUIDs to appropriate permissions and updates WorkflowStep records.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tms_project.settings')
django.setup()

from workflows.models import WorkflowStep
from accounts.models import Permission, Role

print("="*80)
print("CONVERTING WORKFLOWS TO PERMISSION-BASED ASSIGNMENT (V2)")
print("="*80)

# Entity-specific permission mapping (by role name)
ENTITY_PERMISSION_MAP = {
    'travelrequest': {  # TRF entity type
        'Department Focal': 'approve_trf',
        'Line Manager': 'approve_trf',
        'HOD': 'approve_trf',
        'Ticketing Admin': 'view_all_trf',  # For processing
        'CEO': 'approve_high_value',
    },
    'trf': {  # Alias for travelrequest
        'Department Focal': 'approve_trf',
        'Line Manager': 'approve_trf',
        'HOD': 'approve_trf',
        'Ticketing Admin': 'view_all_trf',
        'CEO': 'approve_high_value',
    },
    'transportrequest': {
        'Department Focal': 'approve_transport',
        'Line Manager': 'approve_transport',
        'HOD': 'approve_transport',
        'Transport Admin': 'view_all_transport',  # For processing
    },
    'visaapplication': {
        'Department Focal': 'approve_visa',
        'Line Manager': 'approve_visa',
        'HOD': 'approve_visa',
        'Visa Clerk': 'view_all_visa',  # For processing
    },
    'accommodation': {  # Accommodation entity type
        'Department Focal': 'approve_accommodation',
        'Line Manager': 'approve_accommodation',
        'HOD': 'approve_accommodation',
        'Accommodation Admin': 'view_all_accommodation',  # For processing
    },
    'accommodationrequest': {  # Alias
        'Department Focal': 'approve_accommodation',
        'Line Manager': 'approve_accommodation',
        'HOD': 'approve_accommodation',
        'Accommodation Admin': 'view_all_accommodation',
    },
    'expenseclaim': {
        'Department Focal': 'approve_claims',
        'Line Manager': 'approve_claims',
        'HOD': 'approve_claims',
        'Finance Clerk': 'view_all_claims',  # For processing
    },
}

# Get all workflow steps that have approver_role but no approver_permission
steps_to_update = WorkflowStep.objects.filter(
    approver_role__isnull=False
).exclude(approver_role='')

print(f"\nFound {steps_to_update.count()} workflow steps with role-based assignment")
print()

updated_count = 0
skipped_count = 0

for step in steps_to_update:
    print(f"Step: {step.workflow_template.name} - {step.step_name}")
    print(f"  Template entity: {step.workflow_template.entity_type}")
    print(f"  Current: approver_role = '{step.approver_role}'")

    # Skip if already has permission set
    if step.approver_permission:
        print(f"  ✅ Already has approver_permission = '{step.approver_permission}'")
        skipped_count += 1
        continue

    # Try to get the role by UUID
    try:
        role = Role.objects.get(id=step.approver_role)
        role_name = role.name
        print(f"  Found role: '{role_name}'")
    except (Role.DoesNotExist, ValueError):
        print(f"  ⚠️  Role with ID '{step.approver_role}' not found - skipping")
        skipped_count += 1
        continue

    # Determine the appropriate permission based on entity type and role
    entity_type = step.workflow_template.entity_type
    permission_name = None

    # Try entity-specific mapping
    if entity_type in ENTITY_PERMISSION_MAP:
        permission_name = ENTITY_PERMISSION_MAP[entity_type].get(role_name)

    if permission_name:
        # Verify permission exists
        try:
            permission = Permission.objects.get(name=permission_name)
            step.approver_permission = permission_name
            step.save()
            print(f"  ✅ Updated: approver_permission = '{permission_name}'")
            updated_count += 1
        except Permission.DoesNotExist:
            print(f"  ⚠️  Permission '{permission_name}' not found")
            print(f"     Creating permission '{permission_name}'...")

            # Create the missing permission
            permission = Permission.objects.create(
                name=permission_name,
                description=f"Permission to {permission_name.replace('_', ' ')}"
            )
            print(f"     ✅ Created permission '{permission_name}'")

            # Assign to the role
            role.permissions.add(permission)
            print(f"     ✅ Assigned to role '{role_name}'")

            # Update the step
            step.approver_permission = permission_name
            step.save()
            print(f"  ✅ Updated: approver_permission = '{permission_name}'")
            updated_count += 1
    else:
        print(f"  ⚠️  No permission mapping found for role '{role_name}' in entity '{entity_type}'")
        print(f"     Consider adding a mapping or manually updating this step")
        skipped_count += 1

    print()

print("="*80)
print("SUMMARY")
print("="*80)
print(f"Total steps processed: {steps_to_update.count()}")
print(f"✅ Updated: {updated_count}")
print(f"⚠️  Skipped: {skipped_count}")
print()

if skipped_count > 0:
    print("⚠️  Some steps were skipped. You may need to manually update them.")
    print("   Review the output above and update the permission mapping if needed.")

print()
print("="*80)
print("NEXT STEPS")
print("="*80)
print("""
1. Review the updated workflow steps in Django Admin:
   http://localhost:8000/admin/workflows/workflowstep/

2. Verify that permissions are correctly assigned to roles:
   python backend/check_view_permissions.py

3. Test workflow assignment with different user roles

4. For any skipped steps, manually update them in Django Admin or update the mapping

To view updated workflow steps:
  python manage.py shell
  >>> from workflows.models import WorkflowStep
  >>> for step in WorkflowStep.objects.all():
  ...     print(f"{step.step_name}: permission={step.approver_permission}, role={step.approver_role}")
""")
