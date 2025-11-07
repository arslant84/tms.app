from rest_framework import serializers
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
        """Ensure capacity is positive"""
        if value < 1:
            raise serializers.ValidationError("Capacity must be at least 1")
        return value

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

    class Meta:
        model = AccommodationRequest
        fields = [
            'id', 'request_number', 'requestor_name', 'staff_id', 'department', 'position',
            'cost_center', 'tel_email', 'email', 'status', 'estimated_cost',
            'additional_comments', 'submitted_at', 'created_at', 'updated_at',
            'additional_data'
        ]
        read_only_fields = ['id', 'request_number', 'created_at', 'updated_at']

    def validate_status(self, value):
        """Validate request status"""
        valid_statuses = ['Draft', 'Pending', 'Approved', 'Rejected', 'Cancelled']
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(valid_statuses)}"
            )
        return value

    def validate_email(self, value):
        """Validate email format"""
        if value and '@' not in value:
            raise serializers.ValidationError("Invalid email format")
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
