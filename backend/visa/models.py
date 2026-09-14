from accounts.models import User
from django.db import models


class VisaApplication(models.Model):
    request_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text="Auto-generated request number (e.g., VIS-20251102-1423-TKM-PCYX)",
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    requestor_name = models.CharField(max_length=255)
    staff_id = models.CharField(max_length=255, blank=True, null=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    position = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    destination = models.CharField(max_length=255)
    travel_purpose = models.TextField()
    visa_type = models.CharField(max_length=255)
    trip_start_date = models.DateField(blank=True, null=True)
    trip_end_date = models.DateField(blank=True, null=True)
    passport_number = models.CharField(max_length=255, blank=True, null=True)
    passport_expiry_date = models.DateField(blank=True, null=True)
    passport_file = models.FileField(
        upload_to="visa/passports/",
        blank=True,
        null=True,
        help_text="Uploaded passport scan/photo for visa application",
    )

    # Note: STATUS_CHOICES removed to support dynamic workflow statuses
    # Status will be set by workflow engine based on configured approval roles
    # Examples: "Draft", "Pending HOD", "Pending Line Manager", "Approved", etc.
    status = models.CharField(
        max_length=100,
        default="Draft",
        help_text="Dynamic status set by workflow engine",
    )
    additional_comments = models.TextField(blank=True, null=True)
    submitted_date = models.DateTimeField(blank=True, null=True)
    last_updated_date = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    trf_reference_number = models.CharField(max_length=255, blank=True, null=True)
    processing_details = models.JSONField(blank=True, null=True)
    processing_started_at = models.DateTimeField(blank=True, null=True)
    processing_completed_at = models.DateTimeField(blank=True, null=True)
    # Who marked processing complete - `complete()` in
    # visa_application_views.py already passed request.user through to
    # finalize_visa_workflow_completion() for the completion notification,
    # but never persisted it anywhere durable. processing_details also has
    # a "completed_by_admin" key, but that's just a boolean (human vs
    # system-completed), not an identity.
    processing_completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visa_applications_completed",
    )
    date_of_birth = models.DateField(blank=True, null=True)
    place_of_birth = models.CharField(max_length=255, blank=True, null=True)
    citizenship = models.CharField(max_length=255, blank=True, null=True)
    passport_place_of_issuance = models.CharField(max_length=255, blank=True, null=True)
    passport_date_of_issuance = models.DateField(blank=True, null=True)
    contact_telephone = models.CharField(max_length=255, blank=True, null=True)
    home_address = models.TextField(blank=True, null=True)
    education_details = models.TextField(blank=True, null=True)
    current_employer_name = models.CharField(max_length=255, blank=True, null=True)
    current_employer_address = models.TextField(blank=True, null=True)
    marital_status = models.CharField(max_length=255, blank=True, null=True)
    family_information = models.TextField(blank=True, null=True)
    request_type = models.CharField(max_length=255, default="VISA")
    approximately_arrival_date = models.DateField(blank=True, null=True)
    duration_of_stay = models.CharField(max_length=255, blank=True, null=True)
    visa_entry_type = models.CharField(max_length=255, blank=True, null=True)
    work_visit_category = models.CharField(max_length=255, blank=True, null=True)
    application_fees_borne_by = models.CharField(max_length=255, blank=True, null=True)
    cost_centre_number = models.CharField(max_length=255, blank=True, null=True)
    # line_focal_*/sponsoring_dept_head_*/ceo_approval_* removed 2026-09-11
    # (ERD fix roadmap, Issue 4): never read or written by any serializer,
    # view, or frontend code - a fixed-shape approval chain that was
    # superseded by VisaApprovalStep (and now the generic workflow engine)
    # before ever being wired up to anything. Confirmed dead via grep across
    # the whole backend and frontend; the one row with any value in these
    # columns held junk test data ("uykyu" etc.), not real approvals.
    itinerary_details = models.TextField(blank=True, null=True)
    supporting_documents_notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.requestor_name


class VisaApprovalStep(models.Model):
    visa = models.ForeignKey(VisaApplication, on_delete=models.CASCADE)
    step_role = models.CharField(max_length=255)
    step_name = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    step_date = models.DateTimeField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.visa} - {self.step_name}"


class VisaDocument(models.Model):
    visa = models.ForeignKey(VisaApplication, on_delete=models.CASCADE)
    document_name = models.CharField(max_length=255)
    document_path = models.CharField(max_length=255)
    document_type = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.document_name
