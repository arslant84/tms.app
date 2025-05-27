from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import FlightBooking, HotelBooking, BookingStatus
from trf.models import TravelRequestForm

User = get_user_model()


class FlightBookingSerializer(serializers.ModelSerializer):
    user_id = serializers.ReadOnlyField()
    trf_id = serializers.ReadOnlyField()
    
    class Meta:
        model = FlightBooking
        fields = [
            'id', 'trf', 'trf_id', 'user', 'user_id', 'airline', 'flight_number',
            'departure_airport', 'arrival_airport', 'departure_time', 'arrival_time',
            'booking_class', 'status', 'cost', 'booking_reference', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FlightBookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlightBooking
        fields = [
            'trf', 'airline', 'flight_number', 'departure_airport', 'arrival_airport',
            'departure_time', 'arrival_time', 'booking_class', 'cost', 'booking_reference'
        ]
    
    def validate_trf(self, value):
        if value.status != 'APPROVED':
            raise serializers.ValidationError("Can only book flights for approved TRFs.")
        return value
    
    def create(self, validated_data):
        user = self.context['request'].user
        booking = FlightBooking.objects.create(user=user, **validated_data)
        return booking


class HotelBookingSerializer(serializers.ModelSerializer):
    user_id = serializers.ReadOnlyField()
    trf_id = serializers.ReadOnlyField()
    
    class Meta:
        model = HotelBooking
        fields = [
            'id', 'trf', 'trf_id', 'user', 'user_id', 'hotel_name', 'location',
            'check_in_date', 'check_out_date', 'room_type', 'number_of_rooms',
            'status', 'cost', 'booking_reference', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class HotelBookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelBooking
        fields = [
            'trf', 'hotel_name', 'location', 'check_in_date', 'check_out_date',
            'room_type', 'number_of_rooms', 'cost', 'booking_reference'
        ]
    
    def validate_trf(self, value):
        if value.status != 'APPROVED':
            raise serializers.ValidationError("Can only book hotels for approved TRFs.")
        return value
    
    def create(self, validated_data):
        user = self.context['request'].user
        booking = HotelBooking.objects.create(user=user, **validated_data)
        return booking


class BookingStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=BookingStatus.choices)
    
    def validate_status(self, value):
        # Add any validation rules for status transitions
        return value
