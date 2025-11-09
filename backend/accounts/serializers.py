from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Role, Permission, ApplicationSetting

User = get_user_model()


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = '__all__'


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permissionIds = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'permissions', 'permissionIds', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Create role with permissions"""
        permission_ids = validated_data.pop('permissionIds', [])
        role = Role.objects.create(**validated_data)

        if permission_ids:
            permissions = Permission.objects.filter(id__in=permission_ids)
            role.permissions.set(permissions)

        return role

    def update(self, instance, validated_data):
        """Update role with permissions"""
        permission_ids = validated_data.pop('permissionIds', None)

        # Update basic fields
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.save()

        # Update permissions if provided
        if permission_ids is not None:
            permissions = Permission.objects.filter(id__in=permission_ids)
            instance.permissions.set(permissions)

        return instance

    def to_representation(self, instance):
        """Add permissionIds to response"""
        data = super().to_representation(instance)
        data['permissionIds'] = [str(p.id) for p in instance.permissions.all()]
        return data


class UserSerializer(serializers.ModelSerializer):
    role = RoleSerializer()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'department', 'is_admin', 'is_active', 'staff_id', 'phone', 'profile_photo', 'gender', 'last_login_at']
        # SECURITY: Prevent privilege escalation - these fields can only be modified by admins
        read_only_fields = ['id', 'email', 'is_admin', 'is_active', 'role', 'last_login_at']

    def update(self, instance, validated_data):
        # SECURITY: Extra protection - explicitly prevent modification of sensitive fields
        validated_data.pop('is_admin', None)
        validated_data.pop('is_active', None)
        validated_data.pop('role', None)
        validated_data.pop('email', None)
        return super().update(instance, validated_data)


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for user profile updates - only editable fields"""
    # Make all fields optional for partial updates
    name = serializers.CharField(required=False)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    gender = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    profile_photo = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ['name', 'phone', 'gender', 'profile_photo']

    def validate_profile_photo(self, value):
        """Validate profile photo - can be None or a base64 string"""
        if value and isinstance(value, str) and value.strip():
            # SECURITY: Validate base64 size to prevent DoS
            if len(value) > 5 * 1024 * 1024:  # 5MB limit
                raise serializers.ValidationError('Image too large (max 5MB)')

            # SECURITY: Validate MIME type
            if not value.startswith('data:image/'):
                raise serializers.ValidationError('Invalid image format. Must be a base64 data URL.')

            # SECURITY: Check specific allowed types
            allowed_types = ['data:image/jpeg', 'data:image/jpg', 'data:image/png', 'data:image/gif']
            if not any(value.startswith(t) for t in allowed_types):
                raise serializers.ValidationError('Only JPEG, PNG, and GIF images are allowed')

        return value


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'department', 'is_admin', 'is_active', 'password', 'password_confirm']
        read_only_fields = ['id']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, style={'input_type': 'password'})


class ApplicationSettingSerializer(serializers.ModelSerializer):
    """Serializer for ApplicationSetting model with typed values"""
    value = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationSetting
        fields = ['id', 'setting_key', 'setting_value', 'value', 'setting_type', 'description', 'is_public', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_value(self, obj):
        """Return the typed value instead of string"""
        return obj.get_value()


class ApplicationSettingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating application settings"""
    value = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = ApplicationSetting
        fields = ['setting_key', 'value', 'setting_value', 'setting_type', 'description', 'is_public']

    def validate(self, attrs):
        """Allow setting value either as typed 'value' or raw 'setting_value'"""
        if 'value' in attrs and 'setting_value' not in attrs:
            # Convert typed value to string
            value = attrs.pop('value')
            setting_type = attrs.get('setting_type', 'string')
            if setting_type == 'boolean':
                attrs['setting_value'] = 'true' if value else 'false'
            elif setting_type == 'number':
                attrs['setting_value'] = str(value)
            elif setting_type == 'json':
                import json
                attrs['setting_value'] = json.dumps(value)
            else:
                attrs['setting_value'] = str(value)
        return attrs


class ApplicationSettingUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating application settings"""
    value = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = ApplicationSetting
        fields = ['setting_value', 'value', 'setting_type', 'description', 'is_public']

    def validate(self, attrs):
        """Allow setting value either as typed 'value' or raw 'setting_value'"""
        if 'value' in attrs and 'setting_value' not in attrs:
            # Convert typed value to string
            value = attrs.pop('value')
            setting_type = attrs.get('setting_type', self.instance.setting_type if self.instance else 'string')
            if setting_type == 'boolean':
                attrs['setting_value'] = 'true' if value else 'false'
            elif setting_type == 'number':
                attrs['setting_value'] = str(value)
            elif setting_type == 'json':
                import json
                attrs['setting_value'] = json.dumps(value)
            else:
                attrs['setting_value'] = str(value)
        return attrs

