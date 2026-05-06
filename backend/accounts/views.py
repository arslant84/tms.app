from rest_framework import viewsets, permissions, status, generics, filters
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
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
import logging
import pyotp
from django.db.models import Q
from django.core import signing
from django.core.signing import SignatureExpired, BadSignature

# Import standardized response utilities
from utils.api_response import (
    success_response, error_response, validation_error_response,
    paginated_response, created_response, unauthorized_response,
    forbidden_response, not_found_response, get_pagination_params
)

logger = logging.getLogger(__name__)

from .serializers import (
    UserSerializer, UserCreateSerializer, UserProfileUpdateSerializer, UserAdminUpdateSerializer, RoleSerializer, PermissionSerializer,
    ApplicationSettingSerializer, ApplicationSettingCreateSerializer, ApplicationSettingUpdateSerializer, PasswordChangeSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer, AdminActionLogSerializer,
    DepartmentSerializer, DepartmentListSerializer, UserRegistrationSerializer,
    MFAStatusSerializer, MFAConfirmSerializer, MFAVerifySerializer, MFADisableSerializer,
    PrivacyPolicySerializer,
)
from .utils import has_permission
from .models import Role, Permission, ApplicationSetting, AdminActionLog, Department
from .permissions import HasManageRolesPermission, HasManageUsersPermission, HasViewSystemSettingsPermission

User = get_user_model()


class LoginView(APIView):
    """User authentication endpoint."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Authentication'],
        summary='User Login',
        description='Authenticate user with email and password. Returns user data and sets HttpOnly JWT cookies.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'email': {'type': 'string', 'format': 'email'},
                    'password': {'type': 'string', 'format': 'password'}
                },
                'required': ['email', 'password']
            }
        },
        responses={
            200: UserSerializer,
            401: OpenApiTypes.OBJECT,
            429: OpenApiTypes.OBJECT
        }
    )
    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        # Get username and password from request
        username = request.data.get('email')
        password = request.data.get('password')

        logger.info(f"Login attempt for user: {username}")

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # MFA gate — if MFA is enabled, return a short-lived challenge
            # token instead of issuing JWT cookies (CTRL-0000001024/1063).
            if user.mfa_enabled:
                challenge_token = signing.dumps(
                    {'user_id': str(user.id)},
                    salt='mfa-login-challenge',
                )
                AdminActionLog.log_action(
                    user=user,
                    action_type='login_success',
                    description=f"MFA challenge issued for: {user.email}",
                    entity_type='User',
                    entity_id=str(user.id),
                    request=request
                )
                return success_response(
                    data={'mfa_required': True, 'challenge_token': challenge_token},
                    message='MFA verification required',
                    status_code=status.HTTP_200_OK
                )

            # SECURITY: Log successful login for audit trail
            AdminActionLog.log_action(
                user=user,
                action_type='login_success',
                description=f"User logged in successfully: {user.email}",
                entity_type='User',
                entity_id=str(user.id),
                request=request
            )

            # SECURITY: Generate JWT tokens with expiration
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # CTRL-0000001025 / CTRL-0000001061: privileged passwords expire after 30 days.
            is_privileged = user.is_admin or user.is_staff or user.is_superuser
            if is_privileged and user.password_last_changed:
                age_days = (timezone.now() - user.password_last_changed).days
                if age_days >= 30 and not user.password_change_required:
                    user.password_change_required = True
                    user.save(update_fields=['password_change_required'])
                    AdminActionLog.log_action(
                        user=user,
                        action_type='password_expired',
                        description=f"Privileged account password expired ({age_days} days old): {user.email}",
                        entity_type='User',
                        entity_id=str(user.id),
                        request=request
                    )

            # CTRL-0000001063: privileged accounts must enrol MFA.
            # Issue JWT so they can reach the setup endpoint, but signal
            # the frontend to redirect to MFA setup before allowing access.
            mfa_setup_required = is_privileged and not user.mfa_enabled

            user_data = UserSerializer(user).data
            if mfa_setup_required:
                user_data['mfa_setup_required'] = True

            response = success_response(
                data=user_data,
                message='Login successful — MFA setup required' if mfa_setup_required else 'Login successful',
                status_code=status.HTTP_200_OK
            )

            # SECURITY: Set JWT tokens in HttpOnly cookies
            # Access token for authentication (short-lived)
            response.set_cookie(
                key='access_token',
                value=access_token,
                httponly=True,  # Prevents JavaScript access (XSS protection)
                secure=not settings.DEBUG,  # False in development (HTTP), True in production (HTTPS)
                samesite='Lax', # CSRF protection
                max_age=3600,   # 1 hour (matches ACCESS_TOKEN_LIFETIME)
                path='/'
            )

            # Refresh token for getting new access tokens (long-lived)
            response.set_cookie(
                key='refresh_token',
                value=refresh_token,
                httponly=True,  # Prevents JavaScript access (XSS protection)
                secure=not settings.DEBUG,  # False in development (HTTP), True in production (HTTPS)
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
                secure=not settings.DEBUG,  # False in development (HTTP), True in production (HTTPS)
                samesite='Lax',
                max_age=86400 * 7,
                path='/'
            )

            return response
        else:
            logger.warning(f"Authentication failed for user: {username}")
            # SECURITY: Log failed login attempt for audit trail
            AdminActionLog.log_action(
                user=None,  # User not authenticated
                action_type='login_failed',
                description=f"Failed login attempt for email: {username}",
                entity_type='User',
                entity_id='',
                request=request
            )
            # SECURITY: Generic error message to prevent user enumeration
            return unauthorized_response(message='Invalid credentials')


class LogoutView(APIView):
    """User logout endpoint."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Authentication'],
        summary='User Logout',
        description='Logout the current user. Blacklists refresh token and clears auth cookies.',
        responses={
            200: {'description': 'Successfully logged out'},
            401: {'description': 'Not authenticated'}
        }
    )
    def post(self, request):
        try:
            # SECURITY: Log logout for audit trail
            AdminActionLog.log_action(
                user=request.user,
                action_type='logout',
                description=f"User logged out: {request.user.email}",
                entity_type='User',
                entity_id=str(request.user.id),
                request=request
            )

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
            response = success_response(
                message='Successfully logged out',
                status_code=status.HTTP_200_OK
            )
            response.delete_cookie('access_token', path='/')
            response.delete_cookie('refresh_token', path='/')
            response.delete_cookie('auth_token', path='/')  # Legacy token

            return response
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return error_response(
                message='Logout failed',
                errors={'detail': str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
            return unauthorized_response(message='Refresh token not found')

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

            # Create standardized response
            response = success_response(
                message='Token refreshed successfully',
                status_code=status.HTTP_200_OK
            )

            # Set new access token cookie
            response.set_cookie(
                key='access_token',
                value=new_access_token,
                httponly=True,
                secure=not settings.DEBUG,  # False in development (HTTP), True in production (HTTPS)
                samesite='Lax',
                max_age=3600,  # 1 hour
                path='/'
            )

            # Set new refresh token cookie
            response.set_cookie(
                key='refresh_token',
                value=new_refresh_token,
                httponly=True,
                secure=not settings.DEBUG,  # False in development (HTTP), True in production (HTTPS)
                samesite='Lax',
                max_age=86400 * 7,  # 7 days
                path='/'
            )

            return response

        except TokenError as e:
            logger.warning(f"Token refresh failed: {str(e)}")
            return unauthorized_response(message=f'Invalid refresh token: {str(e)}')


class PasswordChangeView(APIView):
    """
    Change password for authenticated user.
    SECURITY: Clears password_change_required flag after successful change.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors,
                message='Invalid password data'
            )

        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        # Verify old password
        if not user.check_password(old_password):
            return error_response(
                message='Current password is incorrect',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Set new password
        user.set_password(new_password)
        user.password_change_required = False
        user.password_last_changed = timezone.now()  # CTRL-0000001025
        user.save()

        return success_response(
            data={'password_change_required': False},
            message='Password changed successfully',
            status_code=status.HTTP_200_OK
        )


class PasswordResetRequestView(APIView):
    """
    Request a password reset. Sends email with reset token.
    SECURITY: Rate limited to prevent abuse.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Authentication'],
        summary='Request Password Reset',
        description='Request a password reset email. Rate limited to 3 requests per hour.',
        request=PasswordResetRequestSerializer,
        responses={
            200: {'description': 'If the email exists, a reset link will be sent'},
            429: {'description': 'Rate limit exceeded'}
        }
    )
    @method_decorator(ratelimit(key='ip', rate='3/h', method='POST'))
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors,
                message='Invalid email data'
            )

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

            try:
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
            except Exception as e:
                # Log email sending failure but don't expose it to user
                logger.error(f"Failed to send password reset email to {email}: {str(e)}")
                # Continue execution - token is saved, user will see generic success message

        except User.DoesNotExist:
            # SECURITY: Don't reveal if email exists or not
            pass

        # SECURITY: Always return success to prevent email enumeration
        return success_response(
            message='If an account exists with this email, a password reset link has been sent.',
            status_code=status.HTTP_200_OK
        )


class PasswordResetConfirmView(APIView):
    """
    Confirm password reset with token and set new password.
    SECURITY: Token expires after 1 hour.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Authentication'],
        summary='Confirm Password Reset',
        description='Reset password using the token from the reset email.',
        request=PasswordResetConfirmSerializer,
        responses={
            200: {'description': 'Password reset successfully'},
            400: {'description': 'Invalid or expired token'}
        }
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors,
                message='Invalid reset data'
            )

        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            user = User.objects.get(
                password_reset_token=token,
                password_reset_token_expires__gt=timezone.now()
            )

            # Set new password
            user.set_password(new_password)
            user.password_reset_token = None
            user.password_reset_token_expires = None
            user.password_change_required = False
            user.password_last_changed = timezone.now()  # CTRL-0000001025
            user.save()

            logger.info(f"Password reset successful for user: {user.email}")
            return success_response(
                message='Password reset successfully. You can now log in with your new password.',
                status_code=status.HTTP_200_OK
            )

        except User.DoesNotExist:
            return error_response(
                message='Invalid or expired reset token',
                status_code=status.HTTP_400_BAD_REQUEST
            )


class RegisterView(APIView):
    """
    Public endpoint for user self-registration.

    Security Features:
    - Rate limited (3 per hour per IP)
    - Users cannot select their own role
    - Automatically assigned to "Registered User" role
    - All registrations are audit logged
    - No auto-login (prevents bot abuse)
    """
    authentication_classes = []  # Public endpoint - no authentication required
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Authentication'],
        summary='User Self-Registration',
        description='Register a new user account. Users cannot select roles - admin assigns roles later.',
        request=UserRegistrationSerializer,
        responses={
            201: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'data': {'type': 'object'}
                }
            },
            400: {'description': 'Validation error'},
            429: {'description': 'Rate limit exceeded'},
        },
        examples=[
            OpenApiExample(
                'Registration Request',
                value={
                    'email': 'user@example.com',
                    'name': 'John Doe',
                    'password': 'SecurePass123!',
                    'password_confirm': 'SecurePass123!',
                    'staff_id': 'EMP-12345',
                    'phone': '+1234567890',
                    'department': 'IT Department',
                    'gender': 'Male'
                }
            )
        ]
    )
    @method_decorator(ratelimit(key='ip', rate='3/h', method='POST'))
    def post(self, request):
        # Check if rate limited
        was_limited = getattr(request, 'limited', False)
        if was_limited:
            return error_response(
                message='Too many registration attempts. Please try again later.',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS
            )

        serializer = UserRegistrationSerializer(data=request.data)

        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors,
                message='Registration failed. Please correct the errors below.'
            )

        try:
            user = serializer.save()

            # Get IP address from request
            ip_address = self.get_client_ip(request)

            # Log registration action
            AdminActionLog.objects.create(
                user=user,
                action_type='user_created',
                entity_type='User',
                entity_id=str(user.id),
                description=f'User self-registered: {user.email}',
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

            logger.info(
                f"New user registration: {user.email} (ID: {user.id})",
                extra={
                    'user_id': str(user.id),
                    'email': user.email,
                    'ip_address': ip_address
                }
            )

            return created_response(
                data={
                    'id': str(user.id),
                    'email': user.email,
                    'name': user.name,
                    'staff_id': user.staff_id,
                    'role': {
                        'id': str(user.role.id),
                        'name': user.role.name
                    } if user.role else None,
                    'department': {
                        'id': str(user.department.id),
                        'name': user.department.name
                    } if user.department else None
                },
                message='Registration successful! You can now login with your credentials.'
            )

        except Exception as e:
            logger.error(
                f"Registration failed: {str(e)}",
                extra={'error': str(e)},
                exc_info=True
            )
            return error_response(
                message='Registration failed. Please try again later.',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@extend_schema_view(
    list=extend_schema(tags=['Users'], summary='List all users', description='Get paginated list of all users. Supports search and ordering.'),
    retrieve=extend_schema(tags=['Users'], summary='Get user details', description='Get details of a specific user by ID.'),
    create=extend_schema(tags=['Users'], summary='Create user', description='Create a new user. Admin only.'),
    update=extend_schema(tags=['Users'], summary='Update user', description='Update user details. Users can update own profile, admins can update any.'),
    partial_update=extend_schema(tags=['Users'], summary='Partial update user', description='Partially update user details.'),
    destroy=extend_schema(tags=['Users'], summary='Delete user', description='Delete a user. Admin only.')
)
class UserViewSet(viewsets.ModelViewSet):
    """User management viewset with role-based permissions."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    # Filter backends
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    # Search across user fields (use __name for ForeignKey fields)
    search_fields = ['email', 'name', 'staff_id', 'department__name', 'phone']

    # Allow ordering
    ordering_fields = ['email', 'name', 'date_joined', 'department__name', 'is_active']
    ordering = ['-date_joined']  # Default: newest first

    def get_queryset(self):
        """Apply filters for role, department, and is_active."""
        queryset = super().get_queryset()

        # Filter by role (UUID)
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role_id=role)

        # Filter by department (UUID)
        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(department_id=department)

        # Filter by is_active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None and is_active != '':
            # Convert string to boolean
            is_active_bool = is_active.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(is_active=is_active_bool)

        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            # Check if user is updating their own profile
            user_id = self.kwargs.get('pk')
            if user_id and str(self.request.user.id) == str(user_id):
                logger.info(f"User {self.request.user.id} updating own profile")
                return UserProfileUpdateSerializer
            logger.info(f"Admin updating user {user_id}")
            return UserAdminUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        logger.info(f"UserViewSet.get_permissions called for action: {self.action}")
        logger.info(f"Request user: {self.request.user}, is_authenticated: {self.request.user.is_authenticated if hasattr(self.request.user, 'is_authenticated') else 'N/A'}")
        logger.info(f"User is_staff: {getattr(self.request.user, 'is_staff', 'N/A')}, is_superuser: {getattr(self.request.user, 'is_superuser', 'N/A')}")
        
        if self.action == 'create':
            logger.info("Returning IsAdminUser permission for create action")
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
        logger.debug(f"Update called by user {request.user.id} for user {kwargs.get('pk')}")
        logger.debug(f"Request data: {request.data}")
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if not serializer.is_valid():
            logger.error(f"Validation errors: {serializer.errors}")
            return validation_error_response(
                serializer_errors=serializer.errors,
                message='Invalid user data'
            )

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
            return success_response(
                data=user_serializer.data,
                message='Profile updated successfully',
                status_code=status.HTTP_200_OK
            )
        return validation_error_response(
            serializer_errors=serializer.errors,
            message='Invalid profile data'
        )
    
    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAdminUser])
    def change_role(self, request, pk=None):
        user = self.get_object()
        role_id = request.data.get('role_id')

        if not role_id:
            return error_response(
                message='Role ID is required',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            role = Role.objects.get(id=role_id)
            user.role = role
            user.save()
        except Role.DoesNotExist:
            return not_found_response(message='Role not found')

        serializer = self.get_serializer(user)
        return success_response(
            data=serializer.data,
            message='User role updated successfully',
            status_code=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save()

        serializer = self.get_serializer(user)
        return success_response(
            data=serializer.data,
            message='User activated successfully',
            status_code=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save()

        serializer = self.get_serializer(user)
        return success_response(
            data=serializer.data,
            message='User deactivated successfully',
            status_code=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='access-review', permission_classes=[permissions.IsAdminUser])
    def access_review(self, request, pk=None):
        """Record a completed access review for a user. CTRL-0000001018."""
        user = self.get_object()
        user.last_access_review = timezone.now()
        user.last_access_review_by = request.user
        user.save(update_fields=['last_access_review', 'last_access_review_by'])
        AdminActionLog.log_action(
            user=request.user,
            action_type='access_review',
            description=f'Access review completed for user: {user.email}',
            entity_type='User',
            entity_id=str(user.id),
            request=request,
        )
        return success_response(
            data={
                'last_access_review': user.last_access_review.isoformat(),
                'reviewed_by': request.user.email,
            },
            message=f'Access review recorded for {user.email}',
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['get'], url_path='access-review-due', permission_classes=[permissions.IsAdminUser])
    def access_review_due(self, request):
        """List active users overdue for access review (never reviewed or >90 days). CTRL-0000001018."""
        review_threshold = timezone.now() - timedelta(days=90)
        users = self.get_queryset().filter(
            Q(last_access_review__isnull=True) | Q(last_access_review__lt=review_threshold),
            is_active=True,
        )
        serializer = self.get_serializer(users, many=True)
        return success_response(
            data=serializer.data,
            message=f'{users.count()} user(s) due for access review',
            status_code=status.HTTP_200_OK,
        )


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [HasManageRolesPermission]
    pagination_class = None  # Disable pagination for roles

    # Search and ordering
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']  # Default: alphabetical


class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [HasManageRolesPermission]  # Same permission as roles
    pagination_class = None  # Disable pagination for permissions

    # Search and ordering
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']  # Default: alphabetical


@extend_schema_view(
    list=extend_schema(tags=['Departments'], summary='List all departments', description='Get list of all departments. Supports search and filtering.'),
    retrieve=extend_schema(tags=['Departments'], summary='Get department details', description='Get details of a specific department by ID.'),
    create=extend_schema(tags=['Departments'], summary='Create department', description='Create a new department. Admin only.'),
    update=extend_schema(tags=['Departments'], summary='Update department', description='Update department details. Admin only.'),
    partial_update=extend_schema(tags=['Departments'], summary='Partial update department', description='Partially update department details. Admin only.'),
    destroy=extend_schema(tags=['Departments'], summary='Delete department', description='Delete a department. Admin only.')
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
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'code', 'created_at', 'is_active']
    ordering = ['name']  # Default: alphabetical

    def get_permissions(self):
        """
        Allow listing departments for all authenticated users, but restrict modifications to admins.
        The 'active' action is public (used for registration).
        """
        if self.action == 'active':
            return [permissions.AllowAny()]
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = super().get_queryset()

        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        return queryset

    def get_serializer_class(self):
        """Use lightweight serializer for list operations"""
        if self.action == 'list' and self.request.query_params.get('simple') == 'true':
            return DepartmentListSerializer
        return DepartmentSerializer

    def destroy(self, request, *args, **kwargs):
        """Prevent deletion of departments with users"""
        instance = self.get_object()
        user_count = instance.users.count()

        if user_count > 0:
            return error_response(
                message=f'Cannot delete department with {user_count} assigned user(s). Reassign users first.',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def active(self, request):
        """
        Get only active departments (for dropdowns)
        Public endpoint - used for user registration
        """
        queryset = self.get_queryset().filter(is_active=True)
        serializer = DepartmentListSerializer(queryset, many=True)
        return Response(serializer.data)


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
        """
        Permission rules:
        - Public settings (?public=true): Anyone can access
        - List/retrieve: Any authenticated user can read
        - Create/update/delete: Admin only
        """
        if self.action == 'list' and self.request.query_params.get('public') == 'true':
            return [permissions.AllowAny()]
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
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
            return error_response(
                message='settings must be a list',
                status_code=status.HTTP_400_BAD_REQUEST
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

        message = f'Successfully updated {len(updated_settings)} settings'
        if errors:
            message += f', {len(errors)} failed'

        return success_response(
            data={'updated': updated_settings},
            message=message,
            status_code=status.HTTP_200_OK,
            meta={'errors': errors} if errors else None
        )

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
        has_settings_access = request.user.is_superuser or has_permission(request.user, 'view_system_settings')
        if not has_settings_access:
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
            return forbidden_response(
                message='Only administrators can view audit log statistics'
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

        stats_data = {
            'total_logs': queryset.count(),
            'recent_activity_24h': recent_count,
            'by_action_type': list(action_stats),
            'top_users': list(user_stats),
        }

        return success_response(
            data=stats_data,
            message='Audit log statistics retrieved successfully',
            status_code=status.HTTP_200_OK
        )


# ---------------------------------------------------------------------------
# MFA Views — CTRL-0000001024 / CTRL-0000001063
# ---------------------------------------------------------------------------

class MFASetupView(APIView):
    """
    GET  /api/auth/mfa/setup/
    Returns a TOTP secret and QR provisioning URI.
    The user scans the QR code in their authenticator app, then calls
    MFAConfirmView to activate MFA on their account.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.mfa_enabled:
            return error_response(
                message='MFA is already enabled on this account.',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Generate a new secret (overwriting any previous unconfirmed setup)
        secret = pyotp.random_base32()
        user.mfa_secret = secret
        user.save(update_fields=['mfa_secret'])

        totp = pyotp.TOTP(secret)
        qr_uri = totp.provisioning_uri(name=user.email, issuer_name='TMS Application')

        return success_response(
            data={'secret': secret, 'qr_uri': qr_uri},
            message='Scan the QR code with your authenticator app, then confirm with /mfa/confirm/',
            status_code=status.HTTP_200_OK
        )


class MFAConfirmView(APIView):
    """
    POST /api/auth/mfa/confirm/
    Verifies the first OTP from the authenticator app and enables MFA.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = MFAConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        user = request.user
        otp = serializer.validated_data['otp']

        if not user.mfa_secret:
            return error_response(
                message='No MFA setup in progress. Call /mfa/setup/ first.',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(otp, valid_window=1):
            AdminActionLog.log_action(
                user=user,
                action_type='mfa_failed',
                description=f"MFA confirm failed (invalid OTP): {user.email}",
                entity_type='User',
                entity_id=str(user.id),
                request=request
            )
            return error_response(
                message='Invalid OTP code. Please try again.',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        user.mfa_enabled = True
        user.save(update_fields=['mfa_enabled'])

        AdminActionLog.log_action(
            user=user,
            action_type='mfa_enabled',
            description=f"MFA enabled for user: {user.email}",
            entity_type='User',
            entity_id=str(user.id),
            request=request
        )

        return success_response(
            data={'mfa_enabled': True},
            message='MFA has been enabled on your account.',
            status_code=status.HTTP_200_OK
        )


class MFAVerifyView(APIView):
    """
    POST /api/auth/mfa/verify/
    Called after a login attempt returns mfa_required=true.
    Validates the challenge_token and OTP, then issues full JWT cookies.
    """
    permission_classes = [permissions.AllowAny]

    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    def post(self, request):
        serializer = MFAVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        challenge_token = serializer.validated_data['challenge_token']
        otp = serializer.validated_data['otp']

        # Decode the challenge token (max age 5 minutes)
        try:
            data = signing.loads(challenge_token, salt='mfa-login-challenge', max_age=300)
        except SignatureExpired:
            return unauthorized_response(message='MFA challenge expired. Please log in again.')
        except BadSignature:
            return unauthorized_response(message='Invalid challenge token.')

        user = User.objects.filter(id=data.get('user_id')).first()
        if not user or not user.mfa_enabled or not user.mfa_secret:
            return unauthorized_response(message='Invalid MFA session.')

        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(otp, valid_window=1):
            AdminActionLog.log_action(
                user=user,
                action_type='mfa_failed',
                description=f"MFA login verification failed: {user.email}",
                entity_type='User',
                entity_id=str(user.id),
                request=request
            )
            return unauthorized_response(message='Invalid OTP code.')

        # CTRL-0000001025: check password age for privileged accounts after MFA verification.
        is_privileged = user.is_admin or user.is_staff or user.is_superuser
        if is_privileged and user.password_last_changed:
            age_days = (timezone.now() - user.password_last_changed).days
            if age_days >= 30 and not user.password_change_required:
                user.password_change_required = True
                user.save(update_fields=['password_change_required'])
                AdminActionLog.log_action(
                    user=user,
                    action_type='password_expired',
                    description=f"Privileged account password expired ({age_days} days old): {user.email}",
                    entity_type='User',
                    entity_id=str(user.id),
                    request=request
                )

        # OTP valid — issue JWT tokens (same flow as normal login)
        AdminActionLog.log_action(
            user=user,
            action_type='login_success',
            description=f"MFA-verified login for: {user.email}",
            entity_type='User',
            entity_id=str(user.id),
            request=request
        )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token_str = str(refresh)

        response = success_response(
            data=UserSerializer(user).data,
            message='Login successful',
            status_code=status.HTTP_200_OK
        )
        response.set_cookie('access_token', access_token, httponly=True, secure=not settings.DEBUG, samesite='Lax', max_age=3600, path='/')
        response.set_cookie('refresh_token', refresh_token_str, httponly=True, secure=not settings.DEBUG, samesite='Lax', max_age=86400 * 7, path='/')

        token, _ = Token.objects.get_or_create(user=user)
        response.set_cookie('auth_token', token.key, httponly=True, secure=not settings.DEBUG, samesite='Lax', max_age=86400 * 7, path='/')

        return response


class MFADisableView(APIView):
    """
    POST /api/auth/mfa/disable/
    Disables MFA after verifying OTP + account password for safety.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = MFADisableSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        user = request.user
        otp = serializer.validated_data['otp']
        password = serializer.validated_data['password']

        if not user.mfa_enabled:
            return error_response(
                message='MFA is not enabled on this account.',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(password):
            return unauthorized_response(message='Incorrect password.')

        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(otp, valid_window=1):
            AdminActionLog.log_action(
                user=user,
                action_type='mfa_failed',
                description=f"MFA disable failed (invalid OTP): {user.email}",
                entity_type='User',
                entity_id=str(user.id),
                request=request
            )
            return error_response(
                message='Invalid OTP code.',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        user.mfa_enabled = False
        user.mfa_secret = None
        user.save(update_fields=['mfa_enabled', 'mfa_secret'])

        AdminActionLog.log_action(
            user=user,
            action_type='mfa_disabled',
            description=f"MFA disabled for user: {user.email}",
            entity_type='User',
            entity_id=str(user.id),
            request=request
        )

        return success_response(
            data={'mfa_enabled': False},
            message='MFA has been disabled on your account.',
            status_code=status.HTTP_200_OK
        )


class MFAStatusView(APIView):
    """GET /api/auth/mfa/status/ — returns whether MFA is enabled for the current user."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return success_response(
            data={'mfa_enabled': request.user.mfa_enabled},
            message='MFA status retrieved',
            status_code=status.HTTP_200_OK
        )


# ---------------------------------------------------------------------------
# Privacy Policy View — CTRL-0000001000 / CTRL-0000001001 / CTRL-0000001003
# ---------------------------------------------------------------------------

class PrivacyPolicyView(APIView):
    """
    GET /api/auth/privacy-policy/
    Returns the current privacy policy text and version.
    Public endpoint — shown to users before/during registration.
    """
    permission_classes = [permissions.AllowAny]

    POLICY_TEXT = """
TMS APPLICATION PRIVACY NOTICE

1. PURPOSE: Your personal data (name, email, staff ID, phone, department, travel details,
   passport information, and bank details) is collected solely for the purpose of processing
   travel requests and related logistics within the organisation.

2. RETENTION: Personal data is retained for the period required by the organisation's
   data retention policy (default 7 years) and then securely disposed of.

3. PROTECTION: Your data is protected using industry-standard encryption (AES-256 at rest,
   TLS 1.2+ in transit) and access is restricted on a least-privilege basis.

4. ACCESS & CORRECTION: You may request a copy of your personal data or corrections
   by contacting the system administrator.

5. OPT-OUT / ERASURE: Contact the system administrator to request deletion of your
   account and associated personal data, subject to legal retention obligations.

6. THIRD PARTIES: Your data will not be sold or disclosed to third parties outside
   the organisation without your consent, except as required by law.
""".strip()

    def get(self, request):
        from django.conf import settings as django_settings
        version = getattr(django_settings, 'PRIVACY_POLICY_VERSION', '1.0')
        return success_response(
            data={
                'version': version,
                'content': self.POLICY_TEXT,
                'effective_date': '2026-01-01',
            },
            message='Privacy policy retrieved',
            status_code=status.HTTP_200_OK
        )
