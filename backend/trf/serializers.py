from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    TravelRequest,
    TrfAccommodationDetail,
    TrfAdvanceAmountRequestedItem,
    TrfAdvanceBankDetail,
    TrfApprovalStep,
    TrfCompanyTransportDetail,
    TrfDailyMealSelection,
    TrfFlightBooking,
    TrfItinerarySegment,
    TrfMealProvision,
    TrfPassportDetail
)

User = get_user_model()


# =============== NESTED/RELATED SERIALIZERS ===============

class TrfAccommodationDetailSerializer(serializers.ModelSerializer):
    """Serializer for TRF Accommodation Details"""

    class Meta:
        model = TrfAccommodationDetail
        fields = [
            'id', 'trf', 'check_in_date', 'check_out_date', 'accommodation_type',
            'location', 'address', 'place_of_stay', 'estimated_cost_per_night',
            'check_in_time', 'check_out_time', 'other_type_description', 'remarks',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TrfAdvanceAmountRequestedItemSerializer(serializers.ModelSerializer):
    """Serializer for TRF Advance Amount Requested Items"""

    class Meta:
        model = TrfAdvanceAmountRequestedItem
        fields = [
            'id', 'trf', 'date_from', 'date_to', 'lh', 'ma', 'oa', 'tr', 'oe',
            'usd', 'remarks', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TrfAdvanceBankDetailSerializer(serializers.ModelSerializer):
    """Serializer for TRF Advance Bank Details"""

    class Meta:
        model = TrfAdvanceBankDetail
        fields = [
            'id', 'trf', 'bank_name', 'account_number', 'account_name',
            'swift_code', 'iban', 'branch_address', 'currency', 'amount',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TrfApprovalStepSerializer(serializers.ModelSerializer):
    """Serializer for TRF Approval Steps"""

    class Meta:
        model = TrfApprovalStep
        fields = [
            'id', 'trf', 'step_role', 'step_name', 'status', 'step_date',
            'comments', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate_status(self, value):
        """Validate approval status"""
        valid_statuses = ['Pending', 'Approved', 'Rejected', 'In Review']
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(valid_statuses)}"
            )
        return value


class TrfCompanyTransportDetailSerializer(serializers.ModelSerializer):
    """Serializer for TRF Company Transport Details"""

    class Meta:
        model = TrfCompanyTransportDetail
        fields = [
            'id', 'trf', 'transport_date', 'day_of_week', 'from_location',
            'to_location', 'bt_no_required', 'accommodation_type_n', 'address',
            'remarks', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TrfDailyMealSelectionSerializer(serializers.ModelSerializer):
    """Serializer for TRF Daily Meal Selections"""

    class Meta:
        model = TrfDailyMealSelection
        fields = [
            'id', 'trf', 'meal_date', 'breakfast', 'lunch', 'dinner',
            'supper', 'refreshment', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TrfFlightBookingSerializer(serializers.ModelSerializer):
    """Serializer for TRF Flight Bookings"""

    class Meta:
        model = TrfFlightBooking
        fields = [
            'id', 'trf', 'flight_number', 'airline', 'flight_class',
            'departure_location', 'arrival_location', 'departure_date',
            'arrival_date', 'departure_time', 'arrival_time',
            'booking_reference', 'status', 'remarks', 'created_by',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_status(self, value):
        """Validate flight booking status"""
        valid_statuses = ['Pending', 'Confirmed', 'Cancelled', 'Completed']
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(valid_statuses)}"
            )
        return value


class TrfItinerarySegmentSerializer(serializers.ModelSerializer):
    """Serializer for TRF Itinerary Segments"""

    class Meta:
        model = TrfItinerarySegment
        fields = [
            'id', 'trf', 'segment_date', 'day_of_week', 'from_location',
            'to_location', 'departure_time', 'arrival_time', 'flight_number',
            'flight_class', 'purpose', 'remarks', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TrfMealProvisionSerializer(serializers.ModelSerializer):
    """Serializer for TRF Meal Provisions"""

    class Meta:
        model = TrfMealProvision
        fields = [
            'id', 'trf', 'date_from_to', 'breakfast', 'lunch', 'dinner',
            'supper', 'refreshment', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TrfPassportDetailSerializer(serializers.ModelSerializer):
    """Serializer for TRF Passport Details"""

    class Meta:
        model = TrfPassportDetail
        fields = [
            'id', 'trf', 'full_name', 'passport_number', 'nationality',
            'date_of_birth', 'place_of_birth', 'passport_issue_date',
            'passport_expiry_date', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# =============== MAIN TRAVEL REQUEST SERIALIZERS ===============

class TravelRequestSerializer(serializers.ModelSerializer):
    """Main serializer for Travel Requests (list view)"""

    class Meta:
        model = TravelRequest
        fields = [
            'id', 'requestor_name', 'staff_id', 'department', 'position',
            'cost_center', 'tel_email', 'email', 'travel_type', 'status',
            'purpose', 'estimated_cost', 'additional_comments',
            'external_full_name', 'external_organization',
            'external_ref_to_authority_letter', 'external_cost_center',
            'submitted_at', 'created_at', 'updated_at', 'additional_data'
        ]
        read_only_fields = ['id', 'submitted_at', 'created_at', 'updated_at']

    def validate_status(self, value):
        """Validate TRF status"""
        valid_statuses = [
            'Draft', 'Pending Department Focal', 'Pending HOD',
            'Pending Travel Desk', 'Pending Finance', 'Approved',
            'Rejected', 'Cancelled', 'Completed'
        ]
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(valid_statuses)}"
            )
        return value

    def validate_travel_type(self, value):
        """Validate travel type"""
        valid_types = ['Domestic', 'International', 'Local', 'Field Visit']
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Travel type must be one of: {', '.join(valid_types)}"
            )
        return value


class TravelRequestDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Travel Requests with all nested data"""
    accommodation_details = TrfAccommodationDetailSerializer(
        many=True, read_only=True, source='trfaccommodationdetail_set'
    )
    advance_amounts = TrfAdvanceAmountRequestedItemSerializer(
        many=True, read_only=True, source='trfadvanceamountrequesteditem_set'
    )
    bank_detail = TrfAdvanceBankDetailSerializer(
        read_only=True, source='trfadvancebankdetail'
    )
    approval_steps = TrfApprovalStepSerializer(
        many=True, read_only=True, source='trfapprovalstep_set'
    )
    transport_details = TrfCompanyTransportDetailSerializer(
        many=True, read_only=True, source='trfcompanytransportdetail_set'
    )
    daily_meals = TrfDailyMealSelectionSerializer(
        many=True, read_only=True, source='trfdailymealselection_set'
    )
    flight_bookings = TrfFlightBookingSerializer(
        many=True, read_only=True, source='trfflightbooking_set'
    )
    itinerary_segments = TrfItinerarySegmentSerializer(
        many=True, read_only=True, source='trfitinerarysegment_set'
    )
    meal_provisions = TrfMealProvisionSerializer(
        many=True, read_only=True, source='trfmealprovision_set'
    )
    passport_details = TrfPassportDetailSerializer(
        many=True, read_only=True, source='trfpassportdetail_set'
    )

    class Meta:
        model = TravelRequest
        fields = [
            'id', 'requestor_name', 'staff_id', 'department', 'position',
            'cost_center', 'tel_email', 'email', 'travel_type', 'status',
            'purpose', 'estimated_cost', 'additional_comments',
            'external_full_name', 'external_organization',
            'external_ref_to_authority_letter', 'external_cost_center',
            'submitted_at', 'created_at', 'updated_at', 'additional_data',
            'accommodation_details', 'advance_amounts', 'bank_detail',
            'approval_steps', 'transport_details', 'daily_meals',
            'flight_bookings', 'itinerary_segments', 'meal_provisions',
            'passport_details'
        ]
        read_only_fields = ['id', 'submitted_at', 'created_at', 'updated_at']


class TravelRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Travel Requests"""

    class Meta:
        model = TravelRequest
        fields = [
            'requestor_name', 'staff_id', 'department', 'position',
            'cost_center', 'tel_email', 'email', 'travel_type', 'purpose',
            'estimated_cost', 'additional_comments', 'external_full_name',
            'external_organization', 'external_ref_to_authority_letter',
            'external_cost_center', 'additional_data'
        ]

    def create(self, validated_data):
        # Set default status to Draft
        validated_data['status'] = 'Draft'
        return super().create(validated_data)


class TravelRequestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating Travel Requests"""

    class Meta:
        model = TravelRequest
        fields = [
            'requestor_name', 'staff_id', 'department', 'position',
            'cost_center', 'tel_email', 'email', 'travel_type', 'purpose',
            'estimated_cost', 'additional_comments', 'external_full_name',
            'external_organization', 'external_ref_to_authority_letter',
            'external_cost_center', 'additional_data'
        ]

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        if instance and instance.status not in ['Draft', 'Rejected']:
            raise serializers.ValidationError(
                "Only draft or rejected TRFs can be updated."
            )
        return attrs


class ApprovalActionSerializer(serializers.Serializer):
    """Serializer for approval actions (approve/reject)"""
    comments = serializers.CharField(required=False, allow_blank=True)
    step_role = serializers.CharField(required=True)

    def validate_step_role(self, value):
        """Validate step role"""
        valid_roles = [
            'Department Focal', 'HOD', 'Travel Desk', 'Finance',
            'Director', 'Country Director'
        ]
        if value not in valid_roles:
            raise serializers.ValidationError(
                f"Step role must be one of: {', '.join(valid_roles)}"
            )
        return value
