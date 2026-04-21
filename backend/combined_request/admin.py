"""
Combined Request Django Admin Configuration

Provides admin interface for managing Combined Requests and related models.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    CombinedRequest,
    CombinedRequestPassport,
    CombinedRequestItinerary,
    CombinedRequestTransportSegment,
    CombinedRequestDocument,
    CombinedRequestApprovalStep,
)


class CombinedRequestPassportInline(admin.TabularInline):
    model = CombinedRequestPassport
    extra = 0
    fields = ['full_name', 'passport_number', 'nationality', 'expiry_date', 'passport_file']
    readonly_fields = ['created_at']


class CombinedRequestItineraryInline(admin.TabularInline):
    model = CombinedRequestItinerary
    extra = 0
    fields = ['segment_order', 'segment_date', 'from_location', 'to_location', 'mode_of_travel', 'flight_number']
    ordering = ['segment_order']


class CombinedRequestTransportSegmentInline(admin.TabularInline):
    model = CombinedRequestTransportSegment
    extra = 0
    fields = ['segment_order', 'pickup_date', 'pickup_time', 'pickup_location', 'dropoff_location', 'passengers']
    ordering = ['segment_order']


class CombinedRequestDocumentInline(admin.TabularInline):
    model = CombinedRequestDocument
    extra = 0
    fields = ['document_type', 'module', 'file', 'description', 'uploaded_at']
    readonly_fields = ['uploaded_at']


class CombinedRequestApprovalStepInline(admin.TabularInline):
    model = CombinedRequestApprovalStep
    extra = 0
    fields = ['step_order', 'step_name', 'module', 'status', 'approver', 'actioned_at', 'comments']
    readonly_fields = ['actioned_at']
    ordering = ['step_order']


@admin.register(CombinedRequest)
class CombinedRequestAdmin(admin.ModelAdmin):
    list_display = [
        'request_number',
        'requestor_name',
        'department',
        'included_modules_display',
        'status',
        'submitted_at',
        'created_at',
    ]
    list_filter = [
        'status',
        'include_travel',
        'include_transport',
        'include_accommodation',
        'include_visa',
        'travel_type',
        'created_at',
    ]
    search_fields = [
        'request_number',
        'requestor_name',
        'staff_id',
        'department',
        'email',
        'destination_country',
        'destination_city',
    ]
    readonly_fields = [
        'request_number',
        'created_at',
        'updated_at',
        'submitted_at',
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Request Information', {
            'fields': (
                'request_number',
                'status',
                'requestor',
                'requestor_name',
                'staff_id',
                'department',
                'position',
                'email',
                'phone',
                'cost_center',
            )
        }),
        ('Module Selection', {
            'fields': (
                ('include_travel', 'include_transport'),
                ('include_accommodation', 'include_visa'),
            )
        }),
        ('Module Statuses', {
            'fields': (
                ('travel_status', 'transport_status'),
                ('accommodation_status', 'visa_status'),
            ),
            'classes': ('collapse',),
        }),
        ('Travel Details', {
            'fields': (
                'travel_type',
                'travel_purpose',
                ('departure_date', 'return_date'),
                ('destination_country', 'destination_city'),
                'travel_data',
            ),
            'classes': ('collapse',),
        }),
        ('Transport Details', {
            'fields': (
                ('transport_required_from', 'transport_required_to'),
                'transport_pickup_location',
                'transport_dropoff_location',
                'transport_data',
            ),
            'classes': ('collapse',),
        }),
        ('Accommodation Details', {
            'fields': (
                ('accommodation_checkin', 'accommodation_checkout'),
                'accommodation_location',
                'accommodation_guests',
                'accommodation_preferences',
                'accommodation_data',
            ),
            'classes': ('collapse',),
        }),
        ('Visa Details', {
            'fields': (
                'visa_destination_country',
                'visa_type',
                'passport_number',
                'passport_expiry',
                'visa_data',
            ),
            'classes': ('collapse',),
        }),
        ('Comments & Data', {
            'fields': (
                'additional_comments',
                'additional_data',
            ),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': (
                'submitted_at',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )

    inlines = [
        CombinedRequestPassportInline,
        CombinedRequestItineraryInline,
        CombinedRequestTransportSegmentInline,
        CombinedRequestDocumentInline,
        CombinedRequestApprovalStepInline,
    ]

    def included_modules_display(self, obj):
        """Display included modules as colored badges."""
        modules = []
        if obj.include_travel:
            modules.append('<span style="background:#007bff;color:white;padding:2px 6px;border-radius:3px;margin-right:3px;">TSR</span>')
        if obj.include_transport:
            modules.append('<span style="background:#17a2b8;color:white;padding:2px 6px;border-radius:3px;margin-right:3px;">Transport</span>')
        if obj.include_accommodation:
            modules.append('<span style="background:#28a745;color:white;padding:2px 6px;border-radius:3px;margin-right:3px;">Accommodation</span>')
        if obj.include_visa:
            modules.append('<span style="background:#ffc107;color:black;padding:2px 6px;border-radius:3px;margin-right:3px;">Visa</span>')
        return format_html(''.join(modules)) if modules else '-'
    included_modules_display.short_description = 'Modules'


@admin.register(CombinedRequestPassport)
class CombinedRequestPassportAdmin(admin.ModelAdmin):
    list_display = ['combined_request', 'full_name', 'passport_number', 'nationality', 'expiry_date']
    list_filter = ['nationality']
    search_fields = ['full_name', 'passport_number', 'combined_request__request_number']


@admin.register(CombinedRequestItinerary)
class CombinedRequestItineraryAdmin(admin.ModelAdmin):
    list_display = ['combined_request', 'segment_order', 'segment_date', 'from_location', 'to_location', 'mode_of_travel']
    list_filter = ['mode_of_travel', 'segment_date']
    search_fields = ['from_location', 'to_location', 'combined_request__request_number']
    ordering = ['combined_request', 'segment_order']


@admin.register(CombinedRequestTransportSegment)
class CombinedRequestTransportSegmentAdmin(admin.ModelAdmin):
    list_display = ['combined_request', 'segment_order', 'pickup_date', 'pickup_location', 'dropoff_location', 'passengers']
    list_filter = ['pickup_date']
    search_fields = ['pickup_location', 'dropoff_location', 'combined_request__request_number']
    ordering = ['combined_request', 'segment_order']


@admin.register(CombinedRequestDocument)
class CombinedRequestDocumentAdmin(admin.ModelAdmin):
    list_display = ['combined_request', 'document_type', 'module', 'file_name', 'uploaded_at']
    list_filter = ['document_type', 'module', 'uploaded_at']
    search_fields = ['file_name', 'description', 'combined_request__request_number']


@admin.register(CombinedRequestApprovalStep)
class CombinedRequestApprovalStepAdmin(admin.ModelAdmin):
    list_display = ['combined_request', 'step_order', 'step_name', 'module', 'status', 'approver', 'actioned_at']
    list_filter = ['status', 'module', 'step_name']
    search_fields = ['step_name', 'combined_request__request_number']
    ordering = ['combined_request', 'step_order']
