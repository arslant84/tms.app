"""
Permission utility functions for role-based access control.

These functions replace hardcoded is_staff checks with role-based permission checks.
All access control should be determined by permissions assigned to user roles in the database.
"""


def has_permission(user, permission_name):
    """
    Check if user has a specific permission via their role.

    Args:
        user: The user object to check
        permission_name: The name of the permission to check for

    Returns:
        True if user has the permission, False otherwise.
    """
    if not user or not user.is_authenticated:
        return False
    if not user.role:
        return False
    return user.role.permissions.filter(name=permission_name).exists()


def has_any_permission(user, permission_names):
    """
    Check if user has any of the specified permissions.

    Args:
        user: The user object to check
        permission_names: List of permission names to check

    Returns:
        True if user has at least one of the permissions, False otherwise.
    """
    if not user or not user.is_authenticated:
        return False
    if not user.role:
        return False
    return user.role.permissions.filter(name__in=permission_names).exists()


def can_view_all(user, module):
    """
    Check if user can view all records for a specific module.

    Args:
        user: The user object to check
        module: Module name - 'trf', 'accommodation', 'transport', 'visa', 'booking', 'flights'

    Returns:
        True if user can view all records for the module, False otherwise.
    """
    permission_map = {
        "trf": "view_all_trf",
        "accommodation": "view_all_accommodation",
        "transport": "view_all_transport",
        "visa": "view_all_visa",
        "booking": "view_all_bookings",
        "bookings": "view_all_bookings",
        "flights": "view_all_trf",  # Flights are tied to TRF admin
    }
    permission_name = permission_map.get(module)
    if not permission_name:
        return False
    return has_permission(user, permission_name)


def can_manage(user, module):
    """
    Check if user can manage (create/update/process) records for a module.

    Args:
        user: The user object to check
        module: Module name

    Returns:
        True if user can manage records for the module, False otherwise.
    """
    permission_map = {
        "trf": ["process_trf", "manage_trf"],
        "accommodation": ["process_accommodation", "manage_accommodation"],
        "transport": ["process_transport", "manage_transport"],
        "visa": ["process_visa", "manage_visa"],
        "booking": ["process_bookings", "manage_bookings"],
        "bookings": ["process_bookings", "manage_bookings"],
        "workflow": ["manage_workflows"],
        "workflows": ["manage_workflows"],
        "user": ["manage_users"],
        "users": ["manage_users"],
        "role": ["manage_roles"],
        "roles": ["manage_roles"],
        "department": ["manage_departments"],
        "departments": ["manage_departments"],
        "notification": ["manage_notifications", "send_notifications"],
        "notifications": ["manage_notifications", "send_notifications"],
        "approval": ["manage_approvals"],
        "approvals": ["manage_approvals"],
    }
    permissions = permission_map.get(module, [])
    if not permissions:
        return False
    return has_any_permission(user, permissions)


def is_module_admin(user, module):
    """
    Check if user is an admin for a specific module.
    This replaces is_staff checks for module-specific admin actions.

    A user is considered a module admin if they can view all records
    OR can manage records for that module.

    Args:
        user: The user object to check
        module: Module name

    Returns:
        True if user is an admin for the module, False otherwise.
    """
    return can_view_all(user, module) or can_manage(user, module)


def can_approve(user, module=None):
    """
    Check if user has approval permissions.

    Args:
        user: The user object to check
        module: Optional - specific module to check approval for

    Returns:
        True if user can approve requests, False otherwise.
    """
    if module:
        permission_map = {
            "trf": "approve_trf",
            "accommodation": "approve_accommodation",
            "transport": "approve_transport",
            "visa": "approve_visa",
            "combined": "approve_combined",
        }
        permission_name = permission_map.get(module)
        if permission_name:
            return has_permission(user, permission_name)
        return False

    # Check if user has any approval permission
    approval_permissions = [
        "approve_trf",
        "approve_accommodation",
        "approve_transport",
        "approve_visa",
        "approve_combined",
        "view_pending_approvals",
    ]
    return has_any_permission(user, approval_permissions)
