from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class InsightType(models.TextChoices):
    COST_SAVING = 'COST_SAVING', _('Cost Saving')
    BOOKING_TIMING = 'BOOKING_TIMING', _('Booking Timing')
    PREFERRED_VENDOR = 'PREFERRED_VENDOR', _('Preferred Vendor')
    TRAVEL_PATTERN = 'TRAVEL_PATTERN', _('Travel Pattern')
    POLICY_COMPLIANCE = 'POLICY_COMPLIANCE', _('Policy Compliance')


class TravelInsight(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='travel_insights')
    title = models.CharField(max_length=255)
    description = models.TextField()
    insight_type = models.CharField(
        max_length=20,
        choices=InsightType.choices,
        default=InsightType.COST_SAVING,
    )
    potential_savings = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    relevance_score = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} for {self.user.name}"
    
    @property
    def user_id(self):
        return self.user.id


class DestinationStat(models.Model):
    destination = models.CharField(max_length=100)
    count = models.PositiveIntegerField(default=0)
    average_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    
    def __str__(self):
        return f"{self.destination} - {self.count} trips"


class CategorySpend(models.Model):
    category = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    
    def __str__(self):
        return f"{self.category} - {self.amount}"


class MonthlyTrend(models.Model):
    month = models.CharField(max_length=10)
    year = models.PositiveIntegerField()
    trip_count = models.PositiveIntegerField(default=0)
    total_spend = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    
    class Meta:
        ordering = ['year', 'month']
    
    def __str__(self):
        return f"{self.month} {self.year} - {self.trip_count} trips"


class TravelAnalytics(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='travel_analytics', null=True, blank=True)
    total_trips = models.PositiveIntegerField(default=0)
    total_spend = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    average_trip_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    savings_opportunities = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    top_destinations = models.ManyToManyField(DestinationStat, related_name='analytics')
    spend_by_category = models.ManyToManyField(CategorySpend, related_name='analytics')
    monthly_trend = models.ManyToManyField(MonthlyTrend, related_name='analytics')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Travel Analytics'
    
    def __str__(self):
        if self.user:
            return f"Analytics for {self.user.name}"
        return "Company-wide Analytics"
