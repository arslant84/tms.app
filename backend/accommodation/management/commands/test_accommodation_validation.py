"""
Test script for accommodation request TSR linking validations

This script tests two validation rules:
1. One TSR can only be linked to one accommodation request
2. Check-in/check-out dates must be within TSR itinerary dates

Usage:
    python manage.py test_accommodation_validation
"""

from django.core.management.base import BaseCommand
from accommodation.models import AccommodationRequest
from accommodation.serializers import AccommodationRequestSerializer
from trf.models import TravelRequest, TrfItinerarySegment
from datetime import timedelta


class Command(BaseCommand):
    help = 'Test accommodation request TSR linking validations'

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*80)
        self.stdout.write("Testing Accommodation Request TSR Linking Validations")
        self.stdout.write("="*80 + "\n")

        self.test_duplicate_tsr_link()
        self.test_date_range_validation()

        self.stdout.write("\n" + "="*80)
        self.stdout.write("Validation Tests Complete")
        self.stdout.write("="*80 + "\n")

    def test_duplicate_tsr_link(self):
        """Test 1: One TSR can only be linked to one accommodation request"""
        self.stdout.write("\nTEST 1: One TSR can only be linked to one accommodation request")
        self.stdout.write("-" * 80)

        # Get a TSR that already has an accommodation request
        existing_accom = AccommodationRequest.objects.filter(trf__isnull=False).first()

        if existing_accom:
            tsr = existing_accom.trf
            self.stdout.write(self.style.SUCCESS(
                f"✓ Found existing accommodation request: {existing_accom.request_number}"
            ))
            self.stdout.write(f"  Linked to TSR: {tsr.request_number}")

            # Try to create a new accommodation request with the same TSR
            test_data = {
                'requestor_name': 'Test User',
                'trf': tsr.id,
                'status': 'Draft',
                'additional_data': {}
            }

            serializer = AccommodationRequestSerializer(data=test_data)
            if serializer.is_valid():
                self.stdout.write(self.style.ERROR(
                    "✗ VALIDATION FAILED: Should not allow linking same TSR to multiple requests"
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    "✓ VALIDATION PASSED: Correctly prevented duplicate TSR link"
                ))
                error_msg = str(serializer.errors.get('trf', [''])[0])
                self.stdout.write(f"  Error: {error_msg}")
        else:
            self.stdout.write(self.style.WARNING(
                "⚠ SKIPPED: No existing accommodation requests with TSR found"
            ))

    def test_date_range_validation(self):
        """Test 2: Check-in/check-out dates must be within TSR itinerary dates"""
        self.stdout.write("\n\nTEST 2: Check-in/check-out dates must be within TSR itinerary dates")
        self.stdout.write("-" * 80)

        # Get a TSR with itinerary segments that is not already linked
        tsr_with_itinerary = TravelRequest.objects.filter(
            trfitinerarysegment__isnull=False
        ).exclude(
            id__in=AccommodationRequest.objects.filter(trf__isnull=False).values_list('trf_id', flat=True)
        ).first()

        if tsr_with_itinerary:
            segments = TrfItinerarySegment.objects.filter(
                trf=tsr_with_itinerary,
                segment_date__isnull=False
            ).order_by('segment_date')

            if segments.exists():
                first_date = segments.first().segment_date
                last_date = segments.last().segment_date

                self.stdout.write(self.style.SUCCESS(
                    f"✓ Found TSR with itinerary: {tsr_with_itinerary.request_number}"
                ))
                self.stdout.write(f"  TSR Date Range: {first_date} to {last_date}")

                # Test 2a: Valid dates within range
                self.test_valid_dates_within_range(tsr_with_itinerary, first_date, last_date)

                # Test 2b: Check-in date before TSR start date
                self.test_check_in_before_tsr_start(tsr_with_itinerary, first_date, last_date)

                # Test 2c: Check-out date after TSR end date
                self.test_check_out_after_tsr_end(tsr_with_itinerary, first_date, last_date)
            else:
                self.stdout.write(self.style.WARNING(
                    "⚠ SKIPPED: TSR has no itinerary segments with dates"
                ))
        else:
            self.stdout.write(self.style.WARNING(
                "⚠ SKIPPED: No available TSR with itinerary segments found"
            ))

    def test_valid_dates_within_range(self, tsr, first_date, last_date):
        """Test 2a: Valid dates within range"""
        self.stdout.write("\n  Test 2a: Valid dates within range")

        test_data = {
            'requestor_name': 'Test User',
            'trf': tsr.id,
            'status': 'Draft',
            'additional_data': {
                'check_in_date': first_date.strftime('%Y-%m-%d'),
                'check_out_date': last_date.strftime('%Y-%m-%d')
            }
        }

        serializer = AccommodationRequestSerializer(data=test_data)
        if serializer.is_valid():
            self.stdout.write(self.style.SUCCESS(
                "  ✓ VALIDATION PASSED: Accepted dates within range"
            ))
        else:
            self.stdout.write(self.style.ERROR(
                "  ✗ VALIDATION FAILED: Should accept dates within range"
            ))
            self.stdout.write(f"    Error: {serializer.errors}")

    def test_check_in_before_tsr_start(self, tsr, first_date, last_date):
        """Test 2b: Check-in date before TSR start date"""
        self.stdout.write("\n  Test 2b: Check-in date before TSR start date")

        invalid_check_in = (first_date - timedelta(days=1)).strftime('%Y-%m-%d')

        test_data = {
            'requestor_name': 'Test User',
            'trf': tsr.id,
            'status': 'Draft',
            'additional_data': {
                'check_in_date': invalid_check_in,
                'check_out_date': last_date.strftime('%Y-%m-%d')
            }
        }

        serializer = AccommodationRequestSerializer(data=test_data)
        if serializer.is_valid():
            self.stdout.write(self.style.ERROR(
                "  ✗ VALIDATION FAILED: Should not accept check-in before TSR start"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "  ✓ VALIDATION PASSED: Correctly rejected check-in before TSR start"
            ))
            error_msg = str(serializer.errors.get('additional_data', [''])[0])
            self.stdout.write(f"    Error: {error_msg}")

    def test_check_out_after_tsr_end(self, tsr, first_date, last_date):
        """Test 2c: Check-out date after TSR end date"""
        self.stdout.write("\n  Test 2c: Check-out date after TSR end date")

        invalid_check_out = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')

        test_data = {
            'requestor_name': 'Test User',
            'trf': tsr.id,
            'status': 'Draft',
            'additional_data': {
                'check_in_date': first_date.strftime('%Y-%m-%d'),
                'check_out_date': invalid_check_out
            }
        }

        serializer = AccommodationRequestSerializer(data=test_data)
        if serializer.is_valid():
            self.stdout.write(self.style.ERROR(
                "  ✗ VALIDATION FAILED: Should not accept check-out after TSR end"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "  ✓ VALIDATION PASSED: Correctly rejected check-out after TSR end"
            ))
            error_msg = str(serializer.errors.get('additional_data', [''])[0])
            self.stdout.write(f"    Error: {error_msg}")
