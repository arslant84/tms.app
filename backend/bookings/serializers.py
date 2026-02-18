from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import FlightBooking, HotelBooking, BookingStatus, FlightType, BookingClass
from trf.models import TravelRequest
from accounts.utils import is_module_admin

User = get_user_model()


class FlightBookingSerializer(serializers.ModelSerializer):
    """Serializer for flight bookings with detailed information"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    trf_number = serializers.CharField(source='trf.trf_number', read_only=True)
    booked_by_name = serializers.CharField(source='booked_by.get_full_name', read_only=True, allow_null=True)
    total_cost_display = serializers.DecimalField(source='total_cost', read_only=True, max_digits=10, decimal_places=2)
    route_display = serializers.CharField(source='route', read_only=True)
    number_of_days = serializers.SerializerMethodField()

    class Meta:
        model = FlightBooking
        fields = [
            'id', 'trf', 'trf_number', 'user', 'user_name', 'user_email',
            'flight_type', 'airline', 'airline_code', 'flight_number',
            'departure_airport', 'departure_airport_code', 'arrival_airport', 'arrival_airport_code',
            'departure_time', 'arrival_time', 'departure_terminal', 'arrival_terminal',
            'booking_class', 'seat_number', 'status', 'booking_reference', 'ticket_number',
            'cost', 'currency', 'tax_amount', 'total_cost_display',
            'baggage_allowance', 'carry_on_allowance', 'meal_preference', 'special_requests',
            'booked_by', 'booked_by_name', 'booking_date', 'confirmation_date',
            'ticketing_date', 'cancellation_date', 'cancellation_reason',
            'notes', 'route_display', 'number_of_days',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'booked_by', 'booking_date', 'confirmation_date',
            'ticketing_date', 'cancellation_date', 'created_at', 'updated_at'
        ]

    def get_number_of_days(self, obj):
        """Calculate trip duration in days"""
        return (obj.arrival_time.date() - obj.departure_time.date()).days


class FlightBookingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating flight bookings"""

    class Meta:
        model = FlightBooking
        fields = [
            'trf', 'flight_type', 'airline', 'airline_code', 'flight_number',
            'departure_airport', 'departure_airport_code', 'arrival_airport', 'arrival_airport_code',
            'departure_time', 'arrival_time', 'departure_terminal', 'arrival_terminal',
            'booking_class', 'seat_number', 'booking_reference', 'cost', 'currency', 'tax_amount',
            'baggage_allowance', 'carry_on_allowance', 'meal_preference', 'special_requests', 'notes'
        ]

    def validate_trf(self, value):
        """Validate TRF status"""
        if value.status not in ['APPROVED', 'IN_PROGRESS']:
            raise serializers.ValidationError(
                "Can only book flights for approved or in-progress TRFs."
            )
        return value

    def validate_booking_reference(self, value):
        """Ensure booking reference is unique"""
        if FlightBooking.objects.filter(booking_reference=value).exists():
            raise serializers.ValidationError(
                "A booking with this reference already exists."
            )
        return value

    def validate(self, data):
        """Cross-field validation"""
        if data['departure_time'] >= data['arrival_time']:
            raise serializers.ValidationError({
                'arrival_time': 'Arrival time must be after departure time.'
            })
        return data

    def create(self, validated_data):
        """Create flight booking with current user"""
        user = self.context['request'].user

        # If user has booking admin permissions, they can book for TRF owner
        trf = validated_data['trf']
        if user.is_superuser or is_module_admin(user, 'booking') or is_module_admin(user, 'trf'):
            validated_data['user'] = trf.user
            validated_data['booked_by'] = user
        else:
            validated_data['user'] = user

        return FlightBooking.objects.create(**validated_data)


class FlightBookingUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating flight bookings"""

    class Meta:
        model = FlightBooking
        fields = [
            'airline', 'airline_code', 'flight_number',
            'departure_airport', 'departure_airport_code', 'arrival_airport', 'arrival_airport_code',
            'departure_time', 'arrival_time', 'departure_terminal', 'arrival_terminal',
            'booking_class', 'seat_number', 'booking_reference', 'ticket_number',
            'cost', 'currency', 'tax_amount',
            'baggage_allowance', 'carry_on_allowance', 'meal_preference', 'special_requests', 'notes'
        ]

    def validate(self, data):
        """Cross-field validation"""
        departure_time = data.get('departure_time', self.instance.departure_time)
        arrival_time = data.get('arrival_time', self.instance.arrival_time)

        if departure_time >= arrival_time:
            raise serializers.ValidationError({
                'arrival_time': 'Arrival time must be after departure time.'
            })
        return data


class HotelBookingSerializer(serializers.ModelSerializer):
    """Serializer for hotel bookings with detailed information"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    trf_number = serializers.CharField(source='trf.trf_number', read_only=True)
    booked_by_name = serializers.CharField(source='booked_by.get_full_name', read_only=True, allow_null=True)
    nights = serializers.IntegerField(source='number_of_nights', read_only=True)
    grand_total_display = serializers.DecimalField(source='grand_total', read_only=True, max_digits=10, decimal_places=2)

    class Meta:
        model = HotelBooking
        fields = [
            'id', 'trf', 'trf_number', 'user', 'user_name', 'user_email',
            'hotel_name', 'hotel_chain', 'location', 'address', 'contact_number', 'email',
            'check_in_date', 'check_out_date', 'check_in_time', 'check_out_time',
            'room_type', 'number_of_rooms', 'number_of_guests', 'bed_preference', 'smoking_preference',
            'status', 'booking_reference',
            'cost_per_night', 'total_cost', 'currency', 'tax_amount', 'service_charges', 'grand_total_display',
            'breakfast_included', 'wifi_included', 'parking_included', 'airport_transfer',
            'special_requests', 'dietary_requirements',
            'booked_by', 'booked_by_name', 'booking_date', 'confirmation_date',
            'cancellation_date', 'cancellation_reason',
            'payment_method', 'is_prepaid', 'notes', 'nights',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'booked_by', 'booking_date', 'confirmation_date',
            'cancellation_date', 'created_at', 'updated_at'
        ]


class HotelBookingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating hotel bookings"""

    class Meta:
        model = HotelBooking
        fields = [
            'trf', 'hotel_name', 'hotel_chain', 'location', 'address', 'contact_number', 'email',
            'check_in_date', 'check_out_date', 'check_in_time', 'check_out_time',
            'room_type', 'number_of_rooms', 'number_of_guests', 'bed_preference', 'smoking_preference',
            'booking_reference', 'cost_per_night', 'total_cost', 'currency', 'tax_amount', 'service_charges',
            'breakfast_included', 'wifi_included', 'parking_included', 'airport_transfer',
            'special_requests', 'dietary_requirements', 'payment_method', 'is_prepaid', 'notes'
        ]

    def validate_trf(self, value):
        """Validate TRF status"""
        if value.status not in ['APPROVED', 'IN_PROGRESS']:
            raise serializers.ValidationError(
                "Can only book hotels for approved or in-progress TRFs."
            )
        return value

    def validate_booking_reference(self, value):
        """Ensure booking reference is unique"""
        if HotelBooking.objects.filter(booking_reference=value).exists():
            raise serializers.ValidationError(
                "A booking with this reference already exists."
            )
        return value

    def validate(self, data):
        """Cross-field validation"""
        if data['check_in_date'] >= data['check_out_date']:
            raise serializers.ValidationError({
                'check_out_date': 'Check-out date must be after check-in date.'
            })

        # Validate that total cost makes sense
        nights = (data['check_out_date'] - data['check_in_date']).days
        expected_cost = data['cost_per_night'] * nights * data.get('number_of_rooms', 1)

        if abs(data['total_cost'] - expected_cost) > 1:  # Allow small rounding differences
            raise serializers.ValidationError({
                'total_cost': f'Total cost should be approximately {expected_cost} '
                             f'({data["cost_per_night"]} x {nights} nights x {data.get("number_of_rooms", 1)} rooms)'
            })

        return data

    def create(self, validated_data):
        """Create hotel booking with current user"""
        user = self.context['request'].user

        # If user has booking admin permissions, they can book for TRF owner
        trf = validated_data['trf']
        if user.is_superuser or is_module_admin(user, 'booking') or is_module_admin(user, 'accommodation'):
            validated_data['user'] = trf.user
            validated_data['booked_by'] = user
        else:
            validated_data['user'] = user

        return HotelBooking.objects.create(**validated_data)


class HotelBookingUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating hotel bookings"""

    class Meta:
        model = HotelBooking
        fields = [
            'hotel_name', 'hotel_chain', 'location', 'address', 'contact_number', 'email',
            'check_in_date', 'check_out_date', 'check_in_time', 'check_out_time',
            'room_type', 'number_of_rooms', 'number_of_guests', 'bed_preference', 'smoking_preference',
            'booking_reference', 'cost_per_night', 'total_cost', 'currency', 'tax_amount', 'service_charges',
            'breakfast_included', 'wifi_included', 'parking_included', 'airport_transfer',
            'special_requests', 'dietary_requirements', 'payment_method', 'is_prepaid', 'notes'
        ]

    def validate(self, data):
        """Cross-field validation"""
        check_in = data.get('check_in_date', self.instance.check_in_date)
        check_out = data.get('check_out_date', self.instance.check_out_date)

        if check_in >= check_out:
            raise serializers.ValidationError({
                'check_out_date': 'Check-out date must be after check-in date.'
            })

        return data


class BookingStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating booking status"""
    status = serializers.ChoiceField(choices=BookingStatus.choices)
    reason = serializers.CharField(required=False, allow_blank=True, help_text="Reason for status change")

    def validate_status(self, value):
        """Validate status transitions"""
        instance = self.context.get('instance')
        if not instance:
            return value

        # Define valid transitions
        valid_transitions = {
            BookingStatus.PENDING: [BookingStatus.REQUESTED, BookingStatus.CANCELLED],
            BookingStatus.REQUESTED: [BookingStatus.CONFIRMED, BookingStatus.CANCELLED],
            BookingStatus.CONFIRMED: [BookingStatus.TICKETED, BookingStatus.CANCELLED],
            BookingStatus.TICKETED: [BookingStatus.CANCELLED, BookingStatus.NO_SHOW, BookingStatus.REFUNDED],
            BookingStatus.CANCELLED: [BookingStatus.REFUNDED],
        }

        current_status = instance.status
        if value != current_status and value not in valid_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f"Cannot transition from {current_status} to {value}"
            )

        return value


class FlightTicketSerializer(serializers.Serializer):
    """Serializer for issuing flight tickets"""
    ticket_number = serializers.CharField(max_length=50, required=True)

    def validate_ticket_number(self, value):
        """Validate ticket number format"""
        if not value or len(value) < 5:
            raise serializers.ValidationError("Invalid ticket number format")
        return value


class BookingStatsSerializer(serializers.Serializer):
    """Serializer for booking statistics"""
    total_bookings = serializers.IntegerField()
    pending_bookings = serializers.IntegerField()
    confirmed_bookings = serializers.IntegerField()
    cancelled_bookings = serializers.IntegerField()
    total_flight_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_hotel_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    by_status = serializers.DictField()
    by_airline = serializers.DictField(required=False)
    by_hotel = serializers.DictField(required=False)
