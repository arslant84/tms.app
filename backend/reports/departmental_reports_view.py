"""
DepartmentalReportsView - detailed per-department report breakdowns.

Split out of reports/views.py (see docs/CODEBASE_REFACTOR_ROADMAP.md
item 3) - a pure file move, no logic changed. Admin/user-activity/export
views moved to their own sibling modules in the same split.
"""

from datetime import timedelta

from accommodation.models import AccommodationRequest
from accounts.models import User
from django.core.cache import cache
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from transport.models import TransportRequest
from trf.models import TravelRequest
from utils.api_response import forbidden_response, success_response
from visa.models import VisaApplication
from workflows.models import WorkflowInstance

from .permissions import _resolve_department_scope


class DepartmentalReportsView(APIView):
    """
    Detailed departmental reports
    Shows comprehensive statistics for each department
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get detailed department reports
        Query params:
        - department: specific department name (optional)
        - date_range: week, month, quarter, year (default: month)
        """
        allowed, forced_department_id = _resolve_department_scope(request)
        if not allowed:
            return forbidden_response(
                message="You do not have permission to view departmental reports"
            )

        date_range = request.query_params.get("date_range", "month")
        department_filter = request.query_params.get("department")

        # Cache key encodes scope (forced vs free) + filter + range so different
        # users/departments never share each other's cached data.
        dept_scope = forced_department_id or "all"
        dept_param = department_filter or "all"
        cache_key = f"dept_report:{dept_scope}:{dept_param}:{date_range}"
        cached = cache.get(cache_key)
        if cached is not None:
            return success_response(
                data=cached,
                message="Departmental reports retrieved successfully",
                status_code=200,
            )

        # Calculate date range
        now = timezone.now()
        if date_range == "week":
            start_date = now - timedelta(days=7)
        elif date_range == "quarter":
            start_date = now - timedelta(days=90)
        elif date_range == "year":
            start_date = now - timedelta(days=365)
        else:  # month
            start_date = now - timedelta(days=30)

        # Get departments
        from accounts.models import Department

        if forced_department_id:
            # Department-locked caller (e.g. HOD): always their own
            # department, regardless of what ?department= they passed.
            department_ids = [forced_department_id]
        else:
            department_ids = User.objects.values_list(
                "department", flat=True
            ).distinct()
            if department_filter:
                department_ids = [department_filter]

        reports = []
        for dept_id in department_ids:
            if not dept_id:
                continue

            # Look up department name
            try:
                department = Department.objects.get(id=dept_id)
                dept_name = department.name
            except Department.DoesNotExist:
                dept_name = str(dept_id)  # Fallback to ID if not found

            dept_users = User.objects.filter(department=dept_id)

            # Get all request counts by type
            trf_count = TravelRequest.objects.filter(
                created_by__in=dept_users, created_at__gte=start_date
            ).count()

            transport_count = TransportRequest.objects.filter(
                requestor__in=dept_users, created_at__gte=start_date
            ).count()

            visa_count = VisaApplication.objects.filter(
                user__in=dept_users, created_at__gte=start_date
            ).count()

            accommodation_count = AccommodationRequest.objects.filter(
                trf__created_by__in=dept_users, created_at__gte=start_date
            ).count()

            total_requests = (
                trf_count + transport_count + visa_count + accommodation_count
            )

            # Get status breakdown
            approved = (
                TravelRequest.objects.filter(
                    created_by__in=dept_users,
                    created_at__gte=start_date,
                    status="Approved",
                ).count()
                + TransportRequest.objects.filter(
                    requestor__in=dept_users,
                    created_at__gte=start_date,
                    status="Approved",
                ).count()
                + VisaApplication.objects.filter(
                    user__in=dept_users, created_at__gte=start_date, status="Approved"
                ).count()
                + AccommodationRequest.objects.filter(
                    trf__created_by__in=dept_users,
                    created_at__gte=start_date,
                    status="Approved",
                ).count()
            )

            pending = (
                TravelRequest.objects.filter(
                    created_by__in=dept_users, created_at__gte=start_date
                )
                .exclude(status__in=["Approved", "Rejected", "Cancelled"])
                .count()
                + TransportRequest.objects.filter(
                    requestor__in=dept_users, created_at__gte=start_date
                )
                .exclude(status__in=["Approved", "Rejected", "Cancelled"])
                .count()
                + VisaApplication.objects.filter(
                    user__in=dept_users, created_at__gte=start_date
                )
                .exclude(status__in=["Approved", "Rejected", "Cancelled"])
                .count()
                + AccommodationRequest.objects.filter(
                    trf__created_by__in=dept_users, created_at__gte=start_date
                )
                .exclude(status__in=["Approved", "Rejected", "Cancelled"])
                .count()
            )

            rejected = (
                TravelRequest.objects.filter(
                    created_by__in=dept_users,
                    created_at__gte=start_date,
                    status="Rejected",
                ).count()
                + TransportRequest.objects.filter(
                    requestor__in=dept_users,
                    created_at__gte=start_date,
                    status="Rejected",
                ).count()
                + VisaApplication.objects.filter(
                    user__in=dept_users, created_at__gte=start_date, status="Rejected"
                ).count()
                + AccommodationRequest.objects.filter(
                    trf__created_by__in=dept_users,
                    created_at__gte=start_date,
                    status="Rejected",
                ).count()
            )

            # Calculate average processing time
            dept_workflows = WorkflowInstance.objects.filter(
                initiated_by__in=dept_users,
                status="approved",
                completed_at__gte=start_date,
            )

            avg_processing_time = 0
            if dept_workflows.exists():
                times = []
                for wf in dept_workflows:
                    if wf.started_at and wf.completed_at:
                        delta = wf.completed_at - wf.started_at
                        times.append(delta.total_seconds() / 3600)
                if times:
                    avg_processing_time = sum(times) / len(times)

            # Get top requestors in this department
            top_requestors = []
            for user in dept_users[:10]:  # Top 10 users
                user_requests = (
                    TravelRequest.objects.filter(
                        created_by=user, created_at__gte=start_date
                    ).count()
                    + TransportRequest.objects.filter(
                        requestor=user, created_at__gte=start_date
                    ).count()
                    + VisaApplication.objects.filter(
                        user=user, created_at__gte=start_date
                    ).count()
                )
                if user_requests > 0:
                    top_requestors.append(
                        {
                            "name": user.get_full_name() or user.email,
                            "email": user.email,
                            "requests": user_requests,
                        }
                    )

            top_requestors.sort(key=lambda x: x["requests"], reverse=True)
            top_requestors = top_requestors[:5]  # Keep top 5

            monthly_frequency = self._get_department_monthly_frequency(dept_users)

            reports.append(
                {
                    "department": dept_name,
                    "totalRequests": total_requests,
                    "breakdown": {
                        "travel": trf_count,
                        "transport": transport_count,
                        "visa": visa_count,
                        "accommodation": accommodation_count,
                    },
                    "status": {
                        "approved": approved,
                        "pending": pending,
                        "rejected": rejected,
                    },
                    "avgProcessingTime": round(avg_processing_time, 1),
                    "topRequestors": top_requestors,
                    "activeUsers": dept_users.count(),
                    "monthlyFrequency": monthly_frequency,
                }
            )

        # Sort by total requests
        reports.sort(key=lambda x: x["totalRequests"], reverse=True)

        report_data = {
            "reports": reports,
            "dateRange": date_range,
            "startDate": start_date.isoformat(),
            "endDate": now.isoformat(),
        }
        cache.set(cache_key, report_data, timeout=300)
        return success_response(
            data=report_data,
            message="Departmental reports retrieved successfully",
            status_code=200,
        )

    def _get_department_monthly_frequency(self, dept_users):
        """12-calendar-month trip-count trend for a department, broken out
        per request type. Fixed 12-month lookback independent of the
        date_range filter, same as AdminReportsView._get_monthly_trends -
        but using real calendar month boundaries via TruncMonth rather than
        30-day buckets."""
        now = timezone.now()
        current_month_start = now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        month_starts = []
        year, month = current_month_start.year, current_month_start.month
        for i in range(11, -1, -1):
            target_month = month - i
            target_year = year
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            month_starts.append(
                current_month_start.replace(year=target_year, month=target_month)
            )

        labels = [d.strftime("%b") for d in month_starts]
        window_start = month_starts[0]

        def bucket_counts(queryset):
            counts = [0] * len(month_starts)
            monthly = (
                queryset.filter(created_at__gte=window_start)
                .annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(count=Count("id"))
                .order_by("month")
            )
            for row in monthly:
                row_month = row["month"]
                for idx, month_start in enumerate(month_starts):
                    if (
                        row_month.year == month_start.year
                        and row_month.month == month_start.month
                    ):
                        counts[idx] = row["count"]
                        break
            return counts

        return {
            "labels": labels,
            "travel": bucket_counts(
                TravelRequest.objects.filter(created_by__in=dept_users)
            ),
            "transport": bucket_counts(
                TransportRequest.objects.filter(requestor__in=dept_users)
            ),
            "visa": bucket_counts(VisaApplication.objects.filter(user__in=dept_users)),
            "accommodation": bucket_counts(
                AccommodationRequest.objects.filter(trf__created_by__in=dept_users)
            ),
        }
