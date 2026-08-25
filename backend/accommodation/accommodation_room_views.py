"""
Staff house and room viewsets for the accommodation module.

Split out of accommodation/views.py (see
docs/CODEBASE_REFACTOR_ROADMAP.md item 6) - a pure file move, no logic
changed. Request and booking viewsets moved to their own sibling
modules in the same split.
"""

import logging

from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from .models import AccommodationBooking, AccommodationRoom, AccommodationStaffHouse
from .serializers import (
    AccommodationBookingSerializer,
    AccommodationRoomSerializer,
    AccommodationStaffHouseSerializer,
)


class AccommodationStaffHouseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Staff Houses

    Endpoints:
    - GET /api/accommodation/staff-houses/ - List all staff houses
    - POST /api/accommodation/staff-houses/ - Create a new staff house
    - GET /api/accommodation/staff-houses/{id}/ - Retrieve staff house details
    - PUT /api/accommodation/staff-houses/{id}/ - Update staff house
    - PATCH /api/accommodation/staff-houses/{id}/ - Partial update
    - DELETE /api/accommodation/staff-houses/{id}/ - Delete staff house
    """

    queryset = AccommodationStaffHouse.objects.all()
    serializer_class = AccommodationStaffHouseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter staff houses by location if provided"""
        queryset = self.queryset
        location = self.request.query_params.get("location", None)
        search = self.request.query_params.get("search", None)

        if location:
            queryset = queryset.filter(location__icontains=location)

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(location__icontains=search)
                | Q(description__icontains=search)
            )

        return queryset.order_by("-created_at")

    @action(detail=True, methods=["get"])
    def rooms(self, request, pk=None):
        """Get all rooms for a specific staff house"""
        staff_house = self.get_object()
        rooms = AccommodationRoom.objects.filter(staff_house=staff_house)
        serializer = AccommodationRoomSerializer(rooms, many=True)
        return Response(serializer.data)


class AccommodationRoomViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Rooms

    Endpoints:
    - GET /api/accommodation/rooms/ - List all rooms
    - POST /api/accommodation/rooms/ - Create a new room
    - GET /api/accommodation/rooms/{id}/ - Retrieve room details
    - PUT /api/accommodation/rooms/{id}/ - Update room
    - PATCH /api/accommodation/rooms/{id}/ - Partial update
    - DELETE /api/accommodation/rooms/{id}/ - Delete room
    - GET /api/accommodation/rooms/available/ - List available rooms
    """

    queryset = AccommodationRoom.objects.all()
    serializer_class = AccommodationRoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter rooms by staff_house, status, or availability"""
        queryset = self.queryset.select_related("staff_house")

        staff_house = self.request.query_params.get("staff_house", None)
        status = self.request.query_params.get("status", None)
        room_type = self.request.query_params.get("room_type", None)

        if staff_house:
            queryset = queryset.filter(staff_house_id=staff_house)

        if status:
            queryset = queryset.filter(status=status)

        if room_type:
            queryset = queryset.filter(room_type__icontains=room_type)

        return queryset.order_by("staff_house", "name")

    @action(detail=False, methods=["get"])
    def available(self, request):
        """List all available rooms"""
        available_rooms = self.queryset.filter(status="Available")
        serializer = self.get_serializer(available_rooms, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def bookings(self, request, pk=None):
        """Get all bookings for a specific room"""
        room = self.get_object()
        date_from = request.query_params.get("date_from", None)
        date_to = request.query_params.get("date_to", None)

        bookings = AccommodationBooking.objects.filter(room=room)

        if date_from:
            bookings = bookings.filter(date__gte=date_from)
        if date_to:
            bookings = bookings.filter(date__lte=date_to)

        serializer = AccommodationBookingSerializer(bookings, many=True)
        return Response(serializer.data)
