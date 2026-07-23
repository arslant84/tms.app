import logging
from datetime import datetime, timedelta
from decimal import Decimal

from accounts.utils import can_view_all, has_permission
from django.db.models import Avg, Count, F, Max, Q, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from utils.api_response import forbidden_response, success_response

logger = logging.getLogger(__name__)

from accounts.models import User
from bookings.models import FlightBooking
from transport.models import TransportRequest

# Import models from other apps for analytics
from trf.models import TravelRequest
from visa.models import VisaApplication

from .serializers import (
    BookingAnalyticsSerializer,
    ComplianceReportSerializer,
    DashboardSummarySerializer,
    DepartmentAnalyticsSerializer,
    TravelPatternAnalyticsSerializer,
    TravelSpendAnalyticsSerializer,
    UserActivitySerializer,
)


def _require_admin_reports_permission(request):
    """Shared gate for insights' company-wide (non-self-scoped) endpoints
    below, matching reports/views.py's identically-named helper: same
    permission, same class of data (company/department-wide aggregates,
    not a per-user dashboard), so the two apps' admin analytics stay
    consistent rather than diverging on IsAdminUser vs. the real RBAC
    permission system.
    Returns a 403 response if the user lacks generate_admin_reports, else None."""
    if request.user.is_superuser or has_permission(
        request.user, "generate_admin_reports"
    ):
        return None
    return forbidden_response(
        message="You do not have permission to view admin analytics"
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    """
    Get dashboard summary statistics
    """
    user = request.user

    # Filter data based on user permissions (per-module)
    # TRF data - check view_all_trf permission
    if user.is_superuser or can_view_all(user, "trf"):
        trfs = TravelRequest.objects.all()
    else:
        trfs = TravelRequest.objects.filter(created_by=user)

    # Flight bookings - tied to TRF admin permission
    if user.is_superuser or can_view_all(user, "trf"):
        flights = FlightBooking.objects.all()
    else:
        flights = FlightBooking.objects.filter(user=user)

    # Transport requests - check view_all_transport permission
    if user.is_superuser or can_view_all(user, "transport"):
        transports = TransportRequest.objects.all()
    else:
        transports = TransportRequest.objects.filter(requestor=user)

    # Visa applications - check view_all_visa permission
    if user.is_superuser or can_view_all(user, "visa"):
        visas = VisaApplication.objects.all()
    else:
        visas = VisaApplication.objects.filter(user=user)

    # Calculate statistics
    total_trfs = trfs.count()
    # Use case-insensitive contains for dynamic workflow statuses
    pending_trfs = trfs.filter(status__icontains="Pending").count()
    approved_trfs = trfs.filter(status="Approved").count()
    rejected_trfs = trfs.filter(status="Rejected").count()

    # Calculate total travel cost from TRFs
    total_travel_cost = trfs.aggregate(total=Sum("estimated_cost"))["total"] or Decimal(
        "0.00"
    )

    # Active bookings
    active_bookings = flights.filter(status__in=["CONFIRMED", "TICKETED"]).count()

    # Pending transport requests
    pending_transport_requests = transports.filter(status__icontains="Pending").count()

    # Pending visa applications
    pending_visa_applications = visas.filter(status__icontains="Pending").count()

    # Pending approvals (use case-insensitive contains for dynamic statuses)
    pending_approvals = trfs.filter(status__icontains="Pending").count()

    # Recent activities - comprehensive implementation (TSR, Visa, Accommodation, Transport)
    recent_activities = []

    # Helper function to format dates
    def format_date_info(item):
        """Format date info based on status"""
        status_lower = item.get("status", "").lower() if item.get("status") else ""
        if "draft" in status_lower:
            return f"Created: {item.get('created_at').strftime('%b %d, %Y')}"
        elif "pending" in status_lower or "submitted" in status_lower:
            updated = item.get("updated_at", item.get("created_at"))
            return f"Submitted: {updated.strftime('%b %d, %Y')}"
        else:
            updated = item.get("updated_at", item.get("created_at"))
            return f"Updated: {updated.strftime('%b %d, %Y')}"

    # Collect TSR activities (non-accommodation travel requests)
    recent_trfs = trfs.exclude(
        Q(travel_type__iexact="Accommodation")
        | Q(travel_type__icontains="Accommodation")
    ).order_by("-updated_at")[:10]

    for trf in recent_trfs:
        try:
            recent_activities.append(
                {
                    "type": "TSR",
                    "id": trf.id,
                    "title": f"TSR: {trf.purpose[:50] if trf.purpose else 'Travel Request'}",
                    "status": trf.status or "Draft",
                    "date": format_date_info(
                        {
                            "status": trf.status,
                            "created_at": trf.created_at,
                            "updated_at": trf.updated_at,
                        }
                    ),
                    "updated_at": trf.updated_at,
                }
            )
        except Exception as e:
            logger.error(f"Error processing TSR {trf.id}: {e}")

    # Collect Visa activities
    recent_visas = visas.order_by("-updated_at")[:10]
    for visa in recent_visas:
        try:
            recent_activities.append(
                {
                    "type": "Visa",
                    "id": visa.id,
                    "title": f"Visa: {visa.travel_purpose[:50] if visa.travel_purpose else 'Visa Application'}",
                    "status": visa.status or "Draft",
                    "date": format_date_info(
                        {
                            "status": visa.status,
                            "created_at": visa.created_at,
                            "updated_at": visa.updated_at,
                        }
                    ),
                    "updated_at": visa.updated_at,
                }
            )
        except Exception as e:
            logger.error(f"Error processing Visa {visa.id}: {e}")

    # Collect Accommodation activities
    from accommodation.models import AccommodationBooking

    try:
        if user.is_superuser or can_view_all(user, "accommodation"):
            accommodation_bookings = AccommodationBooking.objects.all()
        else:
            accommodation_bookings = AccommodationBooking.objects.filter(staff=user)

        recent_accommodations = accommodation_bookings.order_by("-updated_at")[:10]
        for accommodation in recent_accommodations:
            try:
                recent_activities.append(
                    {
                        "type": "Accommodation",
                        "id": accommodation.id,
                        "title": f"Accommodation: {accommodation.city if hasattr(accommodation, 'city') else 'Booking Request'}",
                        "status": accommodation.status or "Draft",
                        "date": format_date_info(
                            {
                                "status": accommodation.status,
                                "created_at": accommodation.created_at,
                                "updated_at": accommodation.updated_at,
                            }
                        ),
                        "updated_at": accommodation.updated_at,
                    }
                )
            except Exception as e:
                logger.error(f"Error processing Accommodation {accommodation.id}: {e}")
    except Exception as e:
        logger.error(f"Error fetching accommodation bookings: {e}")

    # Collect Transport activities
    recent_transports = transports.order_by("-updated_at")[:10]
    for transport in recent_transports:
        try:
            transport_date = (
                getattr(transport, "updated_at", None)
                or getattr(transport, "created_at", None)
                or timezone.now()
            )
            recent_activities.append(
                {
                    "type": "Transport",
                    "id": transport.id,
                    "title": f"Transport: {transport.from_location if hasattr(transport, 'from_location') else 'Transport Request'}",
                    "status": transport.status or "Draft",
                    "date": format_date_info(
                        {
                            "status": transport.status,
                            "created_at": getattr(
                                transport, "created_at", timezone.now()
                            ),
                            "updated_at": transport_date,
                        }
                    ),
                    "updated_at": transport_date,
                }
            )
        except Exception as e:
            logger.error(f"Error processing Transport {transport.id}: {e}")

    # Sort all activities by updated_at (most recent first)
    recent_activities.sort(key=lambda x: x["updated_at"], reverse=True)

    # Take top 15 activities
    recent_activities = recent_activities[:15]

    # Remove updated_at from response (used only for sorting)
    for activity in recent_activities:
        activity.pop("updated_at", None)

    data = {
        "total_trfs": total_trfs,
        "pending_trfs": pending_trfs,
        "approved_trfs": approved_trfs,
        "rejected_trfs": rejected_trfs,
        "total_travel_cost": total_travel_cost,
        "active_bookings": active_bookings,
        "pending_approvals": pending_approvals,
        "pending_transport_requests": pending_transport_requests,
        "pending_visa_applications": pending_visa_applications,
        "recent_activities": recent_activities,
    }

    serializer = DashboardSummarySerializer(data)
    return success_response(
        data=serializer.data, message="Dashboard summary retrieved successfully"
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def travel_spend_analytics(request):
    """
    Get travel spend analytics
    """
    user = request.user

    # Get date range from query params
    date_from = request.query_params.get("date_from", None)
    date_to = request.query_params.get("date_to", None)

    # Base queryset - check view_all_trf permission
    if user.is_superuser or can_view_all(user, "trf"):
        trfs = TravelRequest.objects.all()
    else:
        trfs = TravelRequest.objects.filter(user=user)

    # Apply date filters
    if date_from:
        trfs = trfs.filter(created_at__gte=date_from)
    if date_to:
        trfs = trfs.filter(created_at__lte=date_to)

    # Total spend
    total_spend = trfs.aggregate(total=Sum("estimated_cost"))["total"] or Decimal(
        "0.00"
    )

    # By category (from travel type)
    by_category = dict(
        trfs.values("travel_type")
        .annotate(total=Sum("estimated_cost"))
        .values_list("travel_type", "total")
    )

    # By department (from user's department) - requires view_all_trf permission
    by_department = {}
    if user.is_superuser or can_view_all(user, "trf"):
        dept_data = trfs.values("user__department__name").annotate(
            total=Sum("estimated_cost")
        )
        for item in dept_data:
            dept_name = item["user__department__name"] or "Unknown"
            by_department[dept_name] = float(item["total"] or 0)

    # By month (last 12 months)
    by_month = []
    for i in range(12):
        month_start = timezone.now().date() - timedelta(days=30 * i)
        month_trfs = trfs.filter(
            created_at__year=month_start.year, created_at__month=month_start.month
        )
        month_total = month_trfs.aggregate(total=Sum("estimated_cost"))[
            "total"
        ] or Decimal("0.00")

        by_month.append(
            {"month": month_start.strftime("%b %Y"), "amount": float(month_total)}
        )

    by_month.reverse()

    # Top spenders (requires view_all_trf permission)
    top_spenders = []
    if user.is_superuser or can_view_all(user, "trf"):
        top_users = (
            trfs.values("user__id", "user__first_name", "user__last_name")
            .annotate(total=Sum("estimated_cost"))
            .order_by("-total")[:10]
        )

        for item in top_users:
            top_spenders.append(
                {
                    "user_id": item["user__id"],
                    "user_name": f"{item['user__first_name']} {item['user__last_name']}",
                    "total_spend": float(item["total"] or 0),
                }
            )

    data = {
        "total_spend": total_spend,
        "by_category": by_category,
        "by_department": by_department,
        "by_month": by_month,
        "top_spenders": top_spenders,
        "budget_utilization": Decimal("0.00"),  # Can be calculated if budget is defined
    }

    serializer = TravelSpendAnalyticsSerializer(data)
    return success_response(
        data=serializer.data, message="Travel spend analytics retrieved successfully"
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def travel_pattern_analytics(request):
    """
    Get travel pattern analytics
    """
    user = request.user

    # Base queryset - check view_all_trf permission
    if user.is_superuser or can_view_all(user, "trf"):
        trfs = TravelRequest.objects.all()
    else:
        trfs = TravelRequest.objects.filter(user=user)

    # Total trips
    total_trips = trfs.count()
    domestic_trips = trfs.filter(travel_type="DOMESTIC").count()
    international_trips = trfs.filter(travel_type="OVERSEAS").count()

    # Top destinations (would need to parse from TRF data)
    top_destinations = []

    # Average trip duration (would need start/end dates from TRF)
    average_trip_duration = 5.0  # Default

    # Most frequent travelers (requires view_all_trf permission)
    most_frequent_travelers = []
    if user.is_superuser or can_view_all(user, "trf"):
        freq_travelers = User.objects.annotate(
            trip_count=Count("travel_requests")
        ).order_by("-trip_count")[:10]

        for traveler in freq_travelers:
            if traveler.trip_count > 0:
                most_frequent_travelers.append(
                    {
                        "user_id": traveler.id,
                        "user_name": traveler.get_full_name(),
                        "trip_count": traveler.trip_count,
                    }
                )

    # Travel by purpose
    travel_by_purpose = dict(
        trfs.values("purpose")
        .annotate(count=Count("id"))
        .values_list("purpose", "count")
    )

    data = {
        "total_trips": total_trips,
        "domestic_trips": domestic_trips,
        "international_trips": international_trips,
        "top_destinations": top_destinations,
        "average_trip_duration": average_trip_duration,
        "most_frequent_travelers": most_frequent_travelers,
        "travel_by_purpose": travel_by_purpose,
    }

    serializer = TravelPatternAnalyticsSerializer(data)
    return success_response(
        data=serializer.data, message="Travel pattern analytics retrieved successfully"
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def booking_analytics(request):
    """
    Get booking analytics
    """
    user = request.user

    # Base queryset - per-module permission checks
    # Flights are tied to TRF admin
    if user.is_superuser or can_view_all(user, "trf"):
        flights = FlightBooking.objects.all()
    else:
        flights = FlightBooking.objects.filter(user=user)

    # Counts
    total_flight_bookings = flights.count()

    # Costs
    flight_cost = flights.aggregate(total=Sum("cost"))["total"] or Decimal("0.00")

    # Average booking lead time (days between booking and departure)
    average_booking_lead_time = 14.0  # Default

    # Preferred airlines
    preferred_airlines = list(
        flights.values("airline")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
        .values_list("airline", flat=True)
    )

    # Booking class distribution
    booking_class_distribution = dict(
        flights.values("booking_class")
        .annotate(count=Count("id"))
        .values_list("booking_class", "count")
    )

    data = {
        "total_flight_bookings": total_flight_bookings,
        "flight_cost": flight_cost,
        "average_booking_lead_time": average_booking_lead_time,
        "preferred_airlines": preferred_airlines,
        "booking_class_distribution": booking_class_distribution,
    }

    serializer = BookingAnalyticsSerializer(data)
    return success_response(
        data=serializer.data, message="Booking analytics retrieved successfully"
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def department_analytics(request):
    """
    Get department-wise analytics (admin only)
    """
    forbidden = _require_admin_reports_permission(request)
    if forbidden:
        return forbidden

    departments = []

    # Get all unique departments
    dept_users = (
        User.objects.exclude(department__isnull=True)
        .values("department__name")
        .distinct()
    )

    for dept in dept_users:
        dept_name = dept["department__name"]
        users_in_dept = User.objects.filter(department__name=dept_name)

        # Get TRFs for this department
        dept_trfs = TravelRequest.objects.filter(created_by__in=users_in_dept)

        total_trips = dept_trfs.count()
        total_spend = dept_trfs.aggregate(total=Sum("estimated_cost"))[
            "total"
        ] or Decimal("0.00")
        active_travelers = (
            users_in_dept.filter(travel_requests_created__isnull=False)
            .distinct()
            .count()
        )
        average_trip_cost = dept_trfs.aggregate(avg=Avg("estimated_cost"))[
            "avg"
        ] or Decimal("0.00")
        pending_approvals = dept_trfs.filter(status__icontains="Pending").count()

        departments.append(
            {
                "department_name": dept_name,
                "total_trips": total_trips,
                "total_spend": total_spend,
                "active_travelers": active_travelers,
                "average_trip_cost": average_trip_cost,
                "pending_approvals": pending_approvals,
            }
        )

    serializer = DepartmentAnalyticsSerializer(departments, many=True)
    return success_response(
        data=serializer.data, message="Department analytics retrieved successfully"
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_activity_report(request):
    """
    Get user activity report (admin only)
    """
    forbidden = _require_admin_reports_permission(request)
    if forbidden:
        return forbidden

    users = User.objects.all()
    user_activities = []

    for user in users[:50]:  # Limit to 50 users for performance
        total_trfs = user.travel_requests_created.count()
        total_bookings = user.flight_bookings.count()
        total_spend = user.travel_requests_created.aggregate(
            total=Sum("estimated_cost")
        )["total"] or Decimal("0.00")

        # Last activity
        last_activity = (
            user.travel_requests_created.aggregate(Max("created_at"))["created_at__max"]
            or timezone.now()
        )

        if total_trfs > 0 or total_bookings > 0:
            user_activities.append(
                {
                    "user_id": user.id,
                    "user_name": user.get_full_name(),
                    "email": user.email,
                    "total_trfs": total_trfs,
                    "total_bookings": total_bookings,
                    "total_spend": total_spend,
                    "last_activity": last_activity,
                }
            )

    serializer = UserActivitySerializer(user_activities, many=True)
    return success_response(
        data=serializer.data, message="User activity report retrieved successfully"
    )
