"""
Transport Serializers
Redesigned to match React source project structure (pctsb.syntra)
NO cost fields - only basic transport details
"""

from accounts.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from rest_framework import serializers

from .models import TransportApprovalStep, TransportRequest, VehicleAssignment


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for nested representation"""

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "department"]
        read_only_fields = ["id", "email", "first_name", "last_name", "department"]


class TransportApprovalStepSerializer(serializers.ModelSerializer):
    """Serializer for transport approval steps"""

    class Meta:
        model = TransportApprovalStep
        fields = [
            "id",
            "transport_request",
            "step_role",
            "step_name",
            "status",
            "step_date",
            "comments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class VehicleAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for vehicle assignments"""

    assigned_by_user = UserSerializer(source="assigned_by", read_only=True)

    class Meta:
        model = VehicleAssignment
        fields = [
            "id",
            "transport_request",
            "vehicle_number",
            "vehicle_type",
            "vehicle_capacity",
            "driver_name",
            "driver_contact",
            "driver_license",
            "assigned_by",
            "assigned_by_user",
            "status",
            "odometer_start",
            "odometer_end",
            "fuel_used_liters",
            "assignment_date",
            "completion_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "assigned_by",
            "assignment_date",
            "created_at",
            "updated_at",
        ]


class TransportRequestSerializer(serializers.ModelSerializer):
    """
    Main serializer for TransportRequest
    Matches React source structure exactly
    """

    requestor_email = serializers.EmailField(source="requestor.email", read_only=True)
    detail_count = serializers.SerializerMethodField()
    vehicle_assignments = VehicleAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = TransportRequest
        fields = [
            "id",
            "request_number",
            "requestor",
            "requestor_email",
            "requestor_name",
            "staff_id",
            "department",
            "position",
            "purpose",
            "tsr_reference",
            "status",
            "transport_details",
            "detail_count",
            "additional_comments",
            "booking_details",
            "vehicle_assignments",
            "submitted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "request_number",
            "requestor",
            "created_at",
            "updated_at",
        ]

    def get_detail_count(self, obj):
        """Get the number of transport details"""
        if isinstance(obj.transport_details, list):
            return len(obj.transport_details)
        return 0

    def validate_transport_details(self, value):
        """Validate transport details array - SECURITY: Comprehensive validation"""
        if not isinstance(value, list):
            raise serializers.ValidationError("transport_details must be an array")

        if len(value) == 0:
            raise serializers.ValidationError(
                "At least one transport detail is required"
            )

        # SECURITY: Limit number of transport details to prevent DoS
        if len(value) > 50:
            raise serializers.ValidationError("Maximum 50 transport details allowed")

        # Validate each transport detail object
        required_fields = ["from", "to", "departureTime", "numberOfPassengers"]
        for i, detail in enumerate(value):
            for field in required_fields:
                if field not in detail or not detail[field]:
                    raise serializers.ValidationError(
                        f"Transport detail #{i+1}: '{field}' is required"
                    )

            # SECURITY: Validate string lengths to prevent excessive data
            if len(str(detail.get("from", ""))) > 200:
                raise serializers.ValidationError(
                    f"Transport detail #{i+1}: 'from' location too long (max 200 characters)"
                )
            if len(str(detail.get("to", ""))) > 200:
                raise serializers.ValidationError(
                    f"Transport detail #{i+1}: 'to' location too long (max 200 characters)"
                )

            # SECURITY: Validate numberOfPassengers range
            num_passengers = detail.get("numberOfPassengers", 0)
            if not isinstance(num_passengers, (int, float)) or num_passengers < 1:
                raise serializers.ValidationError(
                    f"Transport detail #{i+1}: numberOfPassengers must be at least 1"
                )
            if num_passengers > 100:
                raise serializers.ValidationError(
                    f"Transport detail #{i+1}: numberOfPassengers must be 100 or less"
                )

        return value

    def validate_purpose(self, value):
        """SECURITY: Validate purpose length"""
        if len(str(value).strip()) < 10:
            raise serializers.ValidationError("Purpose must be at least 10 characters")
        if len(str(value)) > 1000:
            raise serializers.ValidationError("Purpose too long (max 1000 characters)")
        return value.strip()

    def validate_additional_comments(self, value):
        """SECURITY: Validate comments length"""
        if value and len(str(value)) > 2000:
            raise serializers.ValidationError("Comments too long (max 2000 characters)")
        return value


class TransportRequestDetailSerializer(TransportRequestSerializer):
    """Detailed serializer with nested data"""

    requestor = UserSerializer(read_only=True)
    approval_steps = TransportApprovalStepSerializer(many=True, read_only=True)
    selected_approvers = serializers.SerializerMethodField()
    skipped_steps = serializers.SerializerMethodField()

    class Meta(TransportRequestSerializer.Meta):
        fields = TransportRequestSerializer.Meta.fields + [
            "approval_steps",
            "selected_approvers",
            "skipped_steps",
        ]

    def get_selected_approvers(self, obj):
        """Get selected approvers from workflow instance additional_data"""
        from django.contrib.contenttypes.models import ContentType
        from workflows.models import WorkflowInstance

        try:
            content_type = ContentType.objects.get_for_model(obj)
            workflow_instance = (
                WorkflowInstance.objects.filter(
                    content_type=content_type, object_id=obj.id
                )
                .order_by("-created_at")
                .first()
            )
            if workflow_instance and workflow_instance.additional_data:
                stored_approvers = workflow_instance.additional_data.get(
                    "selected_approvers", {}
                )
                # Convert string keys to integers for frontend compatibility
                return {int(k): v for k, v in stored_approvers.items()}
        except Exception:
            pass
        return {}

    def get_skipped_steps(self, obj):
        """Get skipped steps from workflow instance additional_data"""
        from django.contrib.contenttypes.models import ContentType
        from workflows.models import WorkflowInstance

        try:
            content_type = ContentType.objects.get_for_model(obj)
            workflow_instance = (
                WorkflowInstance.objects.filter(
                    content_type=content_type, object_id=obj.id
                )
                .order_by("-created_at")
                .first()
            )
            if workflow_instance and workflow_instance.additional_data:
                stored_skipped = workflow_instance.additional_data.get(
                    "skipped_steps", {}
                )
                # Convert string keys to integers for frontend compatibility
                return {int(k): v for k, v in stored_skipped.items()}
        except Exception:
            pass
        return {}


class TransportRequestCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating transport requests
    Matches React source exactly - NO cost fields
    """

    class Meta:
        model = TransportRequest
        fields = [
            "trf",
            "requestor_name",
            "staff_id",
            "department",
            "position",
            "purpose",
            "tsr_reference",
            "status",
            "transport_details",
            "additional_comments",
        ]

    def validate(self, data):
        """Validate transport request data"""
        # Validate transport_details
        transport_details = data.get("transport_details", [])
        if not isinstance(transport_details, list) or len(transport_details) == 0:
            raise serializers.ValidationError(
                {"transport_details": "At least one transport detail is required"}
            )

        # Validate each detail - accept both camelCase (from React) and snake_case (from Angular)
        required_fields = [
            ("date", "date"),  # Date field (same in both)
            ("from", "from"),
            ("to", "to"),
            ("departure_time", "departureTime"),
            ("number_of_passengers", "numberOfPassengers"),
        ]

        for i, detail in enumerate(transport_details):
            for snake_case, camel_case in required_fields:
                # Check if either snake_case or camelCase field exists and has value
                snake_value = detail.get(snake_case)
                camel_value = detail.get(camel_case)

                if not snake_value and not camel_value:
                    raise serializers.ValidationError(
                        {
                            "transport_details": f"Detail #{i+1}: '{snake_case}' is required"
                        }
                    )

        return data

    def create(self, validated_data):
        """Create transport request"""
        transport_request = TransportRequest.objects.create(**validated_data)
        return transport_request


class TransportRequestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating transport requests"""

    class Meta:
        model = TransportRequest
        fields = [
            "requestor_name",
            "staff_id",
            "department",
            "position",
            "purpose",
            "tsr_reference",
            "status",
            "transport_details",
            "additional_comments",
            "booking_details",
        ]

    def validate(self, data):
        """Validate update - cannot update submitted/approved requests"""
        instance = self.instance

        # Allow booking_details update by transport admin on any status
        if "booking_details" in data and len(data) == 1:
            # Only updating booking_details, allow this
            return data

        # For other fields, check status
        # Allow editing for Draft, Rejected, Submitted, and any Pending status
        status = instance.status or ""
        can_edit = status in ["Draft", "Rejected", "Submitted"] or status.startswith(
            "Pending"
        )

        if not can_edit:
            raise serializers.ValidationError(
                f"Cannot update transport request with status '{instance.status}'"
            )

        # Validate transport_details if provided
        if "transport_details" in data:
            transport_details = data["transport_details"]
            if not isinstance(transport_details, list) or len(transport_details) == 0:
                raise serializers.ValidationError(
                    {"transport_details": "At least one transport detail is required"}
                )

        return data


class ApprovalActionSerializer(serializers.Serializer):
    """Serializer for approval actions (approve/reject)"""

    comments = serializers.CharField(required=False, allow_blank=True)

    def validate_comments(self, value):
        """Validate comments are provided for rejection"""
        action_type = self.context.get("action_type")
        if action_type == "reject" and not value:
            raise serializers.ValidationError(
                "Comments are required when rejecting a transport request"
            )
        return value
