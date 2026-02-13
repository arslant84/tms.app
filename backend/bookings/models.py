from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from decimal import Decimal
from trf.models import TravelRequest


class BookingClass(models.TextChoices):
    """Flight booking class choices"""
    ECONOMY = 'ECONOMY', _('Economy')
    PREMIUM_ECONOMY = 'PREMIUM_ECONOMY', _('Premium Economy')
    BUSINESS = 'BUSINESS', _('Business')
    FIRST = 'FIRST', _('First')


class BookingStatus(models.TextChoices):
    """Booking status choices"""
    PENDING = 'PENDING', _('Pending')
    REQUESTED = 'REQUESTED', _('Requested')
    CONFIRMED = 'CONFIRMED', _('Confirmed')
    TICKETED = 'TICKETED', _('Ticketed')
    CANCELLED = 'CANCELLED', _('Cancelled')
    REFUNDED = 'REFUNDED', _('Refunded')
    NO_SHOW = 'NO_SHOW', _('No Show')


class FlightType(models.TextChoices):
    """Flight type choices"""
    ONE_WAY = 'ONE_WAY', _('One Way')
    ROUND_TRIP = 'ROUND_TRIP', _('Round Trip')
    MULTI_CITY = 'MULTI_CITY', _('Multi City')


class BaggageType(models.TextChoices):
    """Baggage type choices"""
    CARRY_ON = 'CARRY_ON', _('Carry-on')
    CHECKED = 'CHECKED', _('Checked')
    EXTRA = 'EXTRA', _('Extra')


class FlightBooking(models.Model):
    """
    Flight booking model for managing flight reservations linked to TRFs.
    Supports multi-segment flights, baggage tracking, and ticketing workflow.
    """
    # Core Relations
    trf = models.ForeignKey(
        TravelRequest,
        on_delete=models.CASCADE,
        related_name='flight_bookings',
        help_text="Travel request this booking is for"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='flight_bookings',
        help_text="Traveler for this booking"
    )

    # Flight Details
    flight_type = models.CharField(
        max_length=20,
        choices=FlightType.choices,
        default=FlightType.ONE_WAY,
        help_text="Type of flight booking"
    )
    airline = models.CharField(max_length=100, help_text="Airline name")
    airline_code = models.CharField(max_length=10, blank=True, null=True, help_text="2-letter IATA code (e.g., EK, QR)")
    flight_number = models.CharField(max_length=20, help_text="Flight number (e.g., EK123)")

    # Route Information
    departure_airport = models.CharField(max_length=100, help_text="Departure airport name")
    departure_airport_code = models.CharField(max_length=10, blank=True, null=True, help_text="3-letter IATA code (e.g., DXB)")
    arrival_airport = models.CharField(max_length=100, help_text="Arrival airport name")
    arrival_airport_code = models.CharField(max_length=10, blank=True, null=True, help_text="3-letter IATA code (e.g., LHR)")

    # Schedule
    departure_time = models.DateTimeField(help_text="Scheduled departure date and time")
    arrival_time = models.DateTimeField(help_text="Scheduled arrival date and time")
    departure_terminal = models.CharField(max_length=20, blank=True, null=True, help_text="Departure terminal")
    arrival_terminal = models.CharField(max_length=20, blank=True, null=True, help_text="Arrival terminal")

    # Booking Class and Seat
    booking_class = models.CharField(
        max_length=20,
        choices=BookingClass.choices,
        default=BookingClass.ECONOMY,
        help_text="Cabin class"
    )
    seat_number = models.CharField(max_length=10, blank=True, null=True, help_text="Assigned seat number")

    # Status and References
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
        help_text="Current booking status"
    )
    booking_reference = models.CharField(max_length=50, unique=True, help_text="PNR/Booking reference")
    ticket_number = models.CharField(max_length=50, blank=True, null=True, help_text="E-ticket number")

    # Cost Information
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total booking cost"
    )
    currency = models.CharField(max_length=3, default='USD', help_text="Currency code (ISO 4217)")
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Tax amount"
    )

    # Baggage Allowance
    baggage_allowance = models.CharField(max_length=50, blank=True, null=True, help_text="Baggage allowance (e.g., 2x23kg)")
    carry_on_allowance = models.CharField(max_length=50, blank=True, null=True, help_text="Carry-on allowance (e.g., 7kg)")

    # Meal and Special Requests
    meal_preference = models.CharField(max_length=50, blank=True, null=True, help_text="Meal preference code (e.g., VGML, HNML)")
    special_requests = models.TextField(blank=True, null=True, help_text="Special assistance or requests")

    # Admin and Processing
    booked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='flights_booked',
        help_text="Admin/Travel desk who made the booking"
    )
    booking_date = models.DateTimeField(null=True, blank=True, help_text="Date booking was created")
    confirmation_date = models.DateTimeField(null=True, blank=True, help_text="Date booking was confirmed")
    ticketing_date = models.DateTimeField(null=True, blank=True, help_text="Date ticket was issued")
    cancellation_date = models.DateTimeField(null=True, blank=True, help_text="Date booking was cancelled")
    cancellation_reason = models.TextField(blank=True, null=True, help_text="Reason for cancellation")

    # Additional Information
    notes = models.TextField(blank=True, null=True, help_text="Internal notes")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['trf', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['booking_reference']),
            models.Index(fields=['departure_time']),
        ]

    def __str__(self):
        return f"{self.airline} {self.flight_number} - {self.user.get_full_name()} ({self.booking_reference})"

    @property
    def user_id(self):
        return self.user.id

    @property
    def trf_id(self):
        return self.trf.id

    @property
    def total_cost(self):
        """Total cost including taxes"""
        return self.cost + self.tax_amount

    @property
    def route(self):
        """Formatted route string"""
        dep_code = self.departure_airport_code or self.departure_airport
        arr_code = self.arrival_airport_code or self.arrival_airport
        return f"{dep_code} → {arr_code}"

    def confirm_booking(self):
        """Mark booking as confirmed"""
        from django.utils import timezone
        self.status = BookingStatus.CONFIRMED
        self.confirmation_date = timezone.now()
        self.save(update_fields=['status', 'confirmation_date'])

    def issue_ticket(self, ticket_number):
        """Issue ticket for confirmed booking"""
        from django.utils import timezone
        if self.status != BookingStatus.CONFIRMED:
            raise ValueError("Cannot issue ticket for non-confirmed booking")
        self.status = BookingStatus.TICKETED
        self.ticket_number = ticket_number
        self.ticketing_date = timezone.now()
        self.save(update_fields=['status', 'ticket_number', 'ticketing_date'])

    def cancel_booking(self, reason=None):
        """Cancel the booking"""
        from django.utils import timezone
        self.status = BookingStatus.CANCELLED
        self.cancellation_date = timezone.now()
        self.cancellation_reason = reason
        self.save(update_fields=['status', 'cancellation_date', 'cancellation_reason'])


class HotelBooking(models.Model):
    """
    Hotel booking model for managing hotel reservations linked to TRFs.
    Supports room preferences, special requests, and check-in/out tracking.
    """
    # Core Relations
    trf = models.ForeignKey(
        TravelRequest,
        on_delete=models.CASCADE,
        related_name='hotel_bookings',
        help_text="Travel request this booking is for"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hotel_bookings',
        help_text="Guest for this booking"
    )

    # Hotel Information
    hotel_name = models.CharField(max_length=200, help_text="Hotel name")
    hotel_chain = models.CharField(max_length=100, blank=True, null=True, help_text="Hotel chain (e.g., Marriott, Hilton)")
    location = models.CharField(max_length=200, help_text="Hotel location/city")
    address = models.TextField(blank=True, null=True, help_text="Full hotel address")
    contact_number = models.CharField(max_length=50, blank=True, null=True, help_text="Hotel contact number")
    email = models.EmailField(blank=True, null=True, help_text="Hotel email")

    # Booking Dates
    check_in_date = models.DateField(help_text="Check-in date")
    check_out_date = models.DateField(help_text="Check-out date")
    check_in_time = models.TimeField(blank=True, null=True, help_text="Expected check-in time")
    check_out_time = models.TimeField(blank=True, null=True, help_text="Expected check-out time")

    # Room Details
    room_type = models.CharField(max_length=100, help_text="Room type (e.g., Standard, Deluxe, Suite)")
    number_of_rooms = models.PositiveIntegerField(default=1, help_text="Number of rooms")
    number_of_guests = models.PositiveIntegerField(default=1, help_text="Number of guests")
    bed_preference = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Bed preference (e.g., King, Twin, Double)"
    )
    smoking_preference = models.BooleanField(default=False, help_text="Smoking room preference")

    # Status and References
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
        help_text="Current booking status"
    )
    booking_reference = models.CharField(max_length=50, unique=True, help_text="Hotel booking reference/confirmation number")

    # Cost Information
    cost_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Cost per night"
    )
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total booking cost"
    )
    currency = models.CharField(max_length=3, default='USD', help_text="Currency code (ISO 4217)")
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Tax amount"
    )
    service_charges = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Service charges"
    )

    # Amenities and Services
    breakfast_included = models.BooleanField(default=False, help_text="Breakfast included")
    wifi_included = models.BooleanField(default=True, help_text="WiFi included")
    parking_included = models.BooleanField(default=False, help_text="Parking included")
    airport_transfer = models.BooleanField(default=False, help_text="Airport transfer included")

    # Special Requests and Notes
    special_requests = models.TextField(blank=True, null=True, help_text="Special requests or requirements")
    dietary_requirements = models.TextField(blank=True, null=True, help_text="Dietary requirements for meals")

    # Admin and Processing
    booked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hotels_booked',
        help_text="Admin/Travel desk who made the booking"
    )
    booking_date = models.DateTimeField(null=True, blank=True, help_text="Date booking was created")
    confirmation_date = models.DateTimeField(null=True, blank=True, help_text="Date booking was confirmed")
    cancellation_date = models.DateTimeField(null=True, blank=True, help_text="Date booking was cancelled")
    cancellation_reason = models.TextField(blank=True, null=True, help_text="Reason for cancellation")

    # Payment Information
    payment_method = models.CharField(max_length=50, blank=True, null=True, help_text="Payment method")
    is_prepaid = models.BooleanField(default=False, help_text="Whether booking is prepaid")

    # Additional Information
    notes = models.TextField(blank=True, null=True, help_text="Internal notes")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['trf', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['booking_reference']),
            models.Index(fields=['check_in_date', 'check_out_date']),
        ]

    def __str__(self):
        return f"{self.hotel_name} - {self.user.get_full_name()} ({self.check_in_date} to {self.check_out_date})"

    @property
    def user_id(self):
        return self.user.id

    @property
    def trf_id(self):
        return self.trf.id

    @property
    def number_of_nights(self):
        """Calculate number of nights"""
        return (self.check_out_date - self.check_in_date).days

    @property
    def grand_total(self):
        """Total cost including taxes and service charges"""
        return self.total_cost + self.tax_amount + self.service_charges

    def confirm_booking(self):
        """Mark booking as confirmed"""
        from django.utils import timezone
        self.status = BookingStatus.CONFIRMED
        self.confirmation_date = timezone.now()
        self.save(update_fields=['status', 'confirmation_date'])

    def cancel_booking(self, reason=None):
        """Cancel the booking"""
        from django.utils import timezone
        self.status = BookingStatus.CANCELLED
        self.cancellation_date = timezone.now()
        self.cancellation_reason = reason
        self.save(update_fields=['status', 'cancellation_date', 'cancellation_reason'])
