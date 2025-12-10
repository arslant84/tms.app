from rest_framework import permissions


class HasManageRolesPermission(permissions.BasePermission):
    """
    Custom permission to check if user has manage_roles permission.
    Allows superusers and staff, or users with the specific permission.
    """
    def has_permission(self, request, view):
        # Allow superusers and staff
        if request.user and (request.user.is_superuser or request.user.is_staff):
            return True

        # Check if user has the manage_roles permission
        if request.user and hasattr(request.user, 'role') and request.user.role:
            return request.user.role.permissions.filter(name='manage_roles').exists()

        return False


class HasManageUsersPermission(permissions.BasePermission):
    """
    Custom permission to check if user has manage_users permission.
    """
    def has_permission(self, request, view):
        # Allow superusers and staff
        if request.user and (request.user.is_superuser or request.user.is_staff):
            return True

        # Check if user has the manage_users permission
        if request.user and hasattr(request.user, 'role') and request.user.role:
            return request.user.role.permissions.filter(name='manage_users').exists()

        return False


class HasViewSystemSettingsPermission(permissions.BasePermission):
    """
    Custom permission to check if user has view_system_settings permission.
    """
    def has_permission(self, request, view):
        # Allow superusers and staff
        if request.user and (request.user.is_superuser or request.user.is_staff):
            return True

        # For read-only operations, check view permission
        if request.method in permissions.SAFE_METHODS:
            if request.user and hasattr(request.user, 'role') and request.user.role:
                return request.user.role.permissions.filter(name='view_system_settings').exists()

        # For write operations, check manage permission
        if request.user and hasattr(request.user, 'role') and request.user.role:
            return request.user.role.permissions.filter(name='manage_application_settings').exists()

        return False
