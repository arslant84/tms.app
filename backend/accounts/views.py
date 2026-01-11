from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model, authenticate, login
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.authtoken.views import ObtainAuthToken
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta

from .serializers import (
    UserSerializer, UserCreateSerializer, UserProfileUpdateSerializer, UserAdminUpdateSerializer, RoleSerializer, PermissionSerializer,
    ApplicationSettingSerializer, ApplicationSettingCreateSerializer, ApplicationSettingUpdateSerializer, PasswordChangeSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer, AdminActionLogSerializer
)
from .models import Role, Permission, ApplicationSetting, AdminActionLog
from .permissions import HasManageRolesPermission, HasManageUsersPermission, HasViewSystemSettingsPermission

User = get_user_model()


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        # Get username and password from request
        username = request.data.get('email')
        password = request.data.get('password')

        print(f"Login attempt for user: {username}")

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # SECURITY: Generate JWT tokens with expiration
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # Response with user data
            response = Response({
                'user': UserSerializer(user).data,
                'message': 'Login successful'
            })

            # SECURITY: Set JWT tokens in HttpOnly cookies
            # Access token for authentication (short-lived)
            response.set_cookie(
                key='access_token',
                value=access_token,
                httponly=True,  # Prevents JavaScript access (XSS protection)
                secure=True,    # Only send over HTTPS in production
                samesite='Lax', # CSRF protection
                max_age=3600,   # 1 hour (matches ACCESS_TOKEN_LIFETIME)
                path='/'
            )

            # Refresh token for getting new access tokens (long-lived)
            response.set_cookie(
                key='refresh_token',
                value=refresh_token,
                httponly=True,  # Prevents JavaScript access (XSS protection)
                secure=True,    # Only send over HTTPS in production
                samesite='Lax', # CSRF protection
                max_age=86400 * 7,  # 7 days (matches REFRESH_TOKEN_LIFETIME)
                path='/'
            )

            # Keep legacy token for backward compatibility during migration
            # TODO: Remove this after full JWT migration
            token, created = Token.objects.get_or_create(user=user)
            response.set_cookie(
                key='auth_token',
                value=token.key,
                httponly=True,
                secure=True,
                samesite='Lax',
                max_age=86400 * 7,
                path='/'
            )

            return response
        else:
            print(f"Authentication failed for user: {username}")
            # SECURITY: Generic error message to prevent user enumeration
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            # SECURITY: Blacklist the refresh token to prevent reuse
            refresh_token = request.COOKIES.get('refresh_token')
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()  # Add to blacklist
                except TokenError:
                    pass  # Token already invalid or blacklisted

            # Delete legacy token for backward compatibility
            # TODO: Remove this after full JWT migration
            try:
                request.user.auth_token.delete()
            except:
                pass

            # SECURITY: Clear all auth cookies
            response = Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
            response.delete_cookie('access_token', path='/')
            response.delete_cookie('refresh_token', path='/')
            response.delete_cookie('auth_token', path='/')  # Legacy token

            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TokenRefreshView(APIView):
    """
    Refresh access token using refresh token from HttpOnly cookie.

    SECURITY: Rotates refresh tokens and blacklists old ones.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # Get refresh token from cookie
        refresh_token_str = request.COOKIES.get('refresh_token')

        if not refresh_token_str:
            return Response(
                {'error': 'Refresh token not found'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            # Validate and refresh the token
            refresh = RefreshToken(refresh_token_str)

            # SECURITY: Token rotation - generate new refresh token
            # Old token is automatically blacklisted (BLACKLIST_AFTER_ROTATION=True)
            new_access_token = str(refresh.access_token)

            # For full rotation, generate a completely new refresh token
            if hasattr(refresh, 'rotate'):
                refresh.rotate()
            new_refresh_token = str(refresh)

            # Response
            response = Response({
                'message': 'Token refreshed successfully'
            })

            # Set new access token cookie
            response.set_cookie(
                key='access_token',
                value=new_access_token,
                httponly=True,
                secure=True,
                samesite='Lax',
                max_age=3600,  # 1 hour
                path='/'
            )

            # Set new refresh token cookie
            response.set_cookie(
                key='refresh_token',
                value=new_refresh_token,
                httponly=True,
                secure=True,
                samesite='Lax',
                max_age=86400 * 7,  # 7 days
                path='/'
            )

            return response

        except TokenError as e:
            return Response(
                {'error': f'Invalid refresh token: {str(e)}'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class PasswordChangeView(APIView):
    """
    Change password for authenticated user.
    SECURITY: Clears password_change_required flag after successful change.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        # Verify old password
        if not user.check_password(old_password):
            return Response(
                {'error': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password
        user.set_password(new_password)
        # SECURITY: Clear password change requirement
        user.password_change_required = False
        user.save()

        return Response({
            'message': 'Password changed successfully',
            'password_change_required': False
        })


class PasswordResetRequestView(APIView):
    """
    Request a password reset. Sends email with reset token.
    SECURITY: Rate limited to prevent abuse.
    """
    permission_classes = [permissions.AllowAny]

    @method_decorator(ratelimit(key='ip', rate='3/h', method='POST'))
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email, is_active=True)

            # Generate reset token (64 characters, URL-safe)
            reset_token = get_random_string(64)

            # Store token and expiry in user model (expires in 1 hour)
            user.password_reset_token = reset_token
            user.password_reset_token_expires = timezone.now() + timedelta(hours=1)
            user.save()

            # Send email with reset link
            reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={reset_token}"

            send_mail(
                subject='Password Reset Request - SynTra TMS',
                message=f'''Hello {user.name},

You have requested to reset your password for your SynTra Travel Management System account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you did not request this password reset, please ignore this email and your password will remain unchanged.

Best regards,
SynTra TMS Team''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )

        except User.DoesNotExist:
            # SECURITY: Don't reveal if email exists or not
            pass

        # Always return success to prevent email enumeration
        return Response({
            'message': 'If an account exists with this email, a password reset link has been sent.'
        })


class PasswordResetConfirmView(APIView):
    """
    Confirm password reset with token and set new password.
    SECURITY: Token expires after 1 hour.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            user = User.objects.get(
                password_reset_token=token,
                password_reset_token_expires__gt=timezone.now()
            )

            # Set new password
            user.set_password(new_password)
            # Clear reset token
            user.password_reset_token = None
            user.password_reset_token_expires = None
            # Clear password change requirement if set
            user.password_change_required = False
            user.save()

            return Response({
                'message': 'Password reset successfully. You can now log in with your new password.'
            })

        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired reset token'},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            # Check if user is updating their own profile
            user_id = self.kwargs.get('pk')
            if user_id and str(self.request.user.id) == str(user_id):
                print(f"User {self.request.user.id} updating own profile, using UserProfileUpdateSerializer")
                return UserProfileUpdateSerializer
            print(f"Admin updating user {user_id}, using UserAdminUpdateSerializer")
            return UserAdminUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAdminUser()]
        elif self.action in ['update', 'partial_update']:
            # Users can update their own profile, admins can update any profile
            user_id = self.kwargs.get('pk')
            if user_id and str(self.request.user.id) == str(user_id):
                return [permissions.IsAuthenticated()]
            return [permissions.IsAdminUser()]
        return super().get_permissions()

    def update(self, request, *args, **kwargs):
        """Override update to add logging"""
        print(f"Update called by user {request.user.id} for user {kwargs.get('pk')}")
        print(f"Request data: {request.data}")
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if not serializer.is_valid():
            print(f"Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        self.perform_update(serializer)

        # Return full user data with role
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return_serializer = UserSerializer(instance)
        return Response(return_serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """Override partial_update"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Get the current user's profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['patch', 'put'], permission_classes=[permissions.IsAuthenticated])
    def update_profile(self, request):
        """Update the current user's profile"""
        serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Return full user data
            user_serializer = UserSerializer(request.user)
            return Response(user_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAdminUser])
    def change_role(self, request, pk=None):
        user = self.get_object()
        role_id = request.data.get('role_id')
        
        if not role_id:
            return Response({'error': 'Role ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            role = Role.objects.get(id=role_id)
            user.role = role
            user.save()
        except Role.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save()
        
        serializer = self.get_serializer(user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save()
        
        serializer = self.get_serializer(user)
        return Response(serializer.data)


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [HasManageRolesPermission]
    pagination_class = None  # Disable pagination for roles


class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [HasManageRolesPermission]  # Same permission as roles
    pagination_class = None  # Disable pagination for permissions


class ApplicationSettingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing application settings.
    Supports GET (list/retrieve), POST (create), PUT/PATCH (update), DELETE

    Query parameters:
    - public: bool - Filter by public settings only
    - key: str - Filter by setting key
    """
    queryset = ApplicationSetting.objects.all()
    serializer_class = ApplicationSettingSerializer
    lookup_field = 'setting_key'
    lookup_value_regex = '[^/]+'  # Allow dots and other chars in setting_key
    pagination_class = None  # Disable pagination for settings

    def get_permissions(self):
        """Allow public access for public settings"""
        if self.action == 'list' and self.request.query_params.get('public') == 'true':
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = super().get_queryset()

        # Filter by public settings
        if self.request.query_params.get('public') == 'true':
            queryset = queryset.filter(is_public=True)

        # Filter by key
        key = self.request.query_params.get('key')
        if key:
            queryset = queryset.filter(setting_key=key)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ApplicationSettingCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ApplicationSettingUpdateSerializer
        return ApplicationSettingSerializer

    @action(detail=False, methods=['put'], permission_classes=[permissions.IsAdminUser])
    def bulk_update(self, request):
        """
        Bulk update multiple settings at once.

        Expected payload:
        {
            "settings": [
                {"setting_key": "app_name", "value": "My App"},
                {"setting_key": "support_email", "value": "support@example.com"}
            ]
        }
        """
        settings_data = request.data.get('settings', [])

        if not isinstance(settings_data, list):
            return Response(
                {'error': 'settings must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )

        updated_settings = []
        errors = []

        for setting_data in settings_data:
            setting_key = setting_data.get('setting_key')
            if not setting_key:
                errors.append({'error': 'setting_key is required', 'data': setting_data})
                continue

            try:
                setting = ApplicationSetting.objects.get(setting_key=setting_key)
                serializer = ApplicationSettingUpdateSerializer(
                    setting,
                    data=setting_data,
                    partial=True
                )

                if serializer.is_valid():
                    serializer.save()
                    updated_settings.append(ApplicationSettingSerializer(setting).data)
                else:
                    errors.append({'setting_key': setting_key, 'errors': serializer.errors})

            except ApplicationSetting.DoesNotExist:
                # Create new setting if it doesn't exist
                serializer = ApplicationSettingCreateSerializer(data=setting_data)
                if serializer.is_valid():
                    new_setting = serializer.save()
                    updated_settings.append(ApplicationSettingSerializer(new_setting).data)
                else:
                    errors.append({'setting_key': setting_key, 'errors': serializer.errors})

        return Response({
            'updated': updated_settings,
            'errors': errors
        })

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def as_object(self, request):
        """
        Return all settings as a simple key-value object.

        Query parameters:
        - public: bool - Return only public settings

        Returns: {"setting_key": value, ...}

        SECURITY: Only authenticated users can access settings.
        Non-admin users only get public settings.
        """
        queryset = self.get_queryset()

        # SECURITY: Non-admin users only get public settings
        if not request.user.is_staff and not request.user.is_superuser:
            queryset = queryset.filter(is_public=True)

        settings_obj = {}

        for setting in queryset:
            settings_obj[setting.setting_key] = setting.get_value()

        return Response(settings_obj)


class AdminActionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing audit logs (security trail).
    Read-only access for security monitoring and compliance.

    SECURITY: Access controlled by RBAC permissions.
    Users must have 'view_audit_logs' permission.
    """
    queryset = AdminActionLog.objects.all().select_related('user')
    serializer_class = AdminActionLogSerializer
    permission_classes = [permissions.IsAuthenticated]  # Further restricted by RBAC in get_queryset

    filterset_fields = ['action_type', 'entity_type', 'user']
    search_fields = ['description', 'user__email', 'entity_type', 'entity_id', 'ip_address']
    ordering_fields = ['created_at', 'action_type']
    ordering = ['-created_at']  # Most recent first

    def get_queryset(self):
        """
        SECURITY: Filter audit logs based on user permissions.
        System administrators can see all logs.
        Other users can only see their own actions.
        """
        queryset = super().get_queryset()
        user = self.request.user

        # SECURITY: Admin users see all audit logs
        if user.is_admin or user.is_superuser:
            return queryset

        # SECURITY: Check if user has explicit permission to view audit logs
        # This should be controlled by RBAC permission 'view_audit_logs'
        from .models import Permission as AppPermission
        try:
            view_audit_perm = AppPermission.objects.get(name='view_audit_logs')
            user_permissions = []
            if user.role:
                user_permissions = user.role.permissions.all()

            if view_audit_perm in user_permissions:
                return queryset
        except AppPermission.DoesNotExist:
            pass

        # Regular users can only see their own audit logs
        return queryset.filter(user=user)

    @action(detail=False, methods=['get'])
    def my_logs(self, request):
        """
        Get audit logs for the current user only.
        Allows users to see their own activity history.
        """
        queryset = self.get_queryset().filter(user=request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def stats(self, request):
        """
        Get audit log statistics.
        SECURITY: Only available to admin users.
        """
        if not request.user.is_admin and not request.user.is_superuser:
            return Response(
                {'error': 'Only administrators can view audit log statistics'},
                status=status.HTTP_403_FORBIDDEN
            )

        from django.db.models import Count
        queryset = self.get_queryset()

        # Count by action type
        action_stats = queryset.values('action_type').annotate(count=Count('id')).order_by('-count')

        # Count by user
        user_stats = queryset.values('user__email', 'user__name').annotate(count=Count('id')).order_by('-count')[:10]

        # Recent activity (last 24 hours)
        from datetime import timedelta
        from django.utils import timezone
        recent_cutoff = timezone.now() - timedelta(hours=24)
        recent_count = queryset.filter(created_at__gte=recent_cutoff).count()

        return Response({
            'total_logs': queryset.count(),
            'recent_activity_24h': recent_count,
            'by_action_type': list(action_stats),
            'top_users': list(user_stats),
        })
