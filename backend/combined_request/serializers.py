"""
Combined Request Serializers

This module will contain the DRF serializers for the Combined Request API.
To be implemented in Phase 2.
"""

from rest_framework import serializers

from .models import (
    CombinedRequest,
    CombinedRequestApprovalStep,
    CombinedRequestDocument,
    CombinedRequestItinerary,
    CombinedRequestPassport,
    CombinedRequestTransportSegment,
)


class CombinedRequestPassportSerializer(serializers.ModelSerializer):
    """Serializer for passport details."""

    class Meta:
        model = CombinedRequestPassport
        fields = [
            "id",
            "full_name",
            "passport_number",
            "nationality",
            "date_of_birth",
            "place_of_birth",
            "issue_date",
            "expiry_date",
            "passport_file",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CombinedRequestItinerarySerializer(serializers.ModelSerializer):
    """Serializer for itinerary segments."""

    # Allow blank so that partially-filled segments don't block the entire update
    from_location = serializers.CharField(max_length=255, allow_blank=True, default="")
    to_location = serializers.CharField(max_length=255, allow_blank=True, default="")

    class Meta:
        model = CombinedRequestItinerary
        fields = [
            "id",
            "segment_order",
            "segment_date",
            "day_of_week",
            "from_location",
            "to_location",
            "departure_time",
            "arrival_time",
            "mode_of_travel",
            "flight_number",
            "flight_class",
            "purpose",
            "remarks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CombinedRequestTransportSegmentSerializer(serializers.ModelSerializer):
    """Serializer for transport segments."""

    class Meta:
        model = CombinedRequestTransportSegment
        fields = [
            "id",
            "segment_order",
            "day_of_week",
            "transport_type",
            "pickup_location",
            "dropoff_location",
            "pickup_date",
            "pickup_time",
            "passengers",
            "vehicle_type_preference",
            "notes",
            "vehicle_number",
            "driver_name",
            "driver_contact",
            "segment_cost",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CombinedRequestDocumentSerializer(serializers.ModelSerializer):
    """Serializer for documents."""

    uploaded_by_name = serializers.SerializerMethodField()

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.name or obj.uploaded_by.username
        return None

    class Meta:
        model = CombinedRequestDocument
        fields = [
            "id",
            "document_type",
            "module",
            "file",
            "file_name",
            "description",
            "uploaded_by",
            "uploaded_by_name",
            "uploaded_at",
        ]
        read_only_fields = ["id", "uploaded_at"]


class CombinedRequestApprovalStepSerializer(serializers.ModelSerializer):
    """Serializer for approval steps."""

    approver_name = serializers.CharField(
        source="approver.name", read_only=True, allow_null=True
    )

    class Meta:
        model = CombinedRequestApprovalStep
        fields = [
            "id",
            "step_order",
            "step_name",
            "step_role",
            "module",
            "approver",
            "approver_name",
            "status",
            "comments",
            "actioned_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CombinedRequestListSerializer(serializers.ModelSerializer):
    """Serializer for list views - minimal fields for performance."""

    requestor_email = serializers.CharField(source="requestor.email", read_only=True)
    included_modules = serializers.SerializerMethodField()

    class Meta:
        model = CombinedRequest
        fields = [
            "id",
            "request_number",
            "requestor_name",
            "requestor_email",
            "staff_id",
            "department",
            "status",
            "included_modules",
            "travel_purpose",
            "transport_purpose",
            "departure_date",
            "return_date",
            "destination_city",
            "submitted_at",
            "created_at",
        ]

    def get_included_modules(self, obj):
        return obj.get_included_modules()


class CombinedRequestDetailSerializer(serializers.ModelSerializer):
    """Serializer for detail views - includes all nested data."""

    requestor_email = serializers.CharField(source="requestor.email", read_only=True)
    included_modules = serializers.SerializerMethodField()
    passports = CombinedRequestPassportSerializer(many=True, read_only=True)
    itinerary_segments = CombinedRequestItinerarySerializer(many=True, read_only=True)
    transport_segments = CombinedRequestTransportSegmentSerializer(
        many=True, read_only=True
    )
    documents = CombinedRequestDocumentSerializer(many=True, read_only=True)
    approval_steps = CombinedRequestApprovalStepSerializer(many=True, read_only=True)

    class Meta:
        model = CombinedRequest
        fields = "__all__"

    def get_included_modules(self, obj):
        return obj.get_included_modules()


class CombinedRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new combined requests."""

    passports = CombinedRequestPassportSerializer(many=True, required=False)
    itinerary_segments = CombinedRequestItinerarySerializer(many=True, required=False)
    transport_segments = CombinedRequestTransportSegmentSerializer(
        many=True, required=False
    )

    class Meta:
        model = CombinedRequest
        exclude = [
            "request_number",
            "requestor",
            "status",
            "submitted_at",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        """Create combined request with nested objects."""
        passports_data = validated_data.pop("passports", [])
        itinerary_data = validated_data.pop("itinerary_segments", [])
        transport_data = validated_data.pop("transport_segments", [])

        # Create the main request
        combined_request = CombinedRequest.objects.create(**validated_data)

        # Create nested objects
        for passport_data in passports_data:
            CombinedRequestPassport.objects.create(
                combined_request=combined_request, **passport_data
            )

        for itinerary in itinerary_data:
            CombinedRequestItinerary.objects.create(
                combined_request=combined_request, **itinerary
            )

        for transport in transport_data:
            CombinedRequestTransportSegment.objects.create(
                combined_request=combined_request, **transport
            )

        return combined_request


class CombinedRequestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating combined requests — replaces nested objects on each save."""

    passports = CombinedRequestPassportSerializer(many=True, required=False)
    itinerary_segments = CombinedRequestItinerarySerializer(many=True, required=False)
    transport_segments = CombinedRequestTransportSegmentSerializer(
        many=True, required=False
    )

    class Meta:
        model = CombinedRequest
        exclude = ["request_number", "requestor", "created_at", "updated_at"]
        read_only_fields = ["status", "submitted_at"]

    def update(self, instance, validated_data):
        passports_data = validated_data.pop("passports", None)
        itinerary_data = validated_data.pop("itinerary_segments", None)
        transport_data = validated_data.pop("transport_segments", None)

        # Update all flat fields
        instance = super().update(instance, validated_data)

        # Replace nested objects only when the caller supplies them
        if passports_data is not None:
            instance.passports.all().delete()
            for p in passports_data:
                CombinedRequestPassport.objects.create(combined_request=instance, **p)

        if itinerary_data is not None:
            instance.itinerary_segments.all().delete()
            for seg in itinerary_data:
                CombinedRequestItinerary.objects.create(
                    combined_request=instance, **seg
                )

        if transport_data is not None:
            instance.transport_segments.all().delete()
            for seg in transport_data:
                CombinedRequestTransportSegment.objects.create(
                    combined_request=instance, **seg
                )

        return instance
