import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import AdminActionLog, ApplicationSetting, Department, Permission, Role

User = get_user_model()


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department model with user count"""

    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            "id",
            "name",
            "code",
            "description",
            "is_active",
            "user_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_user_count(self, obj):
        """Return the number of users in this department"""
        return obj.users.count()


class DepartmentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Department listings (dropdowns, etc.)"""

    class Meta:
        model = Department
        fields = ["id", "name", "code", "is_active"]


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = "__all__"


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permissionIds = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "description",
            "permissions",
            "permissionIds",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        """Create role with permissions"""
        permission_ids = validated_data.pop("permissionIds", [])
        role = Role.objects.create(**validated_data)

        if permission_ids:
            permissions = Permission.objects.filter(id__in=permission_ids)
            role.permissions.set(permissions)

        return role

    def update(self, instance, validated_data):
        """Update role with permissions"""
        permission_ids = validated_data.pop("permissionIds", None)

        # Update basic fields
        instance.name = validated_data.get("name", instance.name)
        instance.description = validated_data.get("description", instance.description)
        instance.save()

        # Update permissions if provided
        if permission_ids is not None:
            permissions = Permission.objects.filter(id__in=permission_ids)
            instance.permissions.set(permissions)

        return instance

    def to_representation(self, instance):
        """Add permissionIds to response"""
        data = super().to_representation(instance)
        data["permissionIds"] = [str(p.id) for p in instance.permissions.all()]
        return data


class RoleSlimSerializer(serializers.ModelSerializer):
    """Role representation for list views — id and name only, no nested permissions."""

    class Meta:
        model = Role
        fields = ["id", "name"]


class UserListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for user list views.

    Intentionally omits ``profile_photo`` (stored as base64, up to 5 MB per user)
    and replaces the full ``RoleSerializer`` (which nests all permissions) with a
    slim id+name representation.  Use ``UserSerializer`` for single-user detail views.
    """

    role = RoleSlimSerializer(read_only=True)
    department = DepartmentListSerializer(read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "role",
            "department",
            "is_admin",
            "is_active",
            "staff_id",
            "phone",
            "last_login_at",
            "permissions",
            "password_change_required",
        ]
        read_only_fields = fields

    def get_permissions(self, obj):
        if obj.role_id:
            return list(obj.role.permissions.values_list("name", flat=True))
        return []


class UserSerializer(serializers.ModelSerializer):
    role = RoleSerializer(
        read_only=True
    )  # Make role read_only to prevent validation errors
    department = DepartmentListSerializer(read_only=True)  # Include department details
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "role",
            "department",
            "is_admin",
            "is_active",
            "staff_id",
            "phone",
            "position",
            "profile_photo",
            "gender",
            "last_login_at",
            "permissions",
            "password_change_required",
        ]
        # SECURITY: Prevent privilege escalation - these fields can only be modified by admins
        read_only_fields = [
            "id",
            "email",
            "is_admin",
            "is_active",
            "role",
            "department",
            "last_login_at",
            "permissions",
            "password_change_required",
        ]

    def get_permissions(self, obj):
        """Get list of permission names for this user"""
        if obj.role:
            return list(obj.role.permissions.values_list("name", flat=True))
        return []

    def to_internal_value(self, data):
        """Remove role from input data before validation to prevent errors"""
        # Create a mutable copy of the data
        data = data.copy() if hasattr(data, "copy") else dict(data)
        # Remove fields that shouldn't be updated through this serializer
        data.pop("role", None)
        data.pop("is_admin", None)
        data.pop("is_active", None)
        data.pop("email", None)
        data.pop("permissions", None)
        data.pop(
            "password_change_required", None
        )  # SECURITY: Only admins can modify this
        return super().to_internal_value(data)

    def update(self, instance, validated_data):
        # SECURITY: Extra protection - explicitly prevent modification of sensitive fields
        validated_data.pop("is_admin", None)
        validated_data.pop("is_active", None)
        validated_data.pop("role", None)
        validated_data.pop("email", None)
        return super().update(instance, validated_data)


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for user profile updates - only editable fields"""

    # Make all fields optional for partial updates
    name = serializers.CharField(required=False)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    position = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    gender = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    profile_photo = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    class Meta:
        model = User
        fields = ["name", "phone", "position", "gender", "profile_photo"]

    def validate_profile_photo(self, value):
        """Validate profile photo - can be None or a base64 string"""
        if value and isinstance(value, str) and value.strip():
            # SECURITY: Validate base64 size to prevent DoS
            if len(value) > 5 * 1024 * 1024:  # 5MB limit
                raise serializers.ValidationError("Image too large (max 5MB)")

            # SECURITY: Validate MIME type
            if not value.startswith("data:image/"):
                raise serializers.ValidationError(
                    "Invalid image format. Must be a base64 data URL."
                )

            # SECURITY: Check specific allowed types
            allowed_types = [
                "data:image/jpeg",
                "data:image/jpg",
                "data:image/png",
                "data:image/gif",
            ]
            if not any(value.startswith(t) for t in allowed_types):
                raise serializers.ValidationError(
                    "Only JPEG, PNG, and GIF images are allowed"
                )

        return value


class UserAdminUpdateSerializer(serializers.ModelSerializer):
    """Serializer for admin user updates - allows updating all fields"""

    role = RoleSerializer(read_only=True)
    role_id = serializers.UUIDField(
        write_only=True, required=False, allow_null=True
    )  # Accept role UUID for updates
    department_data = DepartmentListSerializer(source="department", read_only=True)
    permissions = serializers.SerializerMethodField()
    password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password],
        allow_blank=True,
    )
    password_confirm = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    # Accept department as string (UUID, code, or name) - handle conversion in update()
    department = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "role",
            "role_id",
            "department",
            "department_data",
            "is_admin",
            "is_active",
            "staff_id",
            "phone",
            "position",
            "profile_photo",
            "gender",
            "last_login_at",
            "permissions",
            "password",
            "password_confirm",
            "password_change_required",
        ]
        read_only_fields = ["id", "last_login_at", "permissions", "department_data"]

    def get_permissions(self, obj):
        """Get list of permission names for this user"""
        if obj.role:
            return list(obj.role.permissions.values_list("name", flat=True))
        return []

    def validate_email(self, value):
        """Validate email uniqueness excluding current user"""
        if self.instance:
            # Check if email exists for other users (exclude current user)
            if User.objects.filter(email=value).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError(
                    "user with this email address already exists."
                )
        else:
            # For create, check if email exists at all
            if User.objects.filter(email=value).exists():
                raise serializers.ValidationError(
                    "user with this email address already exists."
                )
        return value

    def validate(self, attrs):
        # Only validate passwords if they're being updated
        password = attrs.get("password", "").strip()
        password_confirm = attrs.get("password_confirm", "").strip()

        if password or password_confirm:
            if password != password_confirm:
                raise serializers.ValidationError(
                    {"password": "Password fields didn't match."}
                )

        return attrs

    def update(self, instance, validated_data):
        # Handle password update separately
        password = validated_data.pop("password", "").strip()
        validated_data.pop("password_confirm", None)

        # Handle role update (comes as UUID from frontend via role_id field)
        role_id = validated_data.pop("role_id", None)
        if role_id:
            try:
                role = Role.objects.get(id=role_id)
                instance.role = role
            except Role.DoesNotExist:
                pass

        # Handle department update (can be UUID, code, or name)
        department_value = validated_data.pop("department", None)
        if department_value and department_value.strip():
            department_value = department_value.strip()
            department = None

            # Try to find department by UUID first
            try:
                uuid.UUID(department_value)  # Validate it's a UUID
                department = Department.objects.get(id=department_value)
            except (ValueError, Department.DoesNotExist):
                pass

            # If not found by UUID, try by code
            if not department:
                try:
                    department = Department.objects.get(code__iexact=department_value)
                except Department.DoesNotExist:
                    pass

            # If still not found, try by name
            if not department:
                try:
                    department = Department.objects.get(name__iexact=department_value)
                except Department.DoesNotExist:
                    pass

            if department:
                instance.department = department
        elif department_value == "" or department_value is None:
            # Allow clearing department
            if "department" in self.initial_data:
                instance.department = None

        # Update all other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Update password if provided
        if password:
            instance.set_password(password)

        instance.save()
        return instance


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True, required=True)
    department_data = DepartmentListSerializer(source="department", read_only=True)
    # Accept department as string (UUID, code, or name)
    department = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "role",
            "department",
            "department_data",
            "is_admin",
            "is_active",
            "staff_id",
            "phone",
            "gender",
            "password",
            "password_confirm",
        ]
        read_only_fields = ["id", "department_data"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs

    def validate_department(self, value):
        """Validate and convert department (UUID, code, or name) to Department object"""
        if not value or not value.strip():
            return None

        value = value.strip()
        department = None

        # Try to find department by UUID first
        try:
            uuid.UUID(value)  # Validate it's a UUID
            department = Department.objects.get(id=value)
        except (ValueError, Department.DoesNotExist):
            pass

        # If not found by UUID, try by code
        if not department:
            try:
                department = Department.objects.get(code__iexact=value)
            except Department.DoesNotExist:
                pass

        # If still not found, try by name
        if not department:
            try:
                department = Department.objects.get(name__iexact=value)
            except Department.DoesNotExist:
                pass

        if not department:
            raise serializers.ValidationError("Department not found.")

        return department

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        return user


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user self-registration.
    Security: Users CANNOT select their own role - automatically assigned "Registered User" role.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        validators=[validate_password],
    )
    password_confirm = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    department = serializers.CharField(
        required=True, help_text="Department UUID, code, or name"
    )
    profile_photo = serializers.CharField(
        required=False, allow_blank=True, help_text="Base64 encoded image (max 5MB)"
    )

    privacy_consent = serializers.BooleanField(
        required=True,
        help_text="Must be true — user accepts the privacy policy (CTRL-0000001000/1001/1003)",
    )
    privacy_policy_version = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Privacy policy version accepted by the user",
    )

    class Meta:
        model = User
        fields = [
            "email",
            "name",
            "password",
            "password_confirm",
            "staff_id",
            "phone",
            "department",
            "gender",
            "profile_photo",
            "privacy_consent",
            "privacy_policy_version",
        ]
        extra_kwargs = {
            "staff_id": {"required": False},
            "phone": {"required": False},
            "gender": {"required": False},
        }

    def validate_privacy_consent(self, value):
        if not value:
            raise serializers.ValidationError(
                "You must accept the privacy policy to register."
            )
        return value

    def validate_email(self, value):
        """Ensure email is unique"""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email address already exists."
            )
        return value.lower()

    def validate_password_confirm(self, value):
        """Ensure password confirmation matches"""
        password = self.initial_data.get("password")
        if password != value:
            raise serializers.ValidationError("Passwords do not match.")
        return value

    def validate_department(self, value):
        """Resolve department by UUID, code, or name"""
        # Try UUID
        try:
            return Department.objects.get(id=value, is_active=True)
        except (Department.DoesNotExist, ValueError):
            pass

        # Try code
        try:
            return Department.objects.get(code__iexact=value, is_active=True)
        except Department.DoesNotExist:
            pass

        # Try name
        try:
            return Department.objects.get(name__iexact=value, is_active=True)
        except Department.DoesNotExist:
            raise serializers.ValidationError(
                "Department not found. Please provide a valid department."
            )

    def validate_profile_photo(self, value):
        """Validate base64 image"""
        if not value:
            return value

        # SECURITY: Validate base64 size to prevent DoS
        if len(value) > 5 * 1024 * 1024:  # 5MB limit
            raise serializers.ValidationError("Image too large (max 5MB)")

        # SECURITY: Validate MIME type
        if not value.startswith("data:image/"):
            raise serializers.ValidationError(
                "Invalid image format. Must be a base64 data URL."
            )

        return value

    def create(self, validated_data):
        """Create user with default 'Registered User' role"""
        from django.conf import settings as django_settings
        from django.utils import timezone as tz

        validated_data.pop("password_confirm")

        try:
            registered_user_role = Role.objects.get(name="Registered User")
        except Role.DoesNotExist:
            raise serializers.ValidationError(
                "System error: Default registration role not found. Please contact administrator."
            )

        validated_data["role"] = registered_user_role
        validated_data["is_admin"] = False
        validated_data["is_active"] = True

        # Stamp privacy consent timestamp (CTRL-0000001000/1001/1003)
        if validated_data.get("privacy_consent"):
            validated_data["privacy_consent_date"] = tz.now()
        if not validated_data.get("privacy_policy_version"):
            validated_data["privacy_policy_version"] = getattr(
                django_settings, "PRIVACY_POLICY_VERSION", "1.0"
            )

        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, style={"input_type": "password"})


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change (including forced password change)"""

    old_password = serializers.CharField(
        required=True, style={"input_type": "password"}
    )
    new_password = serializers.CharField(
        required=True, validators=[validate_password], style={"input_type": "password"}
    )
    new_password_confirm = serializers.CharField(
        required=True, style={"input_type": "password"}
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password": "Password fields didn't match."}
            )
        return attrs


class ApplicationSettingSerializer(serializers.ModelSerializer):
    """Serializer for ApplicationSetting model with typed values"""

    value = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationSetting
        fields = [
            "id",
            "setting_key",
            "setting_value",
            "value",
            "setting_type",
            "description",
            "is_public",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_value(self, obj):
        """Return the typed value instead of string"""
        return obj.get_value()


class ApplicationSettingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating application settings"""

    value = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = ApplicationSetting
        fields = [
            "setting_key",
            "value",
            "setting_value",
            "setting_type",
            "description",
            "is_public",
        ]

    def validate(self, attrs):
        """Allow setting value either as typed 'value' or raw 'setting_value'"""
        if "value" in attrs and "setting_value" not in attrs:
            # Convert typed value to string
            value = attrs.pop("value")
            setting_type = attrs.get("setting_type", "string")
            if setting_type == "boolean":
                attrs["setting_value"] = "true" if value else "false"
            elif setting_type == "number":
                attrs["setting_value"] = str(value)
            elif setting_type == "json":
                import json

                attrs["setting_value"] = json.dumps(value)
            else:
                attrs["setting_value"] = str(value)
        return attrs


class ApplicationSettingUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating application settings"""

    value = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = ApplicationSetting
        fields = ["setting_value", "value", "setting_type", "description", "is_public"]

    def validate(self, attrs):
        """Allow setting value either as typed 'value' or raw 'setting_value'"""
        if "value" in attrs and "setting_value" not in attrs:
            # Convert typed value to string
            value = attrs.pop("value")
            setting_type = attrs.get(
                "setting_type",
                self.instance.setting_type if self.instance else "string",
            )
            if setting_type == "boolean":
                attrs["setting_value"] = "true" if value else "false"
            elif setting_type == "number":
                attrs["setting_value"] = str(value)
            elif setting_type == "json":
                import json

                attrs["setting_value"] = json.dumps(value)
            else:
                attrs["setting_value"] = str(value)
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting a password reset"""

    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming password reset with token"""

    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True, validators=[validate_password], style={"input_type": "password"}
    )
    new_password_confirm = serializers.CharField(
        required=True, style={"input_type": "password"}
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password": "Password fields didn't match."}
            )
        return attrs


class AdminActionLogSerializer(serializers.ModelSerializer):
    """
    Serializer for audit logs.
    Read-only serializer for viewing security audit trail.
    """

    user_email = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    action_type_display = serializers.CharField(
        source="get_action_type_display", read_only=True
    )

    class Meta:
        model = AdminActionLog
        fields = [
            "id",
            "user",
            "user_email",
            "user_name",
            "action_type",
            "action_type_display",
            "entity_type",
            "entity_id",
            "description",
            "ip_address",
            "user_agent",
            "created_at",
        ]
        read_only_fields = fields  # All fields are read-only

    def get_user_email(self, obj):
        """Return email of user who performed the action"""
        return obj.user.email if obj.user else "System/Unknown"

    def get_user_name(self, obj):
        """Return name of user who performed the action"""
        return obj.user.name if obj.user else "System/Unknown"


# ---------------------------------------------------------------------------
# MFA Serializers — CTRL-0000001024 / CTRL-0000001063
# ---------------------------------------------------------------------------


class MFAStatusSerializer(serializers.Serializer):
    mfa_enabled = serializers.BooleanField(read_only=True)


class MFAConfirmSerializer(serializers.Serializer):
    """Verify a TOTP code to enable MFA after setup."""

    otp = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6,
        help_text="6-digit TOTP code from authenticator app",
    )


class MFAVerifySerializer(serializers.Serializer):
    """Verify a TOTP code during the login MFA challenge step."""

    otp = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6,
        help_text="6-digit TOTP code from authenticator app",
    )
    challenge_token = serializers.CharField(
        required=True,
        help_text="Short-lived challenge token returned by login when MFA is required",
    )


class MFADisableSerializer(serializers.Serializer):
    """Disable MFA — requires both current OTP and account password for safety."""

    otp = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6,
        help_text="6-digit TOTP code from authenticator app",
    )
    password = serializers.CharField(
        required=True,
        style={"input_type": "password"},
        help_text="Current account password",
    )


class PrivacyPolicySerializer(serializers.Serializer):
    version = serializers.CharField(read_only=True)
    content = serializers.CharField(read_only=True)
    effective_date = serializers.CharField(read_only=True)
