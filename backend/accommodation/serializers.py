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
    tsr_departure_date = serializers.SerializerMethodField()
    tsr_return_date = serializers.SerializerMethodField()

    class Meta:
        model = AccommodationRequest
        fields = [
            'id', 'request_number', 'requestor_name', 'staff_id', 'department', 'position',
            'cost_center', 'tel_email', 'email', 'trf', 'trf_request_number', 'status',
            'additional_comments', 'submitted_at', 'created_at', 'updated_at',
            'additional_data', 'tsr_departure_date', 'tsr_return_date'
        ]
        read_only_fields = ['id', 'request_number', 'trf_request_number', 'created_at', 'updated_at']

    def get_tsr_departure_date(self, obj):
        """Extract departure date from TSR itinerary segments"""
        if not obj.trf:
            return None

        try:
            # Check if the trf object has the related manager
            if not hasattr(obj.trf, 'trfitinerarysegment_set'):
                return None

            # Get first itinerary segment's date as departure date
            first_segment = obj.trf.trfitinerarysegment_set.order_by('segment_date').first()
            if first_segment and first_segment.segment_date:
                return first_segment.segment_date.isoformat()
        except Exception as e:
            print(f"Error getting TSR departure date for request {obj.id}: {e}")
            import traceback
            traceback.print_exc()

        return None

    def get_tsr_return_date(self, obj):
        """Extract return date from TSR itinerary segments"""
        if not obj.trf:
            return None

        try:
            # Check if the trf object has the related manager
            if not hasattr(obj.trf, 'trfitinerarysegment_set'):
                return None

            # Get last itinerary segment's date as return date
            last_segment = obj.trf.trfitinerarysegment_set.order_by('-segment_date').first()
            if last_segment and last_segment.segment_date:
                return last_segment.segment_date.isoformat()
        except Exception as e:
            print(f"Error getting TSR return date for request {obj.id}: {e}")
            import traceback
            traceback.print_exc()

        return None

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

    def validate_trf(self, value):
        """Validate that TSR can only be linked to one accommodation request"""
        if value:
            # Check if this TSR is already linked to another accommodation request
            existing_request = AccommodationRequest.objects.filter(trf=value).exclude(
                id=self.instance.id if self.instance else None
            ).first()

            if existing_request:
                raise serializers.ValidationError(
                    f"TSR {value.request_number or value.id} is already linked to accommodation request "
                    f"{existing_request.request_number or existing_request.id}. "
                    f"Each TSR can only be linked to one accommodation request."
                )

        return value

    def validate(self, data):
        """Validate that check-in/check-out dates are within TSR itinerary dates"""
        trf = data.get('trf') or (self.instance.trf if self.instance else None)
        additional_data = data.get('additional_data') or (self.instance.additional_data if self.instance else {})

        # Only validate if TSR is linked and check-in/check-out dates are provided
        if trf and additional_data and isinstance(additional_data, dict):
            # Check for both field name variations (requested_check_in_date and check_in_date)
            check_in_date_str = additional_data.get('requested_check_in_date') or additional_data.get('check_in_date')
            check_out_date_str = additional_data.get('requested_check_out_date') or additional_data.get('check_out_date')

            if check_in_date_str and check_out_date_str:
                try:
                    from datetime import datetime
                    check_in_date = datetime.strptime(check_in_date_str, '%Y-%m-%d').date()
                    check_out_date = datetime.strptime(check_out_date_str, '%Y-%m-%d').date()

                    # Get TSR itinerary date range
                    from trf.models import TrfItinerarySegment
                    itinerary_segments = TrfItinerarySegment.objects.filter(
                        trf=trf
                    ).exclude(segment_date__isnull=True).order_by('segment_date')

                    if itinerary_segments.exists():
                        first_segment = itinerary_segments.first()
                        last_segment = itinerary_segments.last()

                        tsr_start_date = first_segment.segment_date
                        tsr_end_date = last_segment.segment_date

                        # Validate check-in date is within TSR date range
                        if check_in_date < tsr_start_date or check_in_date > tsr_end_date:
                            raise serializers.ValidationError({
                                'additional_data': f"Check-in date ({check_in_date_str}) must be within TSR itinerary dates "
                                f"({tsr_start_date.strftime('%Y-%m-%d')} to {tsr_end_date.strftime('%Y-%m-%d')})"
                            })

                        # Validate check-out date is within TSR date range
                        if check_out_date < tsr_start_date or check_out_date > tsr_end_date:
                            raise serializers.ValidationError({
                                'additional_data': f"Check-out date ({check_out_date_str}) must be within TSR itinerary dates "
                                f"({tsr_start_date.strftime('%Y-%m-%d')} to {tsr_end_date.strftime('%Y-%m-%d')})"
                            })

                        # Validate check-out is after check-in
                        if check_out_date < check_in_date:
                            raise serializers.ValidationError({
                                'additional_data': "Check-out date must be after check-in date"
                            })

                except ValueError as e:
                    raise serializers.ValidationError({
                        'additional_data': f"Invalid date format. Use YYYY-MM-DD: {str(e)}"
                    })

        return data


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


class AccommodationRequestDetailSerializer(AccommodationRequestSerializer):
    """Detailed serializer for Accommodation Requests with bookings and assignment info"""
    bookings = AccommodationBookingSerializer(many=True, read_only=True)
    assigned_room_name = serializers.SerializerMethodField()
    assigned_staff_house_name = serializers.SerializerMethodField()
    assigned_room = serializers.SerializerMethodField()
    assigned_staff_house = serializers.SerializerMethodField()

    class Meta(AccommodationRequestSerializer.Meta):
        fields = AccommodationRequestSerializer.Meta.fields + [
            'bookings', 'assigned_room', 'assigned_room_name',
            'assigned_staff_house', 'assigned_staff_house_name'
        ]

    def get_assigned_room(self, obj):
        """Get assigned room ID from bookings"""
        booking = obj.bookings.first()
        return booking.room.id if booking and booking.room else None

    def get_assigned_room_name(self, obj):
        """Get assigned room name from bookings"""
        booking = obj.bookings.first()
        return booking.room.name if booking and booking.room else None

    def get_assigned_staff_house(self, obj):
        """Get assigned staff house ID from bookings"""
        booking = obj.bookings.first()
        return booking.staff_house.id if booking and booking.staff_house else None

    def get_assigned_staff_house_name(self, obj):
        """Get assigned staff house name from bookings"""
        booking = obj.bookings.first()
        return booking.staff_house.name if booking and booking.staff_house else None


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
