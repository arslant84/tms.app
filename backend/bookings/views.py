from datetime import datetime, timedelta

from accounts.utils import can_view_all, is_module_admin
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from utils.api_response import (
    error_response,
    forbidden_response,
    get_pagination_params,
    not_found_response,
    success_response,
    validation_error_response,
)

from .models import BookingStatus, FlightBooking
from .serializers import (
    BookingStatsSerializer,
    BookingStatusUpdateSerializer,
    FlightBookingCreateSerializer,
    FlightBookingSerializer,
    FlightBookingUpdateSerializer,
    FlightTicketSerializer,
)


class FlightBookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing flight bookings
    """

    queryset = FlightBooking.objects.all()
    serializer_class = FlightBookingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "airline",
        "flight_number",
        "departure_airport",
        "arrival_airport",
        "booking_reference",
        "ticket_number",
        "user__email",
        "user__first_name",
        "user__last_name",
    ]
    ordering_fields = ["departure_time", "arrival_time", "created_at", "status", "cost"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        user = self.request.user
        queryset = super().get_queryset()

        # Users with view_all_bookings or view_all_trf permission can see all bookings
        if (
            user.is_superuser
            or can_view_all(user, "booking")
            or can_view_all(user, "trf")
        ):
            pass
        else:
            # Regular users can only see their own bookings
            queryset = queryset.filter(user=user)

        # Filter by TRF
        trf_id = self.request.query_params.get("trf", None)
        if trf_id:
            queryset = queryset.filter(trf_id=trf_id)

        # Filter by status
        status_param = self.request.query_params.get("status", None)
        if status_param:
            queryset = queryset.filter(status=status_param)

        # Filter by date range
        from_date = self.request.query_params.get("from_date", None)
        to_date = self.request.query_params.get("to_date", None)
        if from_date:
            queryset = queryset.filter(departure_time__gte=from_date)
        if to_date:
            queryset = queryset.filter(departure_time__lte=to_date)

        # Filter by airline
        airline = self.request.query_params.get("airline", None)
        if airline:
            queryset = queryset.filter(airline__icontains=airline)

        return queryset.select_related("user", "trf", "booked_by")

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == "create":
            return FlightBookingCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return FlightBookingUpdateSerializer
        return FlightBookingSerializer

    def perform_create(self, serializer):
        """
        Booking is an admin/travel-desk function, not self-service - there is
        no traveler-facing UI anywhere in this app for creating a flight
        booking, only the admin flight module. Without this check, any
        authenticated user could create a FlightBooking against any other
        user's approved TRF (validate_trf only checks the TRF's status, not
        who is allowed to book it).
        """
        user = self.request.user
        if not (
            user.is_superuser
            or is_module_admin(user, "booking")
            or is_module_admin(user, "trf")
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "Only booking/TRF admins can create flight bookings."
            )
        serializer.save()

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        """Confirm a flight booking (requires booking management permission)"""
        if (
            not request.user.is_superuser
            and not is_module_admin(request.user, "booking")
            and not is_module_admin(request.user, "trf")
        ):
            return forbidden_response(
                message="Only travel desk staff can confirm bookings"
            )

        booking = self.get_object()

        if booking.status != BookingStatus.REQUESTED:
            return error_response(
                message=f"Cannot confirm booking with status {booking.status}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        booking.confirm_booking()

        serializer = self.get_serializer(booking)
        return success_response(
            data=serializer.data,
            message="Flight booking confirmed successfully",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def issue_ticket(self, request, pk=None):
        """Issue ticket for a confirmed booking (requires booking management permission)"""
        if (
            not request.user.is_superuser
            and not is_module_admin(request.user, "booking")
            and not is_module_admin(request.user, "trf")
        ):
            return forbidden_response(
                message="Only travel desk staff can issue tickets"
            )

        booking = self.get_object()

        serializer = FlightTicketSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors, message="Invalid ticket data"
            )

        try:
            booking.issue_ticket(serializer.validated_data["ticket_number"])
        except ValueError as e:
            return error_response(
                message=str(e), status_code=status.HTTP_400_BAD_REQUEST
            )

        response_serializer = self.get_serializer(booking)
        return success_response(
            data=response_serializer.data,
            message="Ticket issued successfully",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a flight booking"""
        booking = self.get_object()

        # Check permissions - user can cancel own bookings, admins can cancel any
        is_admin = (
            request.user.is_superuser
            or is_module_admin(request.user, "booking")
            or is_module_admin(request.user, "trf")
        )
        if booking.user != request.user and not is_admin:
            return forbidden_response(message="You can only cancel your own bookings")

        if booking.status == BookingStatus.CANCELLED:
            return error_response(
                message="Booking is already cancelled",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get("reason", "Cancelled by user")
        booking.cancel_booking(reason)

        serializer = self.get_serializer(booking)
        return success_response(
            data=serializer.data,
            message="Flight booking cancelled successfully",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"])
    def update_status(self, request, pk=None):
        """Update booking status (requires booking management permission)"""
        if (
            not request.user.is_superuser
            and not is_module_admin(request.user, "booking")
            and not is_module_admin(request.user, "trf")
        ):
            return forbidden_response(
                message="Only travel desk staff can update booking status"
            )

        booking = self.get_object()

        serializer = BookingStatusUpdateSerializer(
            data=request.data, context={"instance": booking}
        )
        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors, message="Invalid status data"
            )

        booking.status = serializer.validated_data["status"]
        if serializer.validated_data.get("reason"):
            booking.notes = (
                f"{booking.notes or ''}\n{serializer.validated_data['reason']}"
            )
        booking.save()

        response_serializer = self.get_serializer(booking)
        return success_response(
            data=response_serializer.data,
            message="Booking status updated successfully",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def my_bookings(self, request):
        """Get current user's flight bookings"""
        bookings = self.get_queryset().filter(user=request.user)
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        """Get upcoming flights"""
        now = timezone.now()
        bookings = (
            self.get_queryset()
            .filter(
                departure_time__gte=now,
                status__in=[BookingStatus.CONFIRMED, BookingStatus.TICKETED],
            )
            .order_by("departure_time")
        )

        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get flight booking statistics"""
        user = request.user
        if (
            user.is_superuser
            or can_view_all(user, "booking")
            or can_view_all(user, "trf")
        ):
            queryset = self.get_queryset()
        else:
            queryset = self.get_queryset().filter(user=user)

        total = queryset.count()
        pending = queryset.filter(status=BookingStatus.PENDING).count()
        confirmed = queryset.filter(status=BookingStatus.CONFIRMED).count()
        ticketed = queryset.filter(status=BookingStatus.TICKETED).count()
        cancelled = queryset.filter(status=BookingStatus.CANCELLED).count()

        total_cost = queryset.aggregate(total=Sum("cost"), total_tax=Sum("tax_amount"))

        # By airline
        by_airline = dict(
            queryset.values("airline")
            .annotate(count=Count("id"))
            .values_list("airline", "count")
        )

        # By booking class
        by_class = dict(
            queryset.values("booking_class")
            .annotate(count=Count("id"))
            .values_list("booking_class", "count")
        )

        stats = {
            "total_bookings": total,
            "pending_bookings": pending,
            "confirmed_bookings": confirmed,
            "ticketed_bookings": ticketed,
            "cancelled_bookings": cancelled,
            "total_flight_cost": total_cost["total"] or 0,
            "total_tax": total_cost["total_tax"] or 0,
            "by_airline": by_airline,
            "by_class": by_class,
            "by_status": {
                "PENDING": pending,
                "CONFIRMED": confirmed,
                "TICKETED": ticketed,
                "CANCELLED": cancelled,
            },
        }

        return success_response(
            data=stats,
            message="Flight booking statistics retrieved successfully",
            status_code=status.HTTP_200_OK,
        )
