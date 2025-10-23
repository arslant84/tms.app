from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model, authenticate, login
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.authtoken.views import ObtainAuthToken

from .serializers import (
    UserSerializer, UserCreateSerializer, RoleSerializer, PermissionSerializer,
    ApplicationSettingSerializer, ApplicationSettingCreateSerializer, ApplicationSettingUpdateSerializer
)
from .models import Role, Permission, ApplicationSetting

User = get_user_model()


class LoginView(ObtainAuthToken):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        # Get username and password from request
        username = request.data.get('email')
        password = request.data.get('password')
        
        print(f"Login attempt for user: {username}")
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Create or get token
            token, created = Token.objects.get_or_create(user=user)
            
            # Return token and user data in format expected by Angular frontend
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data
            })
        else:
            print(f"Authentication failed for user: {username}")
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Delete the token to logout
        try:
            request.user.auth_token.delete()
            return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAdminUser()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Get the current user's profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
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
    permission_classes = [permissions.IsAdminUser]
    pagination_class = None  # Disable pagination for roles


class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAdminUser]
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

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def as_object(self, request):
        """
        Return all settings as a simple key-value object.

        Query parameters:
        - public: bool - Return only public settings

        Returns: {"setting_key": value, ...}
        """
        queryset = self.get_queryset()
        settings_obj = {}

        for setting in queryset:
            settings_obj[setting.setting_key] = setting.get_value()

        return Response(settings_obj)
