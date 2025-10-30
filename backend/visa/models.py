from django.db import models
from accounts.models import User

class VisaApplication(models.Model):
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

    # Note: STATUS_CHOICES removed to support dynamic workflow statuses
    # Status will be set by workflow engine based on configured approval roles
    # Examples: "Draft", "Pending HOD", "Pending Line Manager", "Approved", etc.
    status = models.CharField(max_length=100, default='Draft', help_text="Dynamic status set by workflow engine")
    additional_comments = models.TextField(blank=True, null=True)
    submitted_date = models.DateTimeField(blank=True, null=True)
    last_updated_date = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    trf_reference_number = models.CharField(max_length=255, blank=True, null=True)
    processing_details = models.JSONField(blank=True, null=True)
    processing_started_at = models.DateTimeField(blank=True, null=True)
    processing_completed_at = models.DateTimeField(blank=True, null=True)
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
    request_type = models.CharField(max_length=255, default='VISA')
    approximately_arrival_date = models.DateField(blank=True, null=True)
    duration_of_stay = models.CharField(max_length=255, blank=True, null=True)
    visa_entry_type = models.CharField(max_length=255, blank=True, null=True)
    work_visit_category = models.CharField(max_length=255, blank=True, null=True)
    application_fees_borne_by = models.CharField(max_length=255, blank=True, null=True)
    cost_centre_number = models.CharField(max_length=255, blank=True, null=True)
    line_focal_person = models.CharField(max_length=255, blank=True, null=True)
    line_focal_dept = models.CharField(max_length=255, blank=True, null=True)
    line_focal_contact = models.CharField(max_length=255, blank=True, null=True)
    line_focal_date = models.DateField(blank=True, null=True)
    sponsoring_dept_head = models.CharField(max_length=255, blank=True, null=True)
    sponsoring_dept_head_dept = models.CharField(max_length=255, blank=True, null=True)
    sponsoring_dept_head_contact = models.CharField(max_length=255, blank=True, null=True)
    sponsoring_dept_head_date = models.DateField(blank=True, null=True)
    ceo_approval_name = models.CharField(max_length=255, blank=True, null=True)
    ceo_approval_date = models.DateField(blank=True, null=True)
    itinerary_details = models.TextField(blank=True, null=True)
    supporting_documents_notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

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
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.visa} - {self.step_name}'


class VisaDocument(models.Model):
    visa = models.ForeignKey(VisaApplication, on_delete=models.CASCADE)
    document_name = models.CharField(max_length=255)
    document_path = models.CharField(max_length=255)
    document_type = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.document_name
