"""
User/Role/Permission/Department management viewsets.

Split out of accounts/views.py (see
docs/CODEBASE_REFACTOR_ROADMAP.md item 1) - a pure file move, no
logic changed. Auth/MFA/settings views moved to their own sibling
modules in the same split.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

# Import standardized response utilities
from utils.api_response import (
    error_response,
    forbidden_response,
    not_found_response,
    success_response,
    validation_error_response,
)

logger = logging.getLogger(__name__)

from .models import AdminActionLog, Department, Permission, Role
from .permissions import HasManageRolesPermission
from .serializers import (
    DepartmentListSerializer,
    DepartmentSerializer,
    PermissionSerializer,
    RoleSerializer,
    UserAdminUpdateSerializer,
    UserCreateSerializer,
    UserListSerializer,
    UserProfileUpdateSerializer,
    UserSerializer,
)
from .utils import has_permission

User = get_user_model()


@extend_schema_view(
    list=extend_schema(
        tags=["Users"],
        summary="List all users",
        description="Get paginated list of all users. Supports search and ordering.",
    ),
    retrieve=extend_schema(
        tags=["Users"],
        summary="Get user details",
        description="Get details of a specific user by ID.",
    ),
    create=extend_schema(
        tags=["Users"],
        summary="Create user",
        description="Create a new user. Admin only.",
    ),
    update=extend_schema(
        tags=["Users"],
        summary="Update user",
        description="Update user details. Users can update own profile, admins can update any.",
    ),
    partial_update=extend_schema(
        tags=["Users"],
        summary="Partial update user",
        description="Partially update user details.",
    ),
    destroy=extend_schema(
        tags=["Users"], summary="Delete user", description="Delete a user. Admin only."
    ),
)
class UserViewSet(viewsets.ModelViewSet):
    """User management viewset with role-based permissions."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    # Filter backends
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    # Search across user fields (use __name for ForeignKey fields)
    search_fields = ["email", "name", "staff_id", "department__name", "phone"]

    # Allow ordering
    ordering_fields = ["email", "name", "date_joined", "department__name", "is_active"]
    ordering = ["-date_joined"]  # Default: newest first

    def get_queryset(self):
        """Apply filters for role, department, and is_active."""
        queryset = (
            super()
            .get_queryset()
            .select_related("role", "department")
            .prefetch_related("role__permissions")
        )

        # Filter by role (UUID)
        role = self.request.query_params.get("role")
        if role:
            queryset = queryset.filter(role_id=role)

        # Filter by department (UUID)
        department = self.request.query_params.get("department")
        if department:
            queryset = queryset.filter(department_id=department)

        # Filter by is_active status
        is_active = self.request.query_params.get("is_active")
        if is_active is not None and is_active != "":
            # Convert string to boolean
            is_active_bool = is_active.lower() in ("true", "1", "yes")
            queryset = queryset.filter(is_active=is_active_bool)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return UserListSerializer
        if self.action == "create":
            return UserCreateSerializer
        elif self.action in ["update", "partial_update"]:
            # Check if user is updating their own profile
            user_id = self.kwargs.get("pk")
            if user_id and str(self.request.user.id) == str(user_id):
                logger.info(f"User {self.request.user.id} updating own profile")
                return UserProfileUpdateSerializer
            logger.info(f"Admin updating user {user_id}")
            return UserAdminUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        logger.info(f"UserViewSet.get_permissions called for action: {self.action}")
        logger.info(
            f"Request user: {self.request.user}, is_authenticated: {self.request.user.is_authenticated if hasattr(self.request.user, 'is_authenticated') else 'N/A'}"
        )
        logger.info(
            f"User is_staff: {getattr(self.request.user, 'is_staff', 'N/A')}, is_superuser: {getattr(self.request.user, 'is_superuser', 'N/A')}"
        )

        if self.action == "create":
            logger.info("Returning IsAdminUser permission for create action")
            return [permissions.IsAdminUser()]
        elif self.action in ["update", "partial_update"]:
            # Users can update their own profile, admins can update any profile
            user_id = self.kwargs.get("pk")
            if user_id and str(self.request.user.id) == str(user_id):
                return [permissions.IsAuthenticated()]
            return [permissions.IsAdminUser()]
        return super().get_permissions()

    def update(self, request, *args, **kwargs):
        """Override update to add logging"""
        logger.debug(
            f"Update called by user {request.user.id} for user {kwargs.get('pk')}"
        )
        logger.debug(f"Request data: {request.data}")
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if not serializer.is_valid():
            logger.error(f"Validation errors: {serializer.errors}")
            return validation_error_response(
                serializer_errors=serializer.errors, message="Invalid user data"
            )

        self.perform_update(serializer)

        # Return full user data with role
        if getattr(instance, "_prefetched_objects_cache", None):
            instance._prefetched_objects_cache = {}

        return_serializer = UserSerializer(instance)
        return Response(return_serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """Override partial_update"""
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = serializer.save()
        AdminActionLog.log_action(
            user=self.request.user,
            action_type="user_created",
            description=f"User account created: {user.email} ({user.name})",
            entity_type="User",
            entity_id=str(user.id),
            request=self.request,
        )

    def perform_update(self, serializer):
        serializer.instance._update_request = self.request
        serializer.save()

    def perform_destroy(self, instance):
        AdminActionLog.log_action(
            user=self.request.user,
            action_type="user_deleted",
            description=f"User account deleted: {instance.email} ({instance.name})",
            entity_type="User",
            entity_id=str(instance.id),
            request=self.request,
        )
        instance._deletion_logged = True
        instance.delete()

    @action(
        detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated]
    )
    def me(self, request):
        """Get the current user's profile"""
        serializer = self.get_serializer(request.user)
        response = Response(serializer.data)
        response["Cache-Control"] = "no-store"
        return response

    @action(
        detail=False,
        methods=["patch", "put"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def update_profile(self, request):
        """Update the current user's profile"""
        if not request.user.is_superuser and not has_permission(
            request.user, "manage_own_profile"
        ):
            return forbidden_response(
                message="You do not have permission to update your profile."
            )
        serializer = UserProfileUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            # Return full user data
            user_serializer = UserSerializer(request.user)
            return success_response(
                data=user_serializer.data,
                message="Profile updated successfully",
                status_code=status.HTTP_200_OK,
            )
        return validation_error_response(
            serializer_errors=serializer.errors, message="Invalid profile data"
        )

    @action(
        detail=True, methods=["patch"], permission_classes=[permissions.IsAdminUser]
    )
    def change_role(self, request, pk=None):
        user = self.get_object()
        role_id = request.data.get("role_id")

        if not role_id:
            return error_response(
                message="Role ID is required", status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            role = Role.objects.get(id=role_id)
            user.role = role
            user.save()
        except Role.DoesNotExist:
            return not_found_response(message="Role not found")

        serializer = self.get_serializer(user)
        return success_response(
            data=serializer.data,
            message="User role updated successfully",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save()

        serializer = self.get_serializer(user)
        return success_response(
            data=serializer.data,
            message="User activated successfully",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save()

        serializer = self.get_serializer(user)
        return success_response(
            data=serializer.data,
            message="User deactivated successfully",
            status_code=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="access-review",
        permission_classes=[permissions.IsAdminUser],
    )
    def access_review(self, request, pk=None):
        """Record a completed access review for a user. CTRL-0000001018."""
        user = self.get_object()
        user.last_access_review = timezone.now()
        user.last_access_review_by = request.user
        user.save(update_fields=["last_access_review", "last_access_review_by"])
        AdminActionLog.log_action(
            user=request.user,
            action_type="access_review",
            description=f"Access review completed for user: {user.email}",
            entity_type="User",
            entity_id=str(user.id),
            request=request,
        )
        return success_response(
            data={
                "last_access_review": user.last_access_review.isoformat(),
                "reviewed_by": request.user.email,
            },
            message=f"Access review recorded for {user.email}",
            status_code=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="access-review-due",
        permission_classes=[permissions.IsAdminUser],
    )
    def access_review_due(self, request):
        """List active users overdue for access review (never reviewed or >90 days). CTRL-0000001018."""
        review_threshold = timezone.now() - timedelta(days=90)
        users = self.get_queryset().filter(
            Q(last_access_review__isnull=True)
            | Q(last_access_review__lt=review_threshold),
            is_active=True,
        )
        serializer = self.get_serializer(users, many=True)
        return success_response(
            data=serializer.data,
            message=f"{users.count()} user(s) due for access review",
            status_code=status.HTTP_200_OK,
        )


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [HasManageRolesPermission]
    pagination_class = None  # Disable pagination for roles

    # Search and ordering
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]  # Default: alphabetical


class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [HasManageRolesPermission]  # Same permission as roles
    pagination_class = None  # Disable pagination for permissions

    # Search and ordering
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]  # Default: alphabetical


@extend_schema_view(
    list=extend_schema(
        tags=["Departments"],
        summary="List all departments",
        description="Get list of all departments. Supports search and filtering.",
    ),
    retrieve=extend_schema(
        tags=["Departments"],
        summary="Get department details",
        description="Get details of a specific department by ID.",
    ),
    create=extend_schema(
        tags=["Departments"],
        summary="Create department",
        description="Create a new department. Admin only.",
    ),
    update=extend_schema(
        tags=["Departments"],
        summary="Update department",
        description="Update department details. Admin only.",
    ),
    partial_update=extend_schema(
        tags=["Departments"],
        summary="Partial update department",
        description="Partially update department details. Admin only.",
    ),
    destroy=extend_schema(
        tags=["Departments"],
        summary="Delete department",
        description="Delete a department. Admin only.",
    ),
)
class DepartmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing departments.
    Provides CRUD operations for department management.
    """

    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    pagination_class = None  # Disable pagination for departments

    # Search and ordering
    search_fields = ["name", "code", "description"]
    ordering_fields = ["name", "code", "created_at", "is_active"]
    ordering = ["name"]  # Default: alphabetical

    def get_permissions(self):
        """
        Allow listing departments for all authenticated users, but restrict modifications to admins.
        The 'active' action is public (used for registration).
        """
        if self.action == "active":
            return [permissions.AllowAny()]
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = super().get_queryset()

        # Filter by active status
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset

    def get_serializer_class(self):
        """Use lightweight serializer for list operations"""
        if self.action == "list" and self.request.query_params.get("simple") == "true":
            return DepartmentListSerializer
        return DepartmentSerializer

    def destroy(self, request, *args, **kwargs):
        """Prevent deletion of departments with users"""
        instance = self.get_object()
        user_count = instance.users.count()

        if user_count > 0:
            return error_response(
                message=f"Cannot delete department with {user_count} assigned user(s). Reassign users first.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def active(self, request):
        """
        Get only active departments (for dropdowns)
        Public endpoint - used for user registration
        """
        queryset = self.get_queryset().filter(is_active=True)
        serializer = DepartmentListSerializer(queryset, many=True)
        return Response(serializer.data)
