from django.conf import settings
from django.db import models
from django.utils import timezone
from utils.encryption import EncryptedTextField


class TravelRequest(models.Model):
    """
    Travel Request model with dynamic workflow status support

    Note: STATUS_CHOICES removed to support dynamic workflow statuses
    Status will be set by workflow engine based on configured approval roles
    Examples: "Draft", "Pending HOD", "Pending Line Manager", "Approved", etc.
    """

    request_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text="Auto-generated request number (e.g., TSR-20250702-1423-NYC-PCYX)",
    )
    requestor_name = models.CharField(max_length=255)
    staff_id = models.CharField(max_length=255, blank=True, null=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    position = models.CharField(max_length=255, blank=True, null=True)
    cost_center = models.CharField(max_length=255, blank=True, null=True)
    tel_email = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    travel_type = models.CharField(max_length=255)
    status = models.CharField(
        max_length=100,
        default="Draft",
        help_text="Dynamic status set by workflow engine",
    )
    purpose = models.TextField(blank=True, null=True)
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    additional_comments = models.TextField(blank=True, null=True)
    external_full_name = models.CharField(max_length=255, blank=True, null=True)
    external_organization = models.CharField(max_length=255, blank=True, null=True)
    external_ref_to_authority_letter = models.CharField(
        max_length=255, blank=True, null=True
    )
    external_cost_center = models.CharField(max_length=255, blank=True, null=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    additional_data = models.JSONField(blank=True, null=True)
    MEAL_PROCESSING_STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Arranged", "Arranged"),
        ("Completed", "Completed"),
    ]
    meal_processing_status = models.CharField(
        max_length=20, choices=MEAL_PROCESSING_STATUS_CHOICES, default="Pending"
    )
    advance_consent_accepted = models.BooleanField(
        default=False,
        help_text="Requestor acknowledged the advance amount refund/deduction Terms and Conditions (Overseas/Home Leave only).",
    )
    advance_consent_accepted_at = models.DateTimeField(blank=True, null=True)
    department_focal_notified = models.BooleanField(
        default=False,
        help_text=(
            "Whether the Department Focal has already been notified that this "
            "request's travel arrangements are fully complete — prevents "
            "re-notifying on every subsequent save once notified."
        ),
    )

    # ForeignKey to User who created the request
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="travel_requests_created",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.requestor_name

    def save(self, *args, **kwargs):
        # Stamp the acceptance time server-side the first time consent is given,
        # rather than trusting a client-supplied timestamp.
        if self.advance_consent_accepted and not self.advance_consent_accepted_at:
            self.advance_consent_accepted_at = timezone.now()
        super().save(*args, **kwargs)

    # Maps each canonical travel_type to its own workflow entity_type, so an
    # admin can configure a distinct approval workflow per travel type via
    # the Workflow Configuration screen. See docs/TSR_SUBMODULE_WORKFLOW_ROADMAP.md.
    WORKFLOW_ENTITY_TYPE_MAP = {
        "Domestic": "travelrequest_domestic",
        "Overseas": "travelrequest_overseas",
        "Home Leave": "travelrequest_homeleave",
        "External Parties": "travelrequest_external",
    }

    @property
    def workflow_entity_type(self) -> str:
        """
        The specific entity_type to look up a WorkflowTemplate for. Callers
        should also pass entity_type="travelrequest" as a fallback so a
        travel type with no dedicated template yet still routes through the
        existing shared one.
        """
        return self.WORKFLOW_ENTITY_TYPE_MAP.get(self.travel_type, "travelrequest")

    @property
    def is_fully_arranged(self) -> bool:
        """
        True once every downstream arrangement this specific request actually
        needed (flight/meal/transport/accommodation) is complete. See
        trf.services.check_is_fully_arranged for the per-module rules.
        """
        from trf.services import check_is_fully_arranged

        return check_is_fully_arranged(self)


class TrfAdvanceAmountRequestedItem(models.Model):
    trf = models.ForeignKey(TravelRequest, on_delete=models.CASCADE)
    date_from = models.DateField(blank=True, null=True)
    date_to = models.DateField(blank=True, null=True)
    lh = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ma = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    oa = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    oe = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class TrfAdvanceBankDetail(models.Model):
    trf = models.OneToOneField(TravelRequest, on_delete=models.CASCADE)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    account_number = EncryptedTextField(
        blank=True, null=True
    )  # CTRL-0000001066: encrypted at rest
    account_name = EncryptedTextField(
        blank=True, null=True
    )  # CTRL-0000001066: encrypted at rest
    branch_address = models.TextField(blank=True, null=True)
    currency = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class TrfApprovalStep(models.Model):
    trf = models.ForeignKey(TravelRequest, on_delete=models.CASCADE)
    step_role = models.CharField(max_length=255)
    step_name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255)
    step_date = models.DateTimeField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class TrfDailyMealSelection(models.Model):
    trf = models.ForeignKey(TravelRequest, on_delete=models.CASCADE)
    meal_date = models.DateField()
    breakfast = models.BooleanField(default=False)
    lunch = models.BooleanField(default=False)
    dinner = models.BooleanField(default=False)
    supper = models.BooleanField(default=False)
    refreshment = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("trf", "meal_date")


class TrfItinerarySegment(models.Model):
    trf = models.ForeignKey(TravelRequest, on_delete=models.CASCADE)
    segment_date = models.DateField(blank=True, null=True)
    day_of_week = models.CharField(max_length=255, blank=True, null=True)
    from_location = models.CharField(max_length=255, blank=True, null=True)
    to_location = models.CharField(max_length=255, blank=True, null=True)
    departure_time = models.CharField(max_length=255, blank=True, null=True)
    arrival_time = models.CharField(max_length=255, blank=True, null=True)
    purpose = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    flight_number = models.CharField(max_length=255, blank=True, null=True)
    flight_class = models.CharField(max_length=255, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)


class TrfMealProvision(models.Model):
    trf = models.ForeignKey(TravelRequest, on_delete=models.CASCADE)
    date_from_to = models.CharField(max_length=255, blank=True, null=True)
    breakfast = models.IntegerField(default=0)
    lunch = models.IntegerField(default=0)
    dinner = models.IntegerField(default=0)
    supper = models.IntegerField(default=0)
    refreshment = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TrfPassportDetail(models.Model):
    trf = models.ForeignKey(TravelRequest, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    passport_number = EncryptedTextField(
        blank=True, null=True
    )  # CTRL-0000001066: encrypted at rest
    nationality = models.CharField(max_length=255, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    place_of_birth = models.CharField(max_length=255, blank=True, null=True)
    passport_issue_date = models.DateField(blank=True, null=True)
    passport_expiry_date = models.DateField(blank=True, null=True)
    passport_file = models.FileField(
        upload_to="trf/passports/",
        blank=True,
        null=True,
        help_text="Uploaded passport scan/photo",
    )
    created_at = models.DateTimeField(auto_now_add=True)
