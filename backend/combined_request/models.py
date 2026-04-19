"""
Combined Request Models

This module contains all models for the Combined Request feature,
which allows users to apply for TSR, Transport, Accommodation, and Visa
in a single unified request.
"""

from django.db import models
from django.conf import settings


class CombinedRequest(models.Model):
    """
    Unified request combining TSR, Transport, Accommodation, and Visa.
    Uses a single workflow with conditional steps based on included modules.
    """

    # ===== REQUEST IDENTIFICATION =====
    request_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text="Auto-generated request number (e.g., CMB-20250415-0930-DXB-A7K2)"
    )

    # ===== REQUESTOR INFORMATION (Shared across all modules) =====
    requestor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='combined_requests'
    )
    requestor_name = models.CharField(max_length=255)
    staff_id = models.CharField(max_length=50, blank=True, null=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    position = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    cost_center = models.CharField(max_length=100, blank=True, null=True)

    # ===== MODULE INCLUSION FLAGS =====
    include_travel = models.BooleanField(default=True, help_text="Include Travel/TSR in this request")
    include_transport = models.BooleanField(default=False, help_text="Include Transport in this request")
    include_accommodation = models.BooleanField(default=False, help_text="Include Accommodation in this request")
    include_visa = models.BooleanField(default=False, help_text="Include Visa in this request")

    # ===== TRAVEL/TSR SECTION =====
    travel_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Type: domestic, international, home_leave, external"
    )
    trip_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        default='Round Trip',
        help_text="One Way / Round Trip"
    )
    travel_purpose = models.TextField(blank=True, null=True)
    departure_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    destination_country = models.CharField(max_length=100, blank=True, null=True)
    destination_city = models.CharField(max_length=100, blank=True, null=True)
    travel_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Stores meal_selections list and advance_amount_items list"
    )

    # ===== BANK / ADVANCE PAYMENT DETAILS =====
    advance_bank_account_name = models.CharField(max_length=255, blank=True, null=True)
    advance_bank_name = models.CharField(max_length=255, blank=True, null=True)
    advance_bank_account_number = models.CharField(max_length=100, blank=True, null=True)
    advance_bank_currency = models.CharField(max_length=10, blank=True, null=True, default='TMT')
    advance_bank_branch_remarks = models.TextField(blank=True, null=True)

    # ===== EXTERNAL PARTY INFORMATION =====
    external_full_name = models.CharField(max_length=255, blank=True, null=True)
    external_organization = models.CharField(max_length=255, blank=True, null=True)
    external_ref_to_authority_letter = models.CharField(max_length=255, blank=True, null=True)
    external_cost_center = models.CharField(max_length=100, blank=True, null=True)

    # ===== TRANSPORT SECTION =====
    transport_purpose = models.TextField(blank=True, null=True, help_text="Purpose / reason for transport")
    transport_tsr_reference = models.CharField(max_length=100, blank=True, null=True, help_text="Related TSR reference number")
    transport_required_from = models.DateTimeField(null=True, blank=True)
    transport_required_to = models.DateTimeField(null=True, blank=True)
    transport_pickup_location = models.CharField(max_length=500, blank=True, null=True)
    transport_dropoff_location = models.CharField(max_length=500, blank=True, null=True)
    transport_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional transport data (vehicle preferences, special requirements)"
    )

    # ===== ACCOMMODATION SECTION =====
    accommodation_gender = models.CharField(max_length=20, blank=True, null=True, help_text="Requestor gender for room allocation")
    accommodation_checkin = models.DateField(null=True, blank=True)
    accommodation_checkout = models.DateField(null=True, blank=True)
    accommodation_location = models.CharField(max_length=500, blank=True, null=True)
    accommodation_room_type = models.CharField(max_length=100, blank=True, null=True)
    accommodation_flight_arrival_time = models.CharField(max_length=50, blank=True, null=True)
    accommodation_flight_departure_time = models.CharField(max_length=50, blank=True, null=True)
    accommodation_special_requests = models.TextField(blank=True, null=True)
    accommodation_guests = models.IntegerField(default=1)
    accommodation_preferences = models.TextField(blank=True, null=True)
    accommodation_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional accommodation data (overflow)"
    )

    # ===== VISA SECTION =====
    visa_destination_country = models.CharField(max_length=100, blank=True, null=True)
    visa_type = models.CharField(max_length=50, blank=True, null=True)
    passport_number = models.CharField(max_length=50, blank=True, null=True)
    passport_expiry = models.DateField(null=True, blank=True)

    # Applicant particulars
    visa_date_of_birth = models.DateField(null=True, blank=True)
    visa_place_of_birth = models.CharField(max_length=255, blank=True, null=True)
    visa_citizenship = models.CharField(max_length=100, blank=True, null=True)
    visa_contact_telephone = models.CharField(max_length=50, blank=True, null=True)
    visa_marital_status = models.CharField(max_length=50, blank=True, null=True)
    visa_home_address = models.TextField(blank=True, null=True)
    visa_family_information = models.TextField(blank=True, null=True)
    visa_education_details = models.TextField(blank=True, null=True)

    # Passport details
    visa_passport_number = models.CharField(max_length=50, blank=True, null=True)
    visa_passport_expiry_date = models.DateField(null=True, blank=True)
    visa_passport_place_of_issuance = models.CharField(max_length=255, blank=True, null=True)
    visa_passport_date_of_issuance = models.DateField(null=True, blank=True)

    # Employment
    visa_current_employer_name = models.CharField(max_length=255, blank=True, null=True)
    visa_current_employer_address = models.TextField(blank=True, null=True)

    # Type of request
    visa_request_type = models.CharField(max_length=50, blank=True, null=True, default='VISA')
    visa_approximately_arrival_date = models.DateField(null=True, blank=True)
    visa_duration_of_stay = models.CharField(max_length=100, blank=True, null=True)
    visa_entry_type = models.CharField(max_length=50, blank=True, null=True)
    visa_work_visit_category = models.CharField(max_length=100, blank=True, null=True)
    visa_application_fees_borne_by = models.CharField(max_length=255, blank=True, null=True)
    visa_cost_centre_number = models.CharField(max_length=100, blank=True, null=True)

    # Travel details
    visa_trf_reference_number = models.CharField(max_length=100, blank=True, null=True)
    visa_trip_start_date = models.DateField(null=True, blank=True)
    visa_trip_end_date = models.DateField(null=True, blank=True)
    visa_travel_purpose = models.TextField(blank=True, null=True)
    visa_itinerary_details = models.TextField(blank=True, null=True)

    # Additional
    visa_additional_comments = models.TextField(blank=True, null=True)
    visa_supporting_documents_notes = models.TextField(blank=True, null=True)

    visa_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional visa data overflow"
    )

    # ===== OVERALL STATUS & WORKFLOW =====
    status = models.CharField(
        max_length=100,
        default='Draft',
        help_text="Overall workflow status set by workflow engine"
    )

    # Module-specific statuses for tracking/visibility
    travel_status = models.CharField(
        max_length=50,
        default='pending',
        help_text="Travel module status: not_requested, pending, approved, processing, completed"
    )
    transport_status = models.CharField(
        max_length=50,
        default='not_requested',
        help_text="Transport module status"
    )
    accommodation_status = models.CharField(
        max_length=50,
        default='not_requested',
        help_text="Accommodation module status"
    )
    visa_status = models.CharField(
        max_length=50,
        default='not_requested',
        help_text="Visa module status"
    )

    # ===== COMMENTS & ADDITIONAL DATA =====
    additional_comments = models.TextField(blank=True, null=True)
    additional_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Flexible storage for workflow data (selected_approvers, skipped_steps, etc.)"
    )

    # ===== TIMESTAMPS =====
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'combined_request'
        ordering = ['-created_at']
        verbose_name = 'Combined Request'
        verbose_name_plural = 'Combined Requests'

    def __str__(self):
        modules = []
        if self.include_travel:
            modules.append('TSR')
        if self.include_transport:
            modules.append('Transport')
        if self.include_accommodation:
            modules.append('Accommodation')
        if self.include_visa:
            modules.append('Visa')
        module_str = '+'.join(modules) if modules else 'None'
        return f"{self.request_number or 'Draft'} - {self.requestor_name} [{module_str}]"

    def get_included_modules(self):
        """Returns a list of included module names."""
        modules = []
        if self.include_travel:
            modules.append('travel')
        if self.include_transport:
            modules.append('transport')
        if self.include_accommodation:
            modules.append('accommodation')
        if self.include_visa:
            modules.append('visa')
        return modules

    def save(self, *args, **kwargs):
        """Override save to update module statuses based on inclusion flags."""
        # Set module statuses to 'not_requested' if module is not included
        if not self.include_travel:
            self.travel_status = 'not_requested'
        elif self.travel_status == 'not_requested':
            self.travel_status = 'pending'

        if not self.include_transport:
            self.transport_status = 'not_requested'
        elif self.transport_status == 'not_requested':
            self.transport_status = 'pending'

        if not self.include_accommodation:
            self.accommodation_status = 'not_requested'
        elif self.accommodation_status == 'not_requested':
            self.accommodation_status = 'pending'

        if not self.include_visa:
            self.visa_status = 'not_requested'
        elif self.visa_status == 'not_requested':
            self.visa_status = 'pending'

        super().save(*args, **kwargs)


class CombinedRequestPassport(models.Model):
    """Passport details for combined request (for both travel and visa modules)."""

    combined_request = models.ForeignKey(
        CombinedRequest,
        on_delete=models.CASCADE,
        related_name='passports'
    )
    full_name = models.CharField(max_length=255)
    passport_number = models.CharField(max_length=50)
    nationality = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    place_of_birth = models.CharField(max_length=255, blank=True, null=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    passport_file = models.FileField(
        upload_to='combined_request/passports/',
        null=True,
        blank=True,
        help_text="Uploaded passport scan/photo"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'combined_request'
        verbose_name = 'Passport Detail'
        verbose_name_plural = 'Passport Details'

    def __str__(self):
        return f"{self.full_name} - {self.passport_number}"


class CombinedRequestItinerary(models.Model):
    """Itinerary segments for combined request travel section."""

    combined_request = models.ForeignKey(
        CombinedRequest,
        on_delete=models.CASCADE,
        related_name='itinerary_segments'
    )
    segment_order = models.PositiveIntegerField(default=1)
    segment_date = models.DateField(null=True, blank=True)
    day_of_week = models.CharField(max_length=20, blank=True, null=True)
    from_location = models.CharField(max_length=255)
    to_location = models.CharField(max_length=255)
    departure_time = models.TimeField(null=True, blank=True)
    arrival_time = models.TimeField(null=True, blank=True)
    mode_of_travel = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="flight, train, bus, car, etc."
    )
    flight_number = models.CharField(max_length=50, blank=True, null=True)
    flight_class = models.CharField(max_length=50, blank=True, null=True)
    purpose = models.TextField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'combined_request'
        ordering = ['segment_order', 'segment_date']
        verbose_name = 'Itinerary Segment'
        verbose_name_plural = 'Itinerary Segments'

    def __str__(self):
        return f"{self.from_location} → {self.to_location} ({self.segment_date})"


class CombinedRequestTransportSegment(models.Model):
    """Transport segments for combined request transport section."""

    combined_request = models.ForeignKey(
        CombinedRequest,
        on_delete=models.CASCADE,
        related_name='transport_segments'
    )
    segment_order = models.PositiveIntegerField(default=1)
    day_of_week = models.CharField(max_length=20, blank=True, null=True)
    transport_type = models.CharField(max_length=50, blank=True, null=True, help_text="car, van, bus, etc.")
    pickup_location = models.CharField(max_length=500)
    dropoff_location = models.CharField(max_length=500)
    pickup_date = models.DateField(null=True, blank=True)
    pickup_time = models.TimeField(null=True, blank=True)
    passengers = models.IntegerField(default=1)
    vehicle_type_preference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="sedan, suv, van, bus, etc."
    )
    notes = models.TextField(blank=True, null=True)

    # Admin assignment fields (filled during processing)
    vehicle_number = models.CharField(max_length=50, blank=True, null=True)
    driver_name = models.CharField(max_length=255, blank=True, null=True)
    driver_contact = models.CharField(max_length=50, blank=True, null=True)
    segment_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'combined_request'
        ordering = ['segment_order', 'pickup_date', 'pickup_time']
        verbose_name = 'Transport Segment'
        verbose_name_plural = 'Transport Segments'

    def __str__(self):
        return f"{self.pickup_location} → {self.dropoff_location} ({self.pickup_date})"


class CombinedRequestDocument(models.Model):
    """Supporting documents for combined request."""

    DOCUMENT_TYPES = [
        ('passport', 'Passport Copy'),
        ('visa_photo', 'Visa Photo'),
        ('invitation_letter', 'Invitation Letter'),
        ('flight_ticket', 'Flight Ticket'),
        ('hotel_booking', 'Hotel Booking'),
        ('travel_insurance', 'Travel Insurance'),
        ('supporting_doc', 'Supporting Document'),
        ('other', 'Other'),
    ]

    MODULE_CHOICES = [
        ('travel', 'Travel'),
        ('transport', 'Transport'),
        ('accommodation', 'Accommodation'),
        ('visa', 'Visa'),
        ('general', 'General'),
    ]

    combined_request = models.ForeignKey(
        CombinedRequest,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    module = models.CharField(max_length=20, choices=MODULE_CHOICES, default='general')
    file = models.FileField(upload_to='combined_request/documents/')
    file_name = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'combined_request'
        ordering = ['module', 'document_type', '-uploaded_at']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.module}"


class CombinedRequestApprovalStep(models.Model):
    """
    Approval tracking for combined request.
    Note: This is supplementary to the main WorkflowStepExecution model.
    Used for quick reference and historical tracking.
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('skipped', 'Skipped'),
    ]

    combined_request = models.ForeignKey(
        CombinedRequest,
        on_delete=models.CASCADE,
        related_name='approval_steps'
    )
    step_order = models.PositiveIntegerField()
    step_name = models.CharField(max_length=100)
    step_role = models.CharField(max_length=100, blank=True, null=True)
    module = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Which module this step is for (travel, transport, accommodation, visa, or null for general)"
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='combined_approval_actions'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    comments = models.TextField(blank=True, null=True)
    actioned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'combined_request'
        ordering = ['step_order']
        verbose_name = 'Approval Step'
        verbose_name_plural = 'Approval Steps'

    def __str__(self):
        return f"Step {self.step_order}: {self.step_name} - {self.status}"
