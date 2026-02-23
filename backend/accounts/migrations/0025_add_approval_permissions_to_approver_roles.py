# Migration to add approval permissions to roles used as approver_role in workflow steps
# This fixes the issue where approvers can approve (via workflow) but can't view the approvals page (missing permissions)

from django.db import migrations


def add_approval_permissions_to_approver_roles(apps, schema_editor):
    """
    Find all roles that are used as approver_role in workflow steps
    and ensure they have the corresponding approval permissions.

    This fixes the mismatch between:
    - Workflow-based authorization (allows approval based on role matching approver_role)
    - Permission-based authorization (frontend route guard requires approve_* permissions)
    """
    Permission = apps.get_model('accounts', 'Permission')
    Role = apps.get_model('accounts', 'Role')
    RolePermission = apps.get_model('accounts', 'RolePermission')
    WorkflowStep = apps.get_model('workflows', 'WorkflowStep')

    # Approval permissions that should be assigned to approver roles
    APPROVAL_PERMISSIONS = [
        'approve_trf',
        'approve_accommodation',
        'approve_transport',
        'approve_visa',
        'view_pending_approvals',
    ]

    # Get all permission objects
    approval_permission_objs = Permission.objects.filter(name__in=APPROVAL_PERMISSIONS)
    if not approval_permission_objs.exists():
        print("  No approval permissions found in database - skipping")
        return

    # Find all unique approver_role values from workflow steps
    approver_roles = WorkflowStep.objects.exclude(
        approver_role__isnull=True
    ).exclude(
        approver_role=''
    ).values_list('approver_role', flat=True).distinct()

    if not approver_roles:
        print("  No workflow steps with approver_role found - skipping")
        return

    roles_updated = 0
    permissions_added = 0

    for approver_role_value in approver_roles:
        if not approver_role_value:
            continue

        # Try to find the role by UUID first, then by name
        role = None
        try:
            import uuid
            uuid.UUID(approver_role_value)  # Validate it's a UUID
            role = Role.objects.filter(id=approver_role_value).first()
        except (ValueError, TypeError):
            pass

        if not role:
            # Try by name
            role = Role.objects.filter(name=approver_role_value).first()

        if not role:
            print(f"  Warning: Could not find role for approver_role value: {approver_role_value}")
            continue

        # Add missing approval permissions to this role
        role_updated = False
        for permission in approval_permission_objs:
            # Check if this role-permission combination already exists
            exists = RolePermission.objects.filter(
                role=role,
                permission=permission
            ).exists()

            if not exists:
                RolePermission.objects.create(
                    role=role,
                    permission=permission
                )
                print(f"  Added permission '{permission.name}' to role '{role.name}'")
                permissions_added += 1
                role_updated = True

        if role_updated:
            roles_updated += 1

    print(f"\n  Summary: Updated {roles_updated} role(s), added {permissions_added} permission(s)")


def reverse_migration(apps, schema_editor):
    """
    Don't remove permissions in reverse - they may be intentionally kept
    """
    print("Note: Permissions are not removed in reverse migration (may be in use)")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0024_assign_rbac_permissions_to_admins'),
        ('workflows', '0008_fix_uuid_primary_key'),  # Ensure workflow models exist with latest schema
    ]

    operations = [
        migrations.RunPython(add_approval_permissions_to_approver_roles, reverse_migration),
    ]
