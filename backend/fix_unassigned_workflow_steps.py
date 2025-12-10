#!/usr/bin/env python
"""
Fix all unassigned workflow steps by assigning them to users with appropriate permissions.

This script finds all workflow steps that have no assigned_to user and assigns them
using the permission-based workflow engine logic.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tms_project.settings')
django.setup()

from workflows.models import WorkflowStepExecution, WorkflowInstance
from workflows.engine import WorkflowEngine

print("=" * 80)
print("FIXING UNASSIGNED WORKFLOW STEPS")
print("=" * 80)

# Find all workflow step executions that don't have an assigned user
unassigned_steps = WorkflowStepExecution.objects.filter(assigned_to__isnull=True, status='pending')

print(f"\nFound {unassigned_steps.count()} unassigned pending steps")
print()

fixed_count = 0
failed_count = 0

for step in unassigned_steps:
    workflow = step.workflow_instance
    permission = step.workflow_step.approver_permission

    print(f"Step: {step.workflow_step.step_name} (Workflow #{workflow.id})")
    print(f"  Entity: {workflow.content_type.model} #{workflow.object_id}")
    print(f"  Permission Required: {permission}")
    print(f"  Department: {workflow.initiated_by.department}")

    if permission:
        # Use the workflow engine's permission-based finder
        user = WorkflowEngine._find_user_by_permission(
            permission,
            workflow.initiated_by.department
        )

        if user:
            step.assigned_to = user
            step.save()
            print(f"  ✅ Assigned to: {user.email}")
            fixed_count += 1

            # Send notification to the newly assigned user
            from workflows.notifications import WorkflowNotifications
            WorkflowNotifications.notify_approval_required(step)
            print(f"  📧 Notification sent")
        else:
            print(f"  ❌ No user found with permission '{permission}' in department '{workflow.initiated_by.department}'")
            failed_count += 1
    else:
        print(f"  ⚠️  No permission configured for this step")
        failed_count += 1

    print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total unassigned steps: {unassigned_steps.count()}")
print(f"✅ Successfully assigned: {fixed_count}")
print(f"❌ Failed to assign: {failed_count}")
print()

if fixed_count > 0:
    print("✅ Workflow steps have been assigned and notifications sent!")
    print("   Users should now receive proper workflow notifications.")

if failed_count > 0:
    print(f"\n⚠️  {failed_count} steps could not be assigned.")
    print("   This means no active users were found with the required permissions in those departments.")
    print("   You may need to:")
    print("   1. Create users with the required roles/permissions")
    print("   2. Update the workflow templates to use different permissions")
    print("   3. Manually assign users to these steps in Django Admin")
