from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from trf.models import TravelRequestForm


class BookingClass(models.TextChoices):
    ECONOMY = 'ECONOMY', _('Economy')
    PREMIUM_ECONOMY = 'PREMIUM_ECONOMY', _('Premium Economy')
    BUSINESS = 'BUSINESS', _('Business')
    FIRST = 'FIRST', _('First')


class BookingStatus(models.TextChoices):
    REQUESTED = 'REQUESTED', _('Requested')
    CONFIRMED = 'CONFIRMED', _('Confirmed')
    CANCELLED = 'CANCELLED', _('Cancelled')


class FlightBooking(models.Model):
    trf = models.ForeignKey(TravelRequestForm, on_delete=models.CASCADE, related_name='flight_bookings')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='flight_bookings')
    airline = models.CharField(max_length=100)
    flight_number = models.CharField(max_length=20)
    departure_airport = models.CharField(max_length=100)
    arrival_airport = models.CharField(max_length=100)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    booking_class = models.CharField(
        max_length=20,
        choices=BookingClass.choices,
        default=BookingClass.ECONOMY,
    )
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.REQUESTED,
    )
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    booking_reference = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.airline} {self.flight_number} for {self.user.name}"
    
    @property
    def user_id(self):
        return self.user.id
    
    @property
    def trf_id(self):
        return self.trf.id


class HotelBooking(models.Model):
    trf = models.ForeignKey(TravelRequestForm, on_delete=models.CASCADE, related_name='hotel_bookings')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hotel_bookings')
    hotel_name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    room_type = models.CharField(max_length=50)
    number_of_rooms = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.REQUESTED,
    )
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    booking_reference = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.hotel_name} for {self.user.name}"
    
    @property
    def user_id(self):
        return self.user.id
    
    @property
    def trf_id(self):
        return self.trf.id
