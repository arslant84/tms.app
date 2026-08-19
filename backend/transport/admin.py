from django.contrib import admin

from .models import TransportApprovalStep, TransportRequest, VehicleAssignment


@admin.register(TransportRequest)
class TransportRequestAdmin(admin.ModelAdmin):
    """Admin configuration for TransportRequest model"""

    list_display = [
        "id",
        "requestor_name",
        "department",
        "purpose_short",
        "status",
        "submitted_at",
        "created_at",
    ]
    list_filter = ["status", "department", "created_at", "submitted_at"]
    search_fields = [
        "purpose",
        "requestor_name",
        "staff_id",
        "department",
        "requestor__email",
        "requestor__first_name",
        "requestor__last_name",
    ]
    readonly_fields = ["created_at", "updated_at", "submitted_at"]
    ordering = ["-created_at"]

    def purpose_short(self, obj):
        """Return truncated purpose for list display"""
        return obj.purpose[:50] + "..." if len(obj.purpose) > 50 else obj.purpose

    purpose_short.short_description = "Purpose"

    fieldsets = (
        (
            "Requestor Information",
            {
                "fields": (
                    "requestor",
                    "requestor_name",
                    "staff_id",
                    "department",
                    "position",
                )
            },
        ),
        (
            "Basic Information",
            {"fields": ("trf", "purpose", "tsr_reference", "status")},
        ),
        (
            "Transport Details (JSON)",
            {
                "fields": ("transport_details",),
                "description": "Array of transport detail objects with date, from, to, departureTime, numberOfPassengers",
            },
        ),
        (
            "Submission Confirmations",
            {
                "fields": (
                    "confirm_policy",
                    "confirm_manager_approval",
                    "confirm_terms_and_conditions",
                    "additional_comments",
                )
            },
        ),
        (
            "Booking Details (Admin)",
            {
                "fields": ("booking_details",),
                "description": "Booking details filled by transport admin",
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("submitted_at", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(TransportApprovalStep)
class TransportApprovalStepAdmin(admin.ModelAdmin):
    """Admin configuration for TransportApprovalStep model"""

    list_display = [
        "id",
        "transport_request",
        "step_role",
        "step_name",
        "status",
        "step_date",
        "created_at",
    ]
    list_filter = ["status", "step_role", "step_date", "created_at"]
    search_fields = ["transport_request__title", "step_role", "step_name", "comments"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = (
        ("Transport Request", {"fields": ("transport_request",)}),
        (
            "Approval Step",
            {"fields": ("step_role", "step_name", "status", "step_date")},
        ),
        ("Comments", {"fields": ("comments",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(VehicleAssignment)
class VehicleAssignmentAdmin(admin.ModelAdmin):
    """Admin configuration for VehicleAssignment model"""

    list_display = [
        "id",
        "transport_request",
        "vehicle_number",
        "vehicle_type",
        "driver_name",
        "status",
        "assigned_by",
        "assignment_date",
    ]
    list_filter = ["status", "vehicle_type", "assignment_date", "completion_date"]
    search_fields = [
        "vehicle_number",
        "vehicle_type",
        "driver_name",
        "driver_contact",
        "driver_license",
        "transport_request__title",
    ]
    readonly_fields = ["assignment_date", "created_at", "updated_at"]
    ordering = ["-assignment_date"]

    fieldsets = (
        ("Transport Request", {"fields": ("transport_request",)}),
        (
            "Vehicle Details",
            {"fields": ("vehicle_number", "vehicle_type", "vehicle_capacity")},
        ),
        (
            "Driver Details",
            {"fields": ("driver_name", "driver_contact", "driver_license")},
        ),
        (
            "Assignment Details",
            {"fields": ("assigned_by", "status", "assignment_date", "completion_date")},
        ),
        (
            "Tracking",
            {"fields": ("odometer_start", "odometer_end", "fuel_used_liters")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
