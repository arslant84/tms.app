from django.conf import settings
from django.db import models
from trf.models import TravelRequest


class TransportRequest(models.Model):
    """
    Main transport request model
    Matches React source project structure - NO cost fields
    """

    # Note: STATUS_CHOICES removed to support dynamic workflow statuses
    # Status will be set by workflow engine based on configured approval roles
    # Examples: "Draft", "Pending HOD", "Pending Line Manager", "Approved", etc.

    request_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text="Auto-generated request number (e.g., TRN-20251102-1423-ASH-PCYX)",
    )
    requestor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transport_requests",
    )
    trf = models.ForeignKey(
        TravelRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transport_requests",
    )

    # Requestor information (embedded for display)
    requestor_name = models.CharField(max_length=255)
    staff_id = models.CharField(max_length=50)
    department = models.CharField(max_length=255)
    position = models.CharField(max_length=255)

    # Request details
    purpose = models.TextField()
    tsr_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="TSR Reference if created from TSR",
    )
    status = models.CharField(
        max_length=100,
        default="Draft",
        help_text="Dynamic status set by workflow engine",
    )

    # Transport details array (stored as JSON)
    # Each item has: date, day, from, to, departureTime, numberOfPassengers
    transport_details = models.JSONField(
        default=list, help_text="Array of transport detail objects"
    )

    # Approval submission data
    additional_comments = models.TextField(blank=True, null=True)
    confirm_policy = models.BooleanField(default=False)
    confirm_manager_approval = models.BooleanField(default=False)
    confirm_terms_and_conditions = models.BooleanField(default=False)

    # Booking details (filled by transport admin)
    booking_details = models.JSONField(
        blank=True, null=True, help_text="Booking details filled by transport admin"
    )

    # Timestamps
    submitted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.requestor_name} - {self.purpose[:50]}"


class TransportSegment(models.Model):
    """Individual transport segment/leg within a transport request"""

    transport_request = models.ForeignKey(
        TransportRequest, on_delete=models.CASCADE, related_name="segments"
    )

    # Journey details
    from_location = models.CharField(max_length=255)
    to_location = models.CharField(max_length=255)
    departure_date = models.DateField()
    departure_time = models.TimeField()
    arrival_date = models.DateField(blank=True, null=True)
    arrival_time = models.TimeField(blank=True, null=True)

    # Route information
    distance_km = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True
    )
    estimated_duration_hours = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    route_description = models.TextField(blank=True, null=True)

    # Vehicle assignment (for company vehicles)
    vehicle_number = models.CharField(max_length=50, blank=True, null=True)
    driver_name = models.CharField(max_length=255, blank=True, null=True)
    driver_contact = models.CharField(max_length=50, blank=True, null=True)

    # Cost tracking
    segment_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Additional info
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["departure_date", "departure_time"]

    def __str__(self):
        return f"{self.from_location} → {self.to_location} on {self.departure_date}"


class TransportApprovalStep(models.Model):
    """Approval workflow tracking for transport requests"""

    transport_request = models.ForeignKey(
        TransportRequest, on_delete=models.CASCADE, related_name="approval_steps"
    )

    step_role = models.CharField(max_length=255)
    step_name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, default="Pending")
    step_date = models.DateTimeField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.transport_request.title} - {self.step_role}: {self.status}"


class VehicleAssignment(models.Model):
    """Track vehicle assignments to transport requests"""

    STATUS_CHOICES = [
        ("Assigned", "Assigned"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    ]

    transport_request = models.ForeignKey(
        TransportRequest, on_delete=models.CASCADE, related_name="vehicle_assignments"
    )

    # Vehicle details
    vehicle_number = models.CharField(max_length=50)
    vehicle_type = models.CharField(max_length=100, blank=True, null=True)
    vehicle_capacity = models.IntegerField(default=4)

    # Driver details
    driver_name = models.CharField(max_length=255)
    driver_contact = models.CharField(max_length=50)
    driver_license = models.CharField(max_length=100, blank=True, null=True)

    # Assignment details
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vehicle_assignments_made",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Assigned")

    # Tracking
    odometer_start = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    odometer_end = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    fuel_used_liters = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True
    )

    # Timestamps
    assignment_date = models.DateTimeField(auto_now_add=True)
    completion_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.vehicle_number} - {self.transport_request.title}"
