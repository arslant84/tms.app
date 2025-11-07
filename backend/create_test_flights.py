from decimal import Decimal
from trf.models import TravelRequest, TrfItinerarySegment
from bookings.models import FlightBooking
from datetime import datetime
from django.utils import timezone

# Create TRF with flight booking
trf2 = TravelRequest.objects.create(
    requestor_name='Michael Chen',
    staff_id='EMP006',
    department='Finance',
    position='Senior Accountant',
    email='michael@example.com',
    travel_type='Overseas',
    status='Approved',
    purpose='Financial audit in Istanbul'
)

# Add itinerary
TrfItinerarySegment.objects.create(
    trf=trf2,
    segment_date=datetime(2025, 11, 18).date(),
    from_location='Ashgabat',
    to_location='Istanbul',
    departure_time='08:00',
    arrival_time='12:00'
)

# Create flight booking for trf2
flight = FlightBooking.objects.create(
    trf=trf2,
    airline='Turkish Airlines',
    flight_number='TK123',
    departure_airport='ASB',
    arrival_airport='IST',
    departure_time=timezone.make_aware(datetime(2025, 11, 18, 8, 0)),
    arrival_time=timezone.make_aware(datetime(2025, 11, 18, 12, 0)),
    booking_reference='PNR12345',
    status='Confirmed',
    cost=Decimal('850.00'),
    notes='Economy class, 1 checked bag included'
)

print(f'✓ Created TRF {trf2.id}: {trf2.request_number} - Approved WITH flight booking')
print(f'  Flight: {flight.airline} {flight.flight_number} | Cost: ${flight.cost}')

# Create Home Leave TRF with booking
trf3 = TravelRequest.objects.create(
    requestor_name='Emma Wilson',
    staff_id='EMP007',
    department='Operations',
    position='Operations Coordinator',
    email='emma@example.com',
    travel_type='Home Leave Passage',
    status='Approved',
    purpose='Annual home leave'
)

# Add itinerary
TrfItinerarySegment.objects.create(
    trf=trf3,
    segment_date=datetime(2025, 12, 1).date(),
    from_location='Ashgabat',
    to_location='London',
    departure_time='14:30',
    arrival_time='19:45'
)

# Create flight booking
flight2 = FlightBooking.objects.create(
    trf=trf3,
    airline='Turkmenistan Airlines',
    flight_number='T5201',
    departure_airport='ASB',
    arrival_airport='LHR',
    departure_time=timezone.make_aware(datetime(2025, 12, 1, 14, 30)),
    arrival_time=timezone.make_aware(datetime(2025, 12, 1, 19, 45)),
    booking_reference='PNR67890',
    status='Confirmed',
    cost=Decimal('1250.00'),
    notes='Business class'
)

print(f'✓ Created TRF {trf3.id}: {trf3.request_number} - Home Leave WITH flight booking')
print(f'  Flight: {flight2.airline} {flight2.flight_number} | Cost: ${flight2.cost}')

print('\n=== SUMMARY ===')
print(f'Total TRFs: {TravelRequest.objects.count()}')
print(f'TRFs with flight bookings: {FlightBooking.objects.values("trf").distinct().count()}')
