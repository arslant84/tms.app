from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    TravelInsight, DestinationStat, CategorySpend,
    MonthlyTrend, TravelAnalytics, InsightType
)

User = get_user_model()


class DestinationStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = DestinationStat
        fields = ['id', 'destination', 'count', 'average_cost']
        read_only_fields = ['id']


class CategorySpendSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategorySpend
        fields = ['id', 'category', 'amount', 'percentage']
        read_only_fields = ['id']


class MonthlyTrendSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyTrend
        fields = ['id', 'month', 'year', 'trip_count', 'total_spend']
        read_only_fields = ['id']


class TravelInsightSerializer(serializers.ModelSerializer):
    user_id = serializers.ReadOnlyField()
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = TravelInsight
        fields = [
            'id', 'user', 'user_id', 'user_name', 'title', 'description', 'insight_type',
            'potential_savings', 'relevance_score', 'expiry_date', 'is_expired', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_is_expired(self, obj):
        """Check if insight has expired"""
        if obj.expiry_date:
            from django.utils import timezone
            return obj.expiry_date < timezone.now().date()
        return False


class TravelAnalyticsSerializer(serializers.ModelSerializer):
    top_destinations = DestinationStatSerializer(many=True, read_only=True)
    spend_by_category = CategorySpendSerializer(many=True, read_only=True)
    monthly_trend = MonthlyTrendSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True, allow_null=True)

    class Meta:
        model = TravelAnalytics
        fields = [
            'id', 'user', 'user_name', 'total_trips', 'total_spend', 'average_trip_cost',
            'savings_opportunities', 'top_destinations', 'spend_by_category',
            'monthly_trend', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# Analytics Response Serializers (for computed data)

class DashboardSummarySerializer(serializers.Serializer):
    """Serializer for dashboard summary statistics"""
    total_trfs = serializers.IntegerField()
    pending_trfs = serializers.IntegerField()
    approved_trfs = serializers.IntegerField()
    rejected_trfs = serializers.IntegerField()
    total_travel_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_expense_claims = serializers.IntegerField()
    active_bookings = serializers.IntegerField()
    pending_approvals = serializers.IntegerField()
    pending_transport_requests = serializers.IntegerField()
    pending_visa_applications = serializers.IntegerField()
    recent_activities = serializers.ListField()


class TravelSpendAnalyticsSerializer(serializers.Serializer):
    """Serializer for travel spend analytics"""
    total_spend = serializers.DecimalField(max_digits=12, decimal_places=2)
    by_category = serializers.DictField()
    by_department = serializers.DictField()
    by_month = serializers.ListField()
    top_spenders = serializers.ListField()
    budget_utilization = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)


class TravelPatternAnalyticsSerializer(serializers.Serializer):
    """Serializer for travel pattern analytics"""
    total_trips = serializers.IntegerField()
    domestic_trips = serializers.IntegerField()
    international_trips = serializers.IntegerField()
    top_destinations = serializers.ListField()
    average_trip_duration = serializers.FloatField()
    most_frequent_travelers = serializers.ListField()
    travel_by_purpose = serializers.DictField()


class BookingAnalyticsSerializer(serializers.Serializer):
    """Serializer for booking analytics"""
    total_flight_bookings = serializers.IntegerField()
    total_hotel_bookings = serializers.IntegerField()
    flight_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    hotel_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_booking_lead_time = serializers.FloatField()
    preferred_airlines = serializers.ListField()
    preferred_hotels = serializers.ListField()
    booking_class_distribution = serializers.DictField()


class ExpenseAnalyticsSerializer(serializers.Serializer):
    """Serializer for expense analytics"""
    total_claims = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    approved_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    by_category = serializers.DictField()
    by_status = serializers.DictField()
    average_claim_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    top_expense_categories = serializers.ListField()


class DepartmentAnalyticsSerializer(serializers.Serializer):
    """Serializer for department-wise analytics"""
    department_name = serializers.CharField()
    total_trips = serializers.IntegerField()
    total_spend = serializers.DecimalField(max_digits=12, decimal_places=2)
    active_travelers = serializers.IntegerField()
    average_trip_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_approvals = serializers.IntegerField()


class UserActivitySerializer(serializers.Serializer):
    """Serializer for user activity tracking"""
    user_id = serializers.IntegerField()
    user_name = serializers.CharField()
    email = serializers.EmailField()
    total_trfs = serializers.IntegerField()
    total_bookings = serializers.IntegerField()
    total_claims = serializers.IntegerField()
    total_spend = serializers.DecimalField(max_digits=12, decimal_places=2)
    last_activity = serializers.DateTimeField()


class ComplianceReportSerializer(serializers.Serializer):
    """Serializer for policy compliance report"""
    total_requests = serializers.IntegerField()
    compliant_requests = serializers.IntegerField()
    non_compliant_requests = serializers.IntegerField()
    compliance_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    violations_by_type = serializers.DictField()
    top_violators = serializers.ListField(required=False)


class TimeSeriesDataSerializer(serializers.Serializer):
    """Serializer for time series data"""
    date = serializers.DateField()
    value = serializers.DecimalField(max_digits=12, decimal_places=2)
    count = serializers.IntegerField()


class ExportOptionsSerializer(serializers.Serializer):
    """Serializer for export options"""
    format = serializers.ChoiceField(choices=['pdf', 'excel', 'csv'])
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    include_charts = serializers.BooleanField(default=False)
    filters = serializers.DictField(required=False)
