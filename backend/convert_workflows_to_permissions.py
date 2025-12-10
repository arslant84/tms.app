#!/usr/bin/env python
"""
Convert existing workflow steps from role-based to permission-based assignment.

This script maps role names to appropriate permissions and updates WorkflowStep records.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tms_project.settings')
django.setup()

from workflows.models import WorkflowStep
from accounts.models import Permission

print("="*80)
print("CONVERTING WORKFLOWS TO PERMISSION-BASED ASSIGNMENT")
print("="*80)

# Mapping of role names to permission names
# This ensures each workflow step uses the appropriate permission
ROLE_TO_PERMISSION_MAP = {
    # Approval permissions (department-level)
    'Department Focal': 'approve_trf',  # or approve_transport, etc. based on context
    'Line Manager': 'approve_trf',
    'HOD': 'approve_trf',

    # Processing permissions (org-wide)
    'Transport Admin': 'process_transport',  # or approve_transport if approval step
    'Ticketing Admin': 'process_flights',  # or approve_trf if approval step
    'Visa Clerk': 'process_visa',
    'Accommodation Admin': 'process_accommodation',
    'Finance Clerk': 'process_claims',

    # Executive approvals
    'CEO': 'approve_high_value',
    'CFO': 'approve_high_value',
}

# Entity-specific permission mapping
ENTITY_PERMISSION_MAP = {
    'trf': {
        'Department Focal': 'approve_trf',
        'Line Manager': 'approve_trf',
        'HOD': 'approve_trf',
        'Ticketing Admin': 'process_flights',
        'CEO': 'approve_high_value',
    },
    'transportrequest': {
        'Department Focal': 'approve_transport',
        'Line Manager': 'approve_transport',
        'HOD': 'approve_transport',
        'Transport Admin': 'process_transport',
    },
    'visaapplication': {
        'Department Focal': 'approve_visa',
        'Line Manager': 'approve_visa',
        'HOD': 'approve_visa',
        'Visa Clerk': 'process_visa',
    },
    'accommodationrequest': {
        'Department Focal': 'approve_accommodation',
        'Line Manager': 'approve_accommodation',
        'HOD': 'approve_accommodation',
        'Accommodation Admin': 'process_accommodation',
    },
    'expenseclaim': {
        'Department Focal': 'approve_claims',
        'Line Manager': 'approve_claims',
        'HOD': 'approve_claims',
        'Finance Clerk': 'process_claims',
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
    print(f"  Current: approver_role = '{step.approver_role}'")

    # Skip if already has permission set
    if step.approver_permission:
        print(f"  ✅ Already has approver_permission = '{step.approver_permission}'")
        skipped_count += 1
        continue

    # Determine the appropriate permission based on entity type and role
    entity_type = step.workflow_template.entity_type
    role_name = step.approver_role

    permission_name = None

    # Try entity-specific mapping first
    if entity_type in ENTITY_PERMISSION_MAP:
        permission_name = ENTITY_PERMISSION_MAP[entity_type].get(role_name)

    # Fallback to general mapping
    if not permission_name:
        permission_name = ROLE_TO_PERMISSION_MAP.get(role_name)

    if permission_name:
        # Verify permission exists
        try:
            permission = Permission.objects.get(name=permission_name)
            step.approver_permission = permission_name
            step.save()
            print(f"  ✅ Updated: approver_permission = '{permission_name}'")
            updated_count += 1
        except Permission.DoesNotExist:
            print(f"  ⚠️  Permission '{permission_name}' not found - skipping")
            skipped_count += 1
    else:
        print(f"  ⚠️  No permission mapping found for role '{role_name}' - skipping")
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
    print("   Run this script after ensuring all required permissions exist.")

print()
print("="*80)
print("NEXT STEPS")
print("="*80)
print("""
1. Review the updated workflow steps in Django Admin
2. Verify that permissions are correctly assigned to roles
3. Test workflow assignment with different user roles
4. Update any custom workflow steps manually if needed

To view workflow steps:
  python manage.py shell
  >>> from workflows.models import WorkflowStep
  >>> for step in WorkflowStep.objects.all():
  ...     print(f"{step.step_name}: permission={step.approver_permission}, role={step.approver_role}")
""")
