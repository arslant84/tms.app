from rest_framework import serializers
from .models import (
    TransportRequest, TransportSegment, TransportApprovalStep, VehicleAssignment
)
from accounts.models import User
from trf.models import TravelRequest


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for nested representation"""
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'department']
        read_only_fields = ['id', 'email', 'first_name', 'last_name', 'department']


class TransportSegmentSerializer(serializers.ModelSerializer):
    """Serializer for transport segments"""
    class Meta:
        model = TransportSegment
        fields = [
            'id', 'transport_request', 'from_location', 'to_location',
            'departure_date', 'departure_time', 'arrival_date', 'arrival_time',
            'distance_km', 'estimated_duration_hours', 'route_description',
            'vehicle_number', 'driver_name', 'driver_contact', 'segment_cost',
            'remarks', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        """Validate segment data"""
        # Validate arrival is after departure
        if data.get('arrival_date') and data.get('departure_date'):
            if data['arrival_date'] < data['departure_date']:
                raise serializers.ValidationError(
                    "Arrival date cannot be before departure date"
                )

        # Validate distance is positive
        if data.get('distance_km') and data['distance_km'] <= 0:
            raise serializers.ValidationError("Distance must be positive")

        # Validate duration is positive
        if data.get('estimated_duration_hours') and data['estimated_duration_hours'] <= 0:
            raise serializers.ValidationError("Duration must be positive")

        return data


class TransportApprovalStepSerializer(serializers.ModelSerializer):
    """Serializer for transport approval steps"""
    class Meta:
        model = TransportApprovalStep
        fields = [
            'id', 'transport_request', 'step_role', 'step_name', 'status',
            'step_date', 'comments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VehicleAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for vehicle assignments"""
    assigned_by_user = UserSerializer(source='assigned_by', read_only=True)

    class Meta:
        model = VehicleAssignment
        fields = [
            'id', 'transport_request', 'vehicle_number', 'vehicle_type',
            'vehicle_capacity', 'driver_name', 'driver_contact', 'driver_license',
            'assigned_by', 'assigned_by_user', 'status', 'odometer_start',
            'odometer_end', 'fuel_used_liters', 'assignment_date',
            'completion_date', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'assigned_by', 'assignment_date', 'created_at', 'updated_at'
        ]

    def validate(self, data):
        """Validate vehicle assignment data"""
        # Validate vehicle capacity
        if data.get('vehicle_capacity') and data['vehicle_capacity'] < 1:
            raise serializers.ValidationError("Vehicle capacity must be at least 1")

        # Validate odometer readings
        if data.get('odometer_end') and data.get('odometer_start'):
            if data['odometer_end'] < data['odometer_start']:
                raise serializers.ValidationError(
                    "Ending odometer reading cannot be less than starting reading"
                )

        # Validate fuel used
        if data.get('fuel_used_liters') and data['fuel_used_liters'] < 0:
            raise serializers.ValidationError("Fuel used cannot be negative")

        return data


class TransportRequestSerializer(serializers.ModelSerializer):
    """Basic serializer for transport requests (list view)"""
    requestor_name = serializers.CharField(source='requestor.get_full_name', read_only=True)
    requestor_email = serializers.EmailField(source='requestor.email', read_only=True)
    segment_count = serializers.SerializerMethodField()

    class Meta:
        model = TransportRequest
        fields = [
            'id', 'requestor', 'requestor_name', 'requestor_email', 'trf',
            'title', 'purpose', 'transport_type', 'status',
            'number_of_passengers', 'vehicle_type', 'estimated_cost',
            'currency', 'segment_count', 'submitted_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'requestor']

    def get_segment_count(self, obj):
        """Get the number of transport segments"""
        return obj.segments.count()

    def validate_number_of_passengers(self, value):
        """Validate number of passengers"""
        if value < 1:
            raise serializers.ValidationError("Number of passengers must be at least 1")
        return value

    def validate_estimated_cost(self, value):
        """Validate estimated cost"""
        if value < 0:
            raise serializers.ValidationError("Estimated cost cannot be negative")
        return value


class TransportRequestDetailSerializer(TransportRequestSerializer):
    """Detailed serializer with nested data for retrieve operations"""
    requestor = UserSerializer(read_only=True)
    segments = TransportSegmentSerializer(many=True, read_only=True)
    approval_steps = TransportApprovalStepSerializer(many=True, read_only=True)
    vehicle_assignments = VehicleAssignmentSerializer(many=True, read_only=True)

    class Meta(TransportRequestSerializer.Meta):
        fields = TransportRequestSerializer.Meta.fields + [
            'passenger_names', 'special_requirements', 'additional_comments',
            'additional_data', 'segments', 'approval_steps', 'vehicle_assignments'
        ]


class TransportRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating transport requests"""
    segments = TransportSegmentSerializer(many=True, required=False)

    class Meta:
        model = TransportRequest
        fields = [
            'trf', 'title', 'purpose', 'transport_type',
            'number_of_passengers', 'passenger_names', 'vehicle_type',
            'special_requirements', 'estimated_cost', 'currency',
            'additional_comments', 'additional_data', 'segments'
        ]

    def validate(self, data):
        """Validate transport request data"""
        # Validate passenger names match number of passengers
        if data.get('passenger_names'):
            names = [name.strip() for name in data['passenger_names'].split(',')]
            if len(names) != data.get('number_of_passengers', 1):
                raise serializers.ValidationError(
                    f"Number of passenger names ({len(names)}) must match "
                    f"number of passengers ({data.get('number_of_passengers', 1)})"
                )

        return data

    def create(self, validated_data):
        """Create transport request with segments"""
        segments_data = validated_data.pop('segments', [])

        # Create the transport request
        transport_request = TransportRequest.objects.create(**validated_data)

        # Create segments
        for segment_data in segments_data:
            TransportSegment.objects.create(
                transport_request=transport_request,
                **segment_data
            )

        return transport_request


class TransportRequestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating transport requests"""

    class Meta:
        model = TransportRequest
        fields = [
            'title', 'purpose', 'transport_type', 'number_of_passengers',
            'passenger_names', 'vehicle_type', 'special_requirements',
            'estimated_cost', 'currency', 'additional_comments', 'additional_data'
        ]

    def validate(self, data):
        """Validate update - cannot update submitted/approved requests"""
        instance = self.instance
        if instance.status not in ['Draft', 'Rejected']:
            raise serializers.ValidationError(
                f"Cannot update transport request with status '{instance.status}'"
            )

        # Validate passenger names match number of passengers
        number_of_passengers = data.get('number_of_passengers', instance.number_of_passengers)
        passenger_names = data.get('passenger_names', instance.passenger_names)

        if passenger_names:
            names = [name.strip() for name in passenger_names.split(',')]
            if len(names) != number_of_passengers:
                raise serializers.ValidationError(
                    f"Number of passenger names ({len(names)}) must match "
                    f"number of passengers ({number_of_passengers})"
                )

        return data


class ApprovalActionSerializer(serializers.Serializer):
    """Serializer for approval actions (approve/reject)"""
    comments = serializers.CharField(required=False, allow_blank=True)

    def validate_comments(self, value):
        """Validate comments are provided for rejection"""
        action_type = self.context.get('action_type')
        if action_type == 'reject' and not value:
            raise serializers.ValidationError(
                "Comments are required when rejecting a transport request"
            )
        return value
