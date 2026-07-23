from django.contrib import admin
from django.utils.html import format_html

from .models import FlightBooking


@admin.register(FlightBooking)
class FlightBookingAdmin(admin.ModelAdmin):
    """Admin configuration for FlightBooking model"""

    list_display = [
        "id",
        "booking_reference",
        "user_link",
        "airline",
        "flight_number",
        "route_display",
        "departure_time",
        "status_badge",
        "total_cost",
        "created_at",
    ]
    list_filter = [
        "status",
        "booking_class",
        "flight_type",
        "airline",
        "created_at",
        "departure_time",
    ]
    search_fields = [
        "booking_reference",
        "ticket_number",
        "flight_number",
        "user__email",
        "user__first_name",
        "user__last_name",
        "departure_airport",
        "arrival_airport",
    ]
    readonly_fields = [
        "booking_date",
        "confirmation_date",
        "ticketing_date",
        "cancellation_date",
        "created_at",
        "updated_at",
        "total_cost_display",
        "route_display",
    ]
    ordering = ["-created_at"]
    date_hierarchy = "departure_time"

    fieldsets = (
        (
            "Booking Information",
            {"fields": ("trf", "user", "booking_reference", "ticket_number", "status")},
        ),
        (
            "Flight Details",
            {
                "fields": (
                    "flight_type",
                    "airline",
                    "airline_code",
                    "flight_number",
                    "departure_airport",
                    "departure_airport_code",
                    "departure_terminal",
                    "arrival_airport",
                    "arrival_airport_code",
                    "arrival_terminal",
                    "departure_time",
                    "arrival_time",
                    "route_display",
                )
            },
        ),
        ("Class & Seat", {"fields": ("booking_class", "seat_number")}),
        (
            "Cost Information",
            {"fields": ("cost", "currency", "tax_amount", "total_cost_display")},
        ),
        (
            "Baggage & Services",
            {
                "fields": (
                    "baggage_allowance",
                    "carry_on_allowance",
                    "meal_preference",
                    "special_requests",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Processing",
            {
                "fields": (
                    "booked_by",
                    "booking_date",
                    "confirmation_date",
                    "ticketing_date",
                    "cancellation_date",
                    "cancellation_reason",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Additional",
            {"fields": ("notes", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def user_link(self, obj):
        """Display user with link"""
        return format_html(
            '<a href="/admin/accounts/user/{}/change/">{}</a>',
            obj.user.id,
            obj.user.get_full_name(),
        )

    user_link.short_description = "User"

    def route_display(self, obj):
        """Display formatted route"""
        return obj.route

    route_display.short_description = "Route"

    def status_badge(self, obj):
        """Display status with color badge"""
        colors = {
            "PENDING": "#FFA500",
            "REQUESTED": "#17A2B8",
            "CONFIRMED": "#28A745",
            "TICKETED": "#007BFF",
            "CANCELLED": "#DC3545",
            "REFUNDED": "#6C757D",
            "NO_SHOW": "#343A40",
        }
        color = colors.get(obj.status, "#6C757D")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"

    def total_cost_display(self, obj):
        """Display total cost including tax"""
        return f"{obj.currency} {obj.total_cost:,.2f}"

    total_cost_display.short_description = "Total Cost (incl. tax)"

    def has_delete_permission(self, request, obj=None):
        """Only allow deletion of pending/cancelled bookings"""
        if obj and obj.status in ["TICKETED"]:
            return False
        return super().has_delete_permission(request, obj)
