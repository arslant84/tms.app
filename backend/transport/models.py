from django.db import models
from django.conf import settings
from trf.models import TravelRequest


class TransportRequest(models.Model):
    """Main transport request model"""

    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    TRANSPORT_TYPE_CHOICES = [
        ('Company Vehicle', 'Company Vehicle'),
        ('Hired Vehicle', 'Hired Vehicle'),
        ('Personal Vehicle', 'Personal Vehicle'),
        ('Public Transport', 'Public Transport'),
    ]

    requestor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transport_requests'
    )
    trf = models.ForeignKey(
        TravelRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transport_requests'
    )

    # Request details
    title = models.CharField(max_length=255)
    purpose = models.TextField()
    transport_type = models.CharField(max_length=50, choices=TRANSPORT_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')

    # Passenger information
    number_of_passengers = models.IntegerField(default=1)
    passenger_names = models.TextField(blank=True, null=True, help_text="Comma-separated list of passengers")

    # Vehicle preferences
    vehicle_type = models.CharField(max_length=100, blank=True, null=True)
    special_requirements = models.TextField(blank=True, null=True)

    # Cost estimation
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')

    # Additional info
    additional_comments = models.TextField(blank=True, null=True)
    additional_data = models.JSONField(blank=True, null=True)

    # Timestamps
    submitted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.requestor.email}"


class TransportSegment(models.Model):
    """Individual transport segment/leg within a transport request"""

    transport_request = models.ForeignKey(
        TransportRequest,
        on_delete=models.CASCADE,
        related_name='segments'
    )

    # Journey details
    from_location = models.CharField(max_length=255)
    to_location = models.CharField(max_length=255)
    departure_date = models.DateField()
    departure_time = models.TimeField()
    arrival_date = models.DateField(blank=True, null=True)
    arrival_time = models.TimeField(blank=True, null=True)

    # Route information
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    estimated_duration_hours = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
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
        ordering = ['departure_date', 'departure_time']

    def __str__(self):
        return f"{self.from_location} → {self.to_location} on {self.departure_date}"


class TransportApprovalStep(models.Model):
    """Approval workflow tracking for transport requests"""

    transport_request = models.ForeignKey(
        TransportRequest,
        on_delete=models.CASCADE,
        related_name='approval_steps'
    )

    step_role = models.CharField(max_length=255)
    step_name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, default='Pending')
    step_date = models.DateTimeField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transport_request.title} - {self.step_role}: {self.status}"


class VehicleAssignment(models.Model):
    """Track vehicle assignments to transport requests"""

    STATUS_CHOICES = [
        ('Assigned', 'Assigned'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    transport_request = models.ForeignKey(
        TransportRequest,
        on_delete=models.CASCADE,
        related_name='vehicle_assignments'
    )

    # Vehicle details
    vehicle_number = models.CharField(max_length=50)
    vehicle_type = models.CharField(max_length=100)
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
        related_name='vehicle_assignments_made'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Assigned')

    # Tracking
    odometer_start = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    odometer_end = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    fuel_used_liters = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)

    # Timestamps
    assignment_date = models.DateTimeField(auto_now_add=True)
    completion_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.vehicle_number} - {self.transport_request.title}"
