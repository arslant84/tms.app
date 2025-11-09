from rest_framework import serializers
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import AccommodationStaffHouse, AccommodationRoom, AccommodationRequest, AccommodationBooking
from accounts.serializers import UserSerializer
# from trf.serializers import TravelRequestSerializer  # TODO: Enable after TRF serializers are created


class AccommodationStaffHouseSerializer(serializers.ModelSerializer):
    """Serializer for Staff House entities"""

    class Meta:
        model = AccommodationStaffHouse
        fields = [
            'id', 'name', 'location', 'address', 'description',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AccommodationRoomSerializer(serializers.ModelSerializer):
    """Serializer for Room entities"""
    staff_house_name = serializers.CharField(source='staff_house.name', read_only=True)

    class Meta:
        model = AccommodationRoom
        fields = [
            'id', 'staff_house', 'staff_house_name', 'name', 'room_type',
            'capacity', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_capacity(self, value):
        """SECURITY: Ensure capacity is within reasonable range"""
        if value < 1:
            raise serializers.ValidationError("Capacity must be at least 1")
        if value > 20:
            raise serializers.ValidationError("Capacity must be 20 or less")
        return value

    def validate_name(self, value):
        """SECURITY: Validate room name length"""
        if len(str(value)) > 100:
            raise serializers.ValidationError("Room name too long (max 100 characters)")
        return value.strip()

    def validate_status(self, value):
        """Validate room status"""
        valid_statuses = ['Available', 'Occupied', 'Maintenance', 'Reserved']
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(valid_statuses)}"
            )
        return value


class AccommodationRequestSerializer(serializers.ModelSerializer):
    """Serializer for Accommodation Requests"""
    trf_request_number = serializers.CharField(source='trf.request_number', read_only=True, allow_null=True)

    class Meta:
        model = AccommodationRequest
        fields = [
            'id', 'request_number', 'requestor_name', 'staff_id', 'department', 'position',
            'cost_center', 'tel_email', 'email', 'trf', 'trf_request_number', 'status',
            'additional_comments', 'submitted_at', 'created_at', 'updated_at',
            'additional_data'
        ]
        read_only_fields = ['id', 'request_number', 'trf_request_number', 'created_at', 'updated_at']

    def validate_status(self, value):
        """Validate request status"""
        valid_statuses = ['Draft', 'Pending', 'Approved', 'Rejected', 'Cancelled']
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(valid_statuses)}"
            )
        return value

    def validate_email(self, value):
        """SECURITY: Validate email format and length"""
        if value:
            if '@' not in value or '.' not in value.split('@')[-1]:
                raise serializers.ValidationError("Invalid email format")
            if len(value) > 255:
                raise serializers.ValidationError("Email too long (max 255 characters)")
        return value

    def validate_requestor_name(self, value):
        """SECURITY: Validate requestor name length"""
        if len(str(value)) > 200:
            raise serializers.ValidationError("Requestor name too long (max 200 characters)")
        return value.strip()

    def validate_additional_comments(self, value):
        """SECURITY: Validate comments length"""
        if value and len(str(value)) > 2000:
            raise serializers.ValidationError("Comments too long (max 2000 characters)")
        return value

    def validate_additional_data(self, value):
        """SECURITY: Validate additional_data structure and size"""
        if value:
            # Ensure it's a dictionary
            if not isinstance(value, dict):
                raise serializers.ValidationError("additional_data must be a JSON object")

            # Validate common fields in additional_data
            if 'location' in value and len(str(value['location'])) > 200:
                raise serializers.ValidationError("Location too long (max 200 characters)")

            if 'number_of_guests' in value:
                num_guests = value['number_of_guests']
                if not isinstance(num_guests, (int, float)) or num_guests < 1:
                    raise serializers.ValidationError("number_of_guests must be at least 1")
                if num_guests > 100:
                    raise serializers.ValidationError("number_of_guests must be 100 or less")

        return value


class AccommodationBookingSerializer(serializers.ModelSerializer):
    """Serializer for Accommodation Bookings"""
    staff_house_name = serializers.CharField(source='staff_house.name', read_only=True)
    room_name = serializers.CharField(source='room.name', read_only=True)
    staff_name = serializers.CharField(source='staff.get_full_name', read_only=True)
    trf_reference = serializers.CharField(source='trf.reference_number', read_only=True)

    class Meta:
        model = AccommodationBooking
        fields = [
            'id', 'staff_house', 'staff_house_name', 'room', 'room_name',
            'staff', 'staff_name', 'date', 'trf', 'trf_reference',
            'status', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_status(self, value):
        """Validate booking status"""
        valid_statuses = ['Confirmed', 'Pending', 'Cancelled', 'Completed']
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(valid_statuses)}"
            )
        return value

    def validate(self, data):
        """Check room availability for the given date"""
        room = data.get('room')
        date = data.get('date')

        # Skip validation if we're updating and date/room haven't changed
        if self.instance:
            if room == self.instance.room and date == self.instance.date:
                return data

        # Check if room is already booked for this date
        if room and date:
            existing_booking = AccommodationBooking.objects.filter(
                room=room,
                date=date,
                status__in=['Confirmed', 'Pending']
            ).exclude(
                id=self.instance.id if self.instance else None
            ).exists()

            if existing_booking:
                raise serializers.ValidationError(
                    f"Room {room.name} is already booked for {date}"
                )

        return data


class AccommodationBookingDetailSerializer(AccommodationBookingSerializer):
    """Detailed serializer for Accommodation Bookings with nested data"""
    staff = UserSerializer(read_only=True)
    # trf = TravelRequestSerializer(read_only=True)  # TODO: Enable after TRF serializers are created
    staff_house = AccommodationStaffHouseSerializer(read_only=True)
    room = AccommodationRoomSerializer(read_only=True)

    class Meta(AccommodationBookingSerializer.Meta):
        fields = AccommodationBookingSerializer.Meta.fields


class RoomAvailabilitySerializer(serializers.Serializer):
    """Serializer for checking room availability"""
    staff_house = serializers.IntegerField(required=True)
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)

    def validate(self, data):
        """Ensure end_date is after start_date"""
        if data['end_date'] < data['start_date']:
            raise serializers.ValidationError("end_date must be after start_date")
        return data
