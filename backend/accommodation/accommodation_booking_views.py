"""
AccommodationBookingViewSet - booking CRUD and availability checks.

Split out of accommodation/views.py (see
docs/CODEBASE_REFACTOR_ROADMAP.md item 6) - a pure file move, no logic
changed. Staff-house/room/request viewsets moved to their own sibling
modules in the same split.
"""

import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from .models import AccommodationBooking, AccommodationRoom
from .serializers import (
    AccommodationBookingDetailSerializer,
    AccommodationBookingSerializer,
    RoomAvailabilitySerializer,
)


class AccommodationBookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Accommodation Bookings

    Endpoints:
    - GET /api/accommodation/bookings/ - List all bookings
    - POST /api/accommodation/bookings/ - Create a new booking
    - GET /api/accommodation/bookings/{id}/ - Retrieve booking details
    - PUT /api/accommodation/bookings/{id}/ - Update booking
    - PATCH /api/accommodation/bookings/{id}/ - Partial update
    - DELETE /api/accommodation/bookings/{id}/ - Delete booking
    - POST /api/accommodation/bookings/check-availability/ - Check room availability
    - POST /api/accommodation/bookings/{id}/cancel/ - Cancel booking
    """

    queryset = AccommodationBooking.objects.all()
    serializer_class = AccommodationBookingSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use detailed serializer for retrieve action"""
        if self.action == "retrieve":
            return AccommodationBookingDetailSerializer
        return AccommodationBookingSerializer

    def get_queryset(self):
        """Filter bookings by various parameters"""
        queryset = self.queryset.select_related("staff_house", "room", "staff", "trf")

        staff_house = self.request.query_params.get("staff_house", None)
        room = self.request.query_params.get("room", None)
        staff = self.request.query_params.get("staff", None)
        status = self.request.query_params.get("status", None)
        date_from = self.request.query_params.get("date_from", None)
        date_to = self.request.query_params.get("date_to", None)

        if staff_house:
            queryset = queryset.filter(staff_house_id=staff_house)

        if room:
            queryset = queryset.filter(room_id=room)

        if staff:
            queryset = queryset.filter(staff_id=staff)

        if status:
            queryset = queryset.filter(status=status)

        if date_from:
            queryset = queryset.filter(date__gte=date_from)

        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        return queryset.order_by("-date", "-created_at")

    @action(detail=False, methods=["post"])
    def check_availability(self, request):
        """
        Check room availability for a given date range

        Expected payload:
        {
            "staff_house": 1,
            "start_date": "2025-10-15",
            "end_date": "2025-10-20"
        }
        """
        serializer = RoomAvailabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        staff_house_id = serializer.validated_data["staff_house"]
        start_date = serializer.validated_data["start_date"]
        end_date = serializer.validated_data["end_date"]

        # Get all rooms in the staff house
        rooms = AccommodationRoom.objects.filter(staff_house_id=staff_house_id)

        # Get bookings for the date range
        bookings = AccommodationBooking.objects.filter(
            staff_house_id=staff_house_id,
            date__gte=start_date,
            date__lte=end_date,
            status__in=["Confirmed", "Pending"],
        )

        # Build availability response
        availability = []
        for room in rooms:
            room_bookings = bookings.filter(room=room)
            booked_dates = [
                booking.date.strftime("%Y-%m-%d") for booking in room_bookings
            ]

            availability.append(
                {
                    "room_id": room.id,
                    "room_name": room.name,
                    "room_type": room.room_type,
                    "capacity": room.capacity,
                    "status": room.status,
                    "booked_dates": booked_dates,
                    "is_fully_booked": len(booked_dates)
                    == (end_date - start_date).days + 1,
                }
            )

        return Response(
            {
                "staff_house_id": staff_house_id,
                "start_date": start_date,
                "end_date": end_date,
                "rooms": availability,
            }
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a booking"""
        booking = self.get_object()

        if booking.status == "Cancelled":
            return Response(
                {"error": "Booking is already cancelled"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = "Cancelled"
        booking.save()

        serializer = self.get_serializer(booking)
        return Response(serializer.data)
