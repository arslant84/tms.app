from rest_framework import permissions
from .utils import has_permission


class HasManageRolesPermission(permissions.BasePermission):
    """
    Custom permission to check if user has manage_roles permission.
    Allows superusers or users with the specific permission.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Allow superusers
        if request.user.is_superuser:
            return True

        # Check if user has the manage_roles permission
        return has_permission(request.user, 'manage_roles')


class HasManageUsersPermission(permissions.BasePermission):
    """
    Custom permission to check if user has manage_users permission.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Allow superusers
        if request.user.is_superuser:
            return True

        # Check if user has the manage_users permission
        return has_permission(request.user, 'manage_users')


class HasViewSystemSettingsPermission(permissions.BasePermission):
    """
    Custom permission to check if user has view_system_settings permission.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Allow superusers
        if request.user.is_superuser:
            return True

        # For read-only operations, check view permission
        if request.method in permissions.SAFE_METHODS:
            return has_permission(request.user, 'view_system_settings')

        # For write operations, check manage permission
        return has_permission(request.user, 'manage_application_settings')
