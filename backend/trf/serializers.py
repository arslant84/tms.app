from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    TravelRequest,
    TrfAdvanceAmountRequestedItem,
    TrfAdvanceBankDetail,
    TrfApprovalStep,
    TrfDailyMealSelection,
    TrfFlightBooking,
    TrfItinerarySegment,
    TrfMealProvision,
    TrfPassportDetail
)

User = get_user_model()


# =============== NESTED/RELATED SERIALIZERS ===============

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
    has_flight_booking = serializers.SerializerMethodField()
    flight_details = serializers.SerializerMethodField()
    overseas_travel_details = serializers.SerializerMethodField()
    home_leave_details = serializers.SerializerMethodField()
    domestic_travel_details = serializers.SerializerMethodField()

    class Meta:
        model = TravelRequest
        fields = [
            'id', 'request_number', 'requestor_name', 'staff_id', 'department', 'position',
            'cost_center', 'tel_email', 'email', 'travel_type', 'status',
            'purpose', 'estimated_cost', 'additional_comments',
            'external_full_name', 'external_organization',
            'external_ref_to_authority_letter', 'external_cost_center',
            'submitted_at', 'created_at', 'updated_at', 'additional_data',
            'has_flight_booking', 'flight_details', 'overseas_travel_details',
            'home_leave_details', 'domestic_travel_details'
        ]
        read_only_fields = ['id', 'request_number', 'submitted_at', 'created_at', 'updated_at']

    def get_has_flight_booking(self, obj):
        """Check if TRF has any flight bookings from bookings app"""
        return obj.flight_bookings.exists()

    def get_flight_details(self, obj):
        """Get flight booking details if exists"""
        flight_booking = obj.flight_bookings.first()
        if flight_booking:
            return {
                'id': flight_booking.id,
                'airline': flight_booking.airline,
                'flightNumber': flight_booking.flight_number,
                'departureLocation': flight_booking.departure_airport,
                'arrivalLocation': flight_booking.arrival_airport,
                'departureDate': flight_booking.departure_time.isoformat() if flight_booking.departure_time else None,
                'arrivalDate': flight_booking.arrival_time.isoformat() if flight_booking.arrival_time else None,
                'bookingReference': flight_booking.booking_reference,
                'pnr': flight_booking.booking_reference,
                'status': flight_booking.status,
                'remarks': flight_booking.notes
            }
        return None

    def get_overseas_travel_details(self, obj):
        """Get overseas travel details with itinerary"""
        if obj.travel_type == 'Overseas':
            itinerary_segments = obj.trfitinerarysegment_set.all()
            return {
                'itinerary': [
                    {
                        'from_location': seg.from_location,
                        'from': seg.from_location,
                        'to_location': seg.to_location,
                        'to': seg.to_location,
                        'departure_date': seg.segment_date.isoformat() if seg.segment_date else None,
                        'date': seg.segment_date.isoformat() if seg.segment_date else None,
                        'etd': seg.departure_time,
                        'eta': seg.arrival_time,
                        'departure_time': seg.departure_time,
                        'arrival_time': seg.arrival_time
                    }
                    for seg in itinerary_segments
                ]
            }
        return None

    def get_home_leave_details(self, obj):
        """Get home leave details with itinerary"""
        if obj.travel_type == 'Home Leave Passage':
            itinerary_segments = obj.trfitinerarysegment_set.all()
            return {
                'itinerary': [
                    {
                        'from_location': seg.from_location,
                        'from': seg.from_location,
                        'to_location': seg.to_location,
                        'to': seg.to_location,
                        'departure_date': seg.segment_date.isoformat() if seg.segment_date else None,
                        'date': seg.segment_date.isoformat() if seg.segment_date else None,
                        'etd': seg.departure_time,
                        'eta': seg.arrival_time,
                        'departure_time': seg.departure_time,
                        'arrival_time': seg.arrival_time
                    }
                    for seg in itinerary_segments
                ]
            }
        return None

    def get_domestic_travel_details(self, obj):
        """Get domestic travel details with itinerary"""
        if obj.travel_type == 'Domestic':
            itinerary_segments = obj.trfitinerarysegment_set.all()
            return {
                'itinerary': [
                    {
                        'from_location': seg.from_location,
                        'from': seg.from_location,
                        'to_location': seg.to_location,
                        'to': seg.to_location,
                        'departure_date': seg.segment_date.isoformat() if seg.segment_date else None,
                        'date': seg.segment_date.isoformat() if seg.segment_date else None,
                        'etd': seg.departure_time,
                        'eta': seg.arrival_time,
                        'departure_time': seg.departure_time,
                        'arrival_time': seg.arrival_time
                    }
                    for seg in itinerary_segments
                ]
            }
        return None

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
    advance_amounts = TrfAdvanceAmountRequestedItemSerializer(
        many=True, read_only=True, source='trfadvanceamountrequesteditem_set'
    )
    bank_detail = TrfAdvanceBankDetailSerializer(
        read_only=True, source='trfadvancebankdetail'
    )
    approval_steps = TrfApprovalStepSerializer(
        many=True, read_only=True, source='trfapprovalstep_set'
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

    # Add nested travel details for Angular frontend compatibility
    domesticTravelDetails = serializers.SerializerMethodField()
    overseasTravelDetails = serializers.SerializerMethodField()
    externalPartiesTravelDetails = serializers.SerializerMethodField()
    externalPartyRequestorInfo = serializers.SerializerMethodField()

    class Meta:
        model = TravelRequest
        fields = [
            'id', 'request_number', 'requestor_name', 'staff_id', 'department', 'position',
            'cost_center', 'tel_email', 'email', 'travel_type', 'status',
            'purpose', 'estimated_cost', 'additional_comments',
            'external_full_name', 'external_organization',
            'external_ref_to_authority_letter', 'external_cost_center',
            'submitted_at', 'created_at', 'updated_at', 'additional_data',
            'advance_amounts', 'bank_detail',
            'approval_steps', 'daily_meals',
            'flight_bookings', 'itinerary_segments', 'meal_provisions',
            'passport_details',
            'domesticTravelDetails', 'overseasTravelDetails',
            'externalPartiesTravelDetails', 'externalPartyRequestorInfo'
        ]
        read_only_fields = ['id', 'request_number', 'submitted_at', 'created_at', 'updated_at']

    def get_domesticTravelDetails(self, obj):
        """Get domestic travel details with itinerary"""
        if obj.travel_type == 'Domestic':
            itinerary_segments = obj.trfitinerarysegment_set.all()
            daily_meals = obj.trfdailymealselection_set.all()
            return {
                'purpose': obj.purpose,
                'itinerary': [
                    {
                        'id': seg.id,
                        'date': seg.segment_date.isoformat() if seg.segment_date else None,
                        'day': seg.day_of_week,
                        'from': seg.from_location,
                        'to': seg.to_location,
                        'etd': seg.departure_time,
                        'eta': seg.arrival_time,
                        'flightNumber': seg.flight_number,
                        'remarks': seg.remarks
                    }
                    for seg in itinerary_segments
                ],
                'mealProvision': {
                    'dailyMealSelections': [
                        {
                            'id': meal.id,
                            'meal_date': meal.meal_date.isoformat() if meal.meal_date else None,
                            'breakfast': meal.breakfast,
                            'lunch': meal.lunch,
                            'dinner': meal.dinner,
                            'supper': meal.supper,
                            'refreshment': meal.refreshment
                        }
                        for meal in daily_meals
                    ]
                }
            }
        return None

    def get_overseasTravelDetails(self, obj):
        """Get overseas/home leave travel details with itinerary"""
        if obj.travel_type in ['Overseas', 'Home Leave Passage']:
            itinerary_segments = obj.trfitinerarysegment_set.all()
            advance_amounts = obj.trfadvanceamountrequesteditem_set.all()
            try:
                bank_detail = obj.trfadvancebankdetail
                bank_details_data = {
                    'bankName': bank_detail.bank_name,
                    'accountNumber': bank_detail.account_number,
                    'accountName': bank_detail.account_name,
                    'swiftCode': bank_detail.swift_code,
                    'iban': bank_detail.iban,
                    'branchAddress': bank_detail.branch_address,
                    'currency': bank_detail.currency,
                    'amount': str(bank_detail.amount) if bank_detail.amount else None
                }
            except TrfAdvanceBankDetail.DoesNotExist:
                bank_details_data = None

            return {
                'purpose': obj.purpose,
                'itinerary': [
                    {
                        'id': seg.id,
                        'date': seg.segment_date.isoformat() if seg.segment_date else None,
                        'day': seg.day_of_week,
                        'from': seg.from_location,
                        'to': seg.to_location,
                        'etd': seg.departure_time,
                        'eta': seg.arrival_time,
                        'flightNumber': seg.flight_number,
                        'remarks': seg.remarks
                    }
                    for seg in itinerary_segments
                ],
                'advanceBankDetails': bank_details_data,
                'advanceAmountRequested': [
                    {
                        'id': amt.id,
                        'dateFrom': amt.date_from.isoformat() if amt.date_from else None,
                        'dateTo': amt.date_to.isoformat() if amt.date_to else None,
                        'lh': str(amt.lh) if amt.lh else None,
                        'ma': str(amt.ma) if amt.ma else None,
                        'oa': str(amt.oa) if amt.oa else None,
                        'tr': str(amt.tr) if amt.tr else None,
                        'oe': str(amt.oe) if amt.oe else None,
                        'usd': str(amt.usd) if amt.usd else None,
                        'remarks': amt.remarks
                    }
                    for amt in advance_amounts
                ]
            }
        return None

    def get_externalPartiesTravelDetails(self, obj):
        """Get external parties travel details with itinerary"""
        if obj.travel_type == 'External Parties':
            itinerary_segments = obj.trfitinerarysegment_set.all()
            return {
                'purpose': obj.purpose,
                'itinerary': [
                    {
                        'id': seg.id,
                        'date': seg.segment_date.isoformat() if seg.segment_date else None,
                        'day': seg.day_of_week,
                        'from': seg.from_location,
                        'to': seg.to_location,
                        'etd': seg.departure_time,
                        'eta': seg.arrival_time,
                        'flightNumber': seg.flight_number,
                        'remarks': seg.remarks
                    }
                    for seg in itinerary_segments
                ]
            }
        return None

    def get_externalPartyRequestorInfo(self, obj):
        """Get external party requestor information"""
        if obj.travel_type == 'External Parties':
            return {
                'externalFullName': obj.external_full_name,
                'externalOrganization': obj.external_organization,
                'externalRefToAuthorityLetter': obj.external_ref_to_authority_letter,
                'externalCostCenter': obj.external_cost_center
            }
        return None

    def to_representation(self, instance):
        """Exclude passport_details for Home Leave Passage"""
        representation = super().to_representation(instance)

        # Remove passport_details from Home Leave Passage TSRs
        if instance.travel_type == 'Home Leave Passage':
            representation.pop('passport_details', None)

        return representation


class TravelRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Travel Requests"""

    class Meta:
        model = TravelRequest
        fields = [
            'id', 'requestor_name', 'staff_id', 'department', 'position',
            'cost_center', 'tel_email', 'email', 'travel_type', 'status', 'purpose',
            'estimated_cost', 'additional_comments', 'external_full_name',
            'external_organization', 'external_ref_to_authority_letter',
            'external_cost_center', 'additional_data'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        # Set default status to Draft only if status not provided
        if 'status' not in validated_data:
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
            'external_cost_center', 'additional_data', 'status'
        ]

    def validate(self, attrs):
        """Allow editing for Draft, Rejected, or any Pending status"""
        instance = getattr(self, 'instance', None)
        if instance:
            current_status = instance.status
            # Allow editing if status is Draft, Rejected, or starts with Pending
            if not (current_status == 'Draft' or
                    current_status == 'Rejected' or
                    current_status.startswith('Pending')):
                raise serializers.ValidationError(
                    f"This TRF cannot be edited because its status is '{current_status}'. "
                    "Only Draft, Rejected, or Pending TRFs can be edited."
                )
        return attrs

    def validate_status(self, value):
        """Allow setting status to Draft, Rejected, or any Pending status during update"""
        # Allow Draft, Rejected, or any status starting with Pending
        if not (value == 'Draft' or
                value == 'Rejected' or
                value.startswith('Pending')):
            raise serializers.ValidationError(
                f"Status can only be set to 'Draft', 'Rejected', or 'Pending...' statuses during update. "
                f"Cannot set status to '{value}'."
            )
        return value


class ApprovalActionSerializer(serializers.Serializer):
    """Serializer for approval actions (approve/reject)"""
    comments = serializers.CharField(required=False, allow_blank=True)
    step_role = serializers.CharField(required=True)

    # Note: step_role validation is handled by WorkflowEngine
    # which checks if the user is authorized for the current workflow step
