from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    TravelInsightViewSet,
    TravelAnalyticsViewSet,
    dashboard_summary,
    travel_spend_analytics,
    travel_pattern_analytics,
    booking_analytics,
    department_analytics,
    user_activity_report
)

router = DefaultRouter()
router.register(r'insights', TravelInsightViewSet, basename='travel-insight')
router.register(r'analytics', TravelAnalyticsViewSet, basename='travel-analytics')

urlpatterns = [
    path('', include(router.urls)),

    # Analytics endpoints
    path('dashboard/summary/', dashboard_summary, name='dashboard-summary'),
    path('analytics/travel-spend/', travel_spend_analytics, name='travel-spend-analytics'),
    path('analytics/travel-patterns/', travel_pattern_analytics, name='travel-pattern-analytics'),
    path('analytics/bookings/', booking_analytics, name='booking-analytics'),
    path('analytics/departments/', department_analytics, name='department-analytics'),
    path('reports/user-activity/', user_activity_report, name='user-activity-report'),
]
