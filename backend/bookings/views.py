from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.contrib.auth import get_user_model

from .models import FlightBooking, HotelBooking, BookingStatus
from .serializers import (
    FlightBookingSerializer, 
    FlightBookingCreateSerializer,
    HotelBookingSerializer,
    HotelBookingCreateSerializer,
    BookingStatusUpdateSerializer
)

User = get_user_model()


class FlightBookingViewSet(viewsets.ModelViewSet):
    queryset = FlightBooking.objects.all()
    serializer_class = FlightBookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['airline', 'flight_number', 'departure_airport', 'arrival_airport']
    ordering_fields = ['departure_time', 'arrival_time', 'created_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        
        # Admin and ticketing clerks can see all bookings
        if user.is_admin or user.role == 'ticketing_clerk':
            return FlightBooking.objects.all()
        
        # Regular users can only see their own bookings
        return FlightBooking.objects.filter(user=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FlightBookingCreateSerializer
        return FlightBookingSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status=BookingStatus.REQUESTED)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def confirm(self, request, pk=None):
        booking = self.get_object()
        
        # Only ticketing clerks and admins can confirm bookings
        if not (request.user.is_admin or request.user.role == 'ticketing_clerk'):
            return Response(
                {'error': 'Only ticketing clerks and admins can confirm bookings'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update the booking status
        booking.status = BookingStatus.CONFIRMED
        booking.save()
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        
        # Check if the booking can be cancelled
        if booking.status == BookingStatus.CANCELLED:
            return Response(
                {'error': 'Booking is already cancelled'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if the user is authorized to cancel
        if booking.user != request.user and not (request.user.is_admin or request.user.role == 'ticketing_clerk'):
            return Response(
                {'error': 'You can only cancel your own bookings'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update the booking status
        booking.status = BookingStatus.CANCELLED
        booking.save()
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)


class HotelBookingViewSet(viewsets.ModelViewSet):
    queryset = HotelBooking.objects.all()
    serializer_class = HotelBookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['hotel_name', 'location']
    ordering_fields = ['check_in_date', 'check_out_date', 'created_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        
        # Admin and ticketing clerks can see all bookings
        if user.is_admin or user.role == 'ticketing_clerk':
            return HotelBooking.objects.all()
        
        # Regular users can only see their own bookings
        return HotelBooking.objects.filter(user=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return HotelBookingCreateSerializer
        return HotelBookingSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status=BookingStatus.REQUESTED)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def confirm(self, request, pk=None):
        booking = self.get_object()
        
        # Only ticketing clerks and admins can confirm bookings
        if not (request.user.is_admin or request.user.role == 'ticketing_clerk'):
            return Response(
                {'error': 'Only ticketing clerks and admins can confirm bookings'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update the booking status
        booking.status = BookingStatus.CONFIRMED
        booking.save()
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        
        # Check if the booking can be cancelled
        if booking.status == BookingStatus.CANCELLED:
            return Response(
                {'error': 'Booking is already cancelled'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if the user is authorized to cancel
        if booking.user != request.user and not (request.user.is_admin or request.user.role == 'ticketing_clerk'):
            return Response(
                {'error': 'You can only cancel your own bookings'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update the booking status
        booking.status = BookingStatus.CANCELLED
        booking.save()
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
