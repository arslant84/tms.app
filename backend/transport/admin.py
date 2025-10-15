from django.contrib import admin
from .models import (
    TransportRequest, TransportSegment, TransportApprovalStep, VehicleAssignment
)


@admin.register(TransportRequest)
class TransportRequestAdmin(admin.ModelAdmin):
    """Admin configuration for TransportRequest model"""
    list_display = [
        'id', 'title', 'requestor', 'transport_type', 'status',
        'number_of_passengers', 'estimated_cost', 'currency',
        'submitted_at', 'created_at'
    ]
    list_filter = ['status', 'transport_type', 'currency', 'created_at', 'submitted_at']
    search_fields = [
        'title', 'purpose', 'requestor__email', 'requestor__first_name',
        'requestor__last_name', 'passenger_names'
    ]
    readonly_fields = ['created_at', 'updated_at', 'submitted_at']
    ordering = ['-created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('requestor', 'trf', 'title', 'purpose', 'status')
        }),
        ('Transport Details', {
            'fields': (
                'transport_type', 'vehicle_type', 'number_of_passengers',
                'passenger_names', 'special_requirements'
            )
        }),
        ('Cost Information', {
            'fields': ('estimated_cost', 'currency')
        }),
        ('Additional Information', {
            'fields': ('additional_comments', 'additional_data')
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TransportSegment)
class TransportSegmentAdmin(admin.ModelAdmin):
    """Admin configuration for TransportSegment model"""
    list_display = [
        'id', 'transport_request', 'from_location', 'to_location',
        'departure_date', 'departure_time', 'distance_km', 'segment_cost'
    ]
    list_filter = ['departure_date', 'created_at']
    search_fields = [
        'from_location', 'to_location', 'route_description',
        'vehicle_number', 'driver_name'
    ]
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['departure_date', 'departure_time']

    fieldsets = (
        ('Transport Request', {
            'fields': ('transport_request',)
        }),
        ('Journey Details', {
            'fields': (
                'from_location', 'to_location', 'departure_date', 'departure_time',
                'arrival_date', 'arrival_time'
            )
        }),
        ('Route Information', {
            'fields': ('distance_km', 'estimated_duration_hours', 'route_description')
        }),
        ('Vehicle Assignment', {
            'fields': ('vehicle_number', 'driver_name', 'driver_contact')
        }),
        ('Cost', {
            'fields': ('segment_cost',)
        }),
        ('Additional Information', {
            'fields': ('remarks',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TransportApprovalStep)
class TransportApprovalStepAdmin(admin.ModelAdmin):
    """Admin configuration for TransportApprovalStep model"""
    list_display = [
        'id', 'transport_request', 'step_role', 'step_name',
        'status', 'step_date', 'created_at'
    ]
    list_filter = ['status', 'step_role', 'step_date', 'created_at']
    search_fields = [
        'transport_request__title', 'step_role', 'step_name', 'comments'
    ]
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    fieldsets = (
        ('Transport Request', {
            'fields': ('transport_request',)
        }),
        ('Approval Step', {
            'fields': ('step_role', 'step_name', 'status', 'step_date')
        }),
        ('Comments', {
            'fields': ('comments',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(VehicleAssignment)
class VehicleAssignmentAdmin(admin.ModelAdmin):
    """Admin configuration for VehicleAssignment model"""
    list_display = [
        'id', 'transport_request', 'vehicle_number', 'vehicle_type',
        'driver_name', 'status', 'assigned_by', 'assignment_date'
    ]
    list_filter = ['status', 'vehicle_type', 'assignment_date', 'completion_date']
    search_fields = [
        'vehicle_number', 'vehicle_type', 'driver_name',
        'driver_contact', 'driver_license', 'transport_request__title'
    ]
    readonly_fields = ['assignment_date', 'created_at', 'updated_at']
    ordering = ['-assignment_date']

    fieldsets = (
        ('Transport Request', {
            'fields': ('transport_request',)
        }),
        ('Vehicle Details', {
            'fields': ('vehicle_number', 'vehicle_type', 'vehicle_capacity')
        }),
        ('Driver Details', {
            'fields': ('driver_name', 'driver_contact', 'driver_license')
        }),
        ('Assignment Details', {
            'fields': ('assigned_by', 'status', 'assignment_date', 'completion_date')
        }),
        ('Tracking', {
            'fields': ('odometer_start', 'odometer_end', 'fuel_used_liters')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
