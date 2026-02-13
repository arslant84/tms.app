from django.contrib import admin
from .models import (
    AccommodationStaffHouse,
    AccommodationRoom,
    AccommodationRequest,
    AccommodationBooking
)


@admin.register(AccommodationStaffHouse)
class AccommodationStaffHouseAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'location', 'created_at']
    search_fields = ['name', 'location', 'address']
    list_filter = ['location', 'created_at']
    ordering = ['-created_at']


@admin.register(AccommodationRoom)
class AccommodationRoomAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'staff_house', 'room_type', 'capacity', 'status', 'created_at']
    search_fields = ['name', 'room_type']
    list_filter = ['status', 'staff_house', 'created_at']
    ordering = ['staff_house', 'name']


@admin.register(AccommodationRequest)
class AccommodationRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'requestor_name', 'department', 'status', 'submitted_at', 'created_at']
    search_fields = ['requestor_name', 'department', 'email']
    list_filter = ['status', 'department', 'created_at']
    ordering = ['-created_at']


@admin.register(AccommodationBooking)
class AccommodationBookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'room', 'staff', 'date', 'status', 'created_at']
    search_fields = ['room__name', 'staff__email', 'notes']
    list_filter = ['status', 'date', 'staff_house', 'created_at']
    ordering = ['-date', '-created_at']
