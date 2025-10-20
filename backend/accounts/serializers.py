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

    class Meta:
        model = Role
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    role = RoleSerializer()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'department', 'is_admin', 'is_active', 'staff_id', 'phone', 'profile_photo', 'gender', 'last_login_at']
        read_only_fields = ['id']


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

