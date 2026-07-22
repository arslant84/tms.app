from django.urls import path

from .views import (
    booking_analytics,
    dashboard_summary,
    department_analytics,
    travel_pattern_analytics,
    travel_spend_analytics,
    user_activity_report,
)

urlpatterns = [
    # Analytics endpoints
    path("dashboard/summary/", dashboard_summary, name="dashboard-summary"),
    path(
        "analytics/travel-spend/", travel_spend_analytics, name="travel-spend-analytics"
    ),
    path(
        "analytics/travel-patterns/",
        travel_pattern_analytics,
        name="travel-pattern-analytics",
    ),
    path("analytics/bookings/", booking_analytics, name="booking-analytics"),
    path("analytics/departments/", department_analytics, name="department-analytics"),
    path("reports/user-activity/", user_activity_report, name="user-activity-report"),
]
