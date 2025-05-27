from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from trf.models import TravelRequestForm, ApprovalStatus


class ExpenseCategory(models.TextChoices):
    ACCOMMODATION = 'ACCOMMODATION', _('Accommodation')
    MEALS = 'MEALS', _('Meals')
    TRANSPORTATION = 'TRANSPORTATION', _('Transportation')
    ENTERTAINMENT = 'ENTERTAINMENT', _('Entertainment')
    MISCELLANEOUS = 'MISCELLANEOUS', _('Miscellaneous')


class ExpenseStatus(models.TextChoices):
    DRAFT = 'DRAFT', _('Draft')
    SUBMITTED = 'SUBMITTED', _('Submitted')
    UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review')
    APPROVED = 'APPROVED', _('Approved')
    REJECTED = 'REJECTED', _('Rejected')
    PAID = 'PAID', _('Paid')


class ExpenseItem(models.Model):
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(
        max_length=20,
        choices=ExpenseCategory.choices,
        default=ExpenseCategory.MISCELLANEOUS,
    )
    date = models.DateField()
    receipt_url = models.URLField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.description} - {self.amount}"


class ExpenseClaim(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='expense_claims')
    trf = models.ForeignKey(TravelRequestForm, on_delete=models.SET_NULL, related_name='expense_claims', null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    expense_date = models.DateField()
    category = models.CharField(
        max_length=20,
        choices=ExpenseCategory.choices,
        default=ExpenseCategory.MISCELLANEOUS,
    )
    status = models.CharField(
        max_length=20,
        choices=ExpenseStatus.choices,
        default=ExpenseStatus.DRAFT,
    )
    receipt_urls = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    items = models.ManyToManyField(ExpenseItem, related_name='expense_claim')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.name}"
    
    @property
    def user_id(self):
        return self.user.id
    
    @property
    def trf_id(self):
        return self.trf.id if self.trf else None


class ExpenseApproval(models.Model):
    expense = models.ForeignKey(ExpenseClaim, on_delete=models.CASCADE, related_name='approval_chain')
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='expense_approvals')
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
        return f"{self.approver.name}'s approval for {self.expense}"
    
    @property
    def approver_name(self):
        return self.approver.name
    
    @property
    def approver_id(self):
        return self.approver.id
