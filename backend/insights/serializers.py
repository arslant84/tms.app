from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


# Analytics Response Serializers (for computed data)


class DashboardSummarySerializer(serializers.Serializer):
    """Serializer for dashboard summary statistics"""

    total_trfs = serializers.IntegerField()
    pending_trfs = serializers.IntegerField()
    approved_trfs = serializers.IntegerField()
    rejected_trfs = serializers.IntegerField()
    total_travel_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
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
    budget_utilization = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )


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
    average_booking_lead_time = serializers.FloatField()
    preferred_airlines = serializers.ListField()
    booking_class_distribution = serializers.DictField()


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

    format = serializers.ChoiceField(choices=["pdf", "excel", "csv"])
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    include_charts = serializers.BooleanField(default=False)
    filters = serializers.DictField(required=False)
