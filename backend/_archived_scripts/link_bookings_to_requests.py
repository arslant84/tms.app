"""
Script to link existing AccommodationBookings to AccommodationRequests
based on the TRF (TravelRequest) relationship
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tms_project.settings')
django.setup()

from accommodation.models import AccommodationBooking, AccommodationRequest

def link_bookings_to_requests():
    """Link existing bookings to accommodation requests"""

    # Get all bookings without an accommodation_request
    bookings_without_request = AccommodationBooking.objects.filter(accommodation_request__isnull=True)

    print(f"Found {bookings_without_request.count()} bookings without accommodation_request")

    updated_count = 0

    for booking in bookings_without_request:
        # Try to find the accommodation request for this booking
        # First, try by TRF
        if booking.trf:
            accommodation_requests = AccommodationRequest.objects.filter(trf=booking.trf)

            if accommodation_requests.count() == 1:
                # Single match - link it
                booking.accommodation_request = accommodation_requests.first()
                booking.save()
                updated_count += 1
                print(f"✓ Linked booking {booking.id} to accommodation request {booking.accommodation_request.id}")
            elif accommodation_requests.count() > 1:
                # Multiple matches - find the one with status "Accommodation Assigned"
                assigned_request = accommodation_requests.filter(status='Accommodation Assigned').first()
                if assigned_request:
                    booking.accommodation_request = assigned_request
                    booking.save()
                    updated_count += 1
                    print(f"✓ Linked booking {booking.id} to accommodation request {assigned_request.id} (multiple matches, chose assigned one)")
                else:
                    print(f"⚠ Booking {booking.id} has multiple accommodation requests for TRF {booking.trf.id}, skipping")
            else:
                print(f"⚠ Booking {booking.id} has TRF {booking.trf.id} but no matching accommodation request found")
        else:
            print(f"⚠ Booking {booking.id} has no TRF, cannot link to accommodation request")

    print(f"\n✅ Updated {updated_count} bookings")

if __name__ == '__main__':
    link_bookings_to_requests()
