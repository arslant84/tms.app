from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class TravelType(models.TextChoices):
    DOMESTIC = 'DOMESTIC', _('Domestic')
    INTERNATIONAL = 'INTERNATIONAL', _('International')


class TRFStatus(models.TextChoices):
    DRAFT = 'DRAFT', _('Draft')
    SUBMITTED = 'SUBMITTED', _('Submitted')
    PENDING_APPROVAL = 'PENDING_APPROVAL', _('Pending Approval')
    APPROVED = 'APPROVED', _('Approved')
    REJECTED = 'REJECTED', _('Rejected')
    CANCELLED = 'CANCELLED', _('Cancelled')


class ApprovalStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    APPROVED = 'APPROVED', _('Approved')
    REJECTED = 'REJECTED', _('Rejected')


class TravelRequestForm(models.Model):
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='travel_requests')
    purpose = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    departure_date = models.DateField()
    return_date = models.DateField()
    travel_type = models.CharField(
        max_length=20,
        choices=TravelType.choices,
        default=TravelType.DOMESTIC,
    )
    accommodation_required = models.BooleanField(default=False)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=TRFStatus.choices,
        default=TRFStatus.DRAFT,
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.requester.name}'s travel to {self.destination}"
    
    @property
    def requester_name(self):
        return self.requester.name
    
    @property
    def requester_id(self):
        return self.requester.id


class ApprovalStep(models.Model):
    trf = models.ForeignKey(TravelRequestForm, on_delete=models.CASCADE, related_name='approval_chain')
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trf_approvals')
    status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    comments = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.approver.name}'s approval for {self.trf}"
    
    @property
    def approver_name(self):
        return self.approver.name
    
    @property
    def approver_id(self):
        return self.approver.id
