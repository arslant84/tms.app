"""
AdminReportsView - main analytics endpoint for the admin dashboard.

Split out of reports/views.py (see docs/CODEBASE_REFACTOR_ROADMAP.md
item 3) - a pure file move, no logic changed. Departmental/user-activity/
export views moved to their own sibling modules in the same split.
"""

from datetime import timedelta

from accommodation.models import AccommodationRequest
from accounts.models import User
from django.core.cache import cache
from django.db.models import Avg, Count
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from transport.models import TransportRequest
from trf.models import TravelRequest
from utils.api_response import success_response
from visa.models import VisaApplication
from workflows.models import WorkflowInstance, WorkflowStepExecution

from .permissions import _require_admin_reports_permission


class AdminReportsView(APIView):
    """
    Main reports endpoint for admin analytics
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get comprehensive report data
        Query params:
        - date_range: week, month, quarter, year (default: month)
        """
        forbidden = _require_admin_reports_permission(request)
        if forbidden:
            return forbidden

        date_range = request.query_params.get("date_range", "month")

        # Serve from cache if available (5-minute TTL — report data changes rarely
        # within a single working session and these queries are expensive)
        cache_key = f"admin_report:{date_range}"
        cached = cache.get(cache_key)
        if cached is not None:
            return success_response(
                data=cached,
                message="Admin reports retrieved successfully",
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

        # Get all requests within date range
        trf_requests = TravelRequest.objects.filter(created_at__gte=start_date)
        transport_requests = TransportRequest.objects.filter(created_at__gte=start_date)
        visa_requests = VisaApplication.objects.filter(created_at__gte=start_date)
        accommodation_requests = AccommodationRequest.objects.filter(
            created_at__gte=start_date
        )

        # Calculate key metrics
        total_requests = (
            trf_requests.count()
            + transport_requests.count()
            + visa_requests.count()
            + accommodation_requests.count()
        )

        # Get previous period for comparison
        previous_start = start_date - (now - start_date)
        previous_total = (
            TravelRequest.objects.filter(
                created_at__gte=previous_start, created_at__lt=start_date
            ).count()
            + TransportRequest.objects.filter(
                created_at__gte=previous_start, created_at__lt=start_date
            ).count()
            + VisaApplication.objects.filter(
                created_at__gte=previous_start, created_at__lt=start_date
            ).count()
            + AccommodationRequest.objects.filter(
                created_at__gte=previous_start, created_at__lt=start_date
            ).count()
        )

        # Calculate percentage change
        total_change = (
            ((total_requests - previous_total) / previous_total * 100)
            if previous_total > 0
            else 0
        )

        # Calculate average processing time (from workflows)
        completed_workflows = WorkflowInstance.objects.filter(
            status="approved", completed_at__gte=start_date
        )

        avg_processing_hours = 0
        if completed_workflows.exists():
            processing_times = []
            for wf in completed_workflows:
                if wf.started_at and wf.completed_at:
                    delta = wf.completed_at - wf.started_at
                    processing_times.append(
                        delta.total_seconds() / 3600
                    )  # Convert to hours

            if processing_times:
                avg_processing_hours = sum(processing_times) / len(processing_times)

        # Previous period processing time
        previous_completed_workflows = WorkflowInstance.objects.filter(
            status="approved",
            completed_at__gte=previous_start,
            completed_at__lt=start_date,
        )

        previous_avg_hours = 0
        if previous_completed_workflows.exists():
            prev_times = []
            for wf in previous_completed_workflows:
                if wf.started_at and wf.completed_at:
                    delta = wf.completed_at - wf.started_at
                    prev_times.append(delta.total_seconds() / 3600)
            if prev_times:
                previous_avg_hours = sum(prev_times) / len(prev_times)

        processing_change = (
            ((avg_processing_hours - previous_avg_hours) / previous_avg_hours * 100)
            if previous_avg_hours > 0
            else 0
        )

        # Calculate completion rate
        total_workflows = WorkflowInstance.objects.filter(
            started_at__gte=start_date
        ).count()
        completed_count = completed_workflows.count()
        completion_rate = (
            (completed_count / total_workflows * 100) if total_workflows > 0 else 0
        )

        # Previous period completion rate
        prev_total_workflows = WorkflowInstance.objects.filter(
            started_at__gte=previous_start, started_at__lt=start_date
        ).count()
        prev_completed = WorkflowInstance.objects.filter(
            status="approved",
            completed_at__gte=previous_start,
            completed_at__lt=start_date,
        ).count()
        prev_completion_rate = (
            (prev_completed / prev_total_workflows * 100)
            if prev_total_workflows > 0
            else 0
        )
        completion_change = completion_rate - prev_completion_rate

        # Pending requests
        pending_count = (
            trf_requests.exclude(
                status__in=["Approved", "Rejected", "Cancelled"]
            ).count()
            + transport_requests.exclude(
                status__in=["Approved", "Rejected", "Cancelled"]
            ).count()
            + visa_requests.exclude(
                status__in=["Approved", "Rejected", "Cancelled"]
            ).count()
            + accommodation_requests.exclude(
                status__in=["Approved", "Rejected", "Cancelled"]
            ).count()
        )

        previous_pending = (
            TravelRequest.objects.filter(
                created_at__gte=previous_start, created_at__lt=start_date
            )
            .exclude(status__in=["Approved", "Rejected", "Cancelled"])
            .count()
            + TransportRequest.objects.filter(
                created_at__gte=previous_start, created_at__lt=start_date
            )
            .exclude(status__in=["Approved", "Rejected", "Cancelled"])
            .count()
            + VisaApplication.objects.filter(
                created_at__gte=previous_start, created_at__lt=start_date
            )
            .exclude(status__in=["Approved", "Rejected", "Cancelled"])
            .count()
            + AccommodationRequest.objects.filter(
                created_at__gte=previous_start, created_at__lt=start_date
            )
            .exclude(status__in=["Approved", "Rejected", "Cancelled"])
            .count()
        )

        pending_change = (
            ((pending_count - previous_pending) / previous_pending * 100)
            if previous_pending > 0
            else 0
        )

        # Requests by type
        requests_by_type = {
            "labels": ["Travel", "Transport", "Visa", "Accommodation"],
            "data": [
                trf_requests.count(),
                transport_requests.count(),
                visa_requests.count(),
                accommodation_requests.count(),
            ],
        }

        # Processing time by type
        processing_by_type = {
            "labels": ["Travel", "Transport", "Visa", "Accommodation"],
            "data": [],
        }

        # Calculate processing time for each type. TravelRequest can route through
        # either the shared "travelrequest" template or one of its per-travel-type
        # templates (see docs/TSR_SUBMODULE_WORKFLOW_ROADMAP.md), so it's matched
        # against all of those entity_types rather than a single literal.
        travelrequest_entity_types = ["travelrequest"] + list(
            TravelRequest.WORKFLOW_ENTITY_TYPE_MAP.values()
        )
        for model, entity_types in [
            (TravelRequest, travelrequest_entity_types),
            (TransportRequest, ["transportrequest"]),
            (VisaApplication, ["visaapplication"]),
            (AccommodationRequest, ["accommodation"]),
        ]:
            workflows = WorkflowInstance.objects.filter(
                workflow_template__entity_type__in=entity_types,
                status="approved",
                completed_at__gte=start_date,
            )

            if workflows.exists():
                times = []
                for wf in workflows:
                    if wf.started_at and wf.completed_at:
                        delta = wf.completed_at - wf.started_at
                        times.append(delta.total_seconds() / 3600)
                avg_time = sum(times) / len(times) if times else 0
                processing_by_type["data"].append(round(avg_time, 1))
            else:
                processing_by_type["data"].append(0)

        # Request trends (last 12 months)
        months_data = self._get_monthly_trends()

        # Department statistics
        department_stats = self._get_department_stats(start_date)

        # Top performers (users with most approvals)
        top_performers = self._get_top_performers(start_date)

        report_data = {
            "key_metrics": [
                {
                    "name": "Total Requests",
                    "value": total_requests,
                    "change": round(total_change, 1),
                    "trend": (
                        "up"
                        if total_change > 0
                        else "down" if total_change < 0 else "neutral"
                    ),
                    "icon": "bi-file-earmark-text",
                },
                {
                    "name": "Avg. Processing Time",
                    "value": round(avg_processing_hours, 0),
                    "change": round(processing_change, 1),
                    "trend": (
                        "down"
                        if processing_change < 0
                        else "up" if processing_change > 0 else "neutral"
                    ),
                    "icon": "bi-clock",
                },
                {
                    "name": "Completion Rate",
                    "value": round(completion_rate, 0),
                    "change": round(completion_change, 1),
                    "trend": (
                        "up"
                        if completion_change > 0
                        else "down" if completion_change < 0 else "neutral"
                    ),
                    "icon": "bi-check-circle",
                },
                {
                    "name": "Pending Requests",
                    "value": pending_count,
                    "change": round(pending_change, 1),
                    "trend": (
                        "down"
                        if pending_change < 0
                        else "up" if pending_change > 0 else "neutral"
                    ),
                    "icon": "bi-hourglass-split",
                },
            ],
            "requests_by_type": requests_by_type,
            "processing_by_type": processing_by_type,
            "monthly_trends": months_data,
            "department_stats": department_stats,
            "top_performers": top_performers,
        }

        cache.set(cache_key, report_data, timeout=300)
        return success_response(
            data=report_data,
            message="Admin reports retrieved successfully",
            status_code=200,
        )

    def _get_monthly_trends(self):
        """Get request trends for last 12 months"""
        now = timezone.now()
        months = []
        submitted_data = []
        completed_data = []

        for i in range(11, -1, -1):
            month_start = timezone.datetime(
                now.year, now.month, 1, tzinfo=timezone.get_current_timezone()
            ) - timedelta(days=30 * i)
            month_end = month_start + timedelta(days=30)

            months.append(month_start.strftime("%b"))

            # Count submitted requests
            submitted = (
                TravelRequest.objects.filter(
                    created_at__gte=month_start, created_at__lt=month_end
                ).count()
                + TransportRequest.objects.filter(
                    created_at__gte=month_start, created_at__lt=month_end
                ).count()
                + VisaApplication.objects.filter(
                    created_at__gte=month_start, created_at__lt=month_end
                ).count()
                + AccommodationRequest.objects.filter(
                    created_at__gte=month_start, created_at__lt=month_end
                ).count()
            )
            submitted_data.append(submitted)

            # Count completed workflows
            completed = WorkflowInstance.objects.filter(
                status="approved",
                completed_at__gte=month_start,
                completed_at__lt=month_end,
            ).count()
            completed_data.append(completed)

        return {
            "labels": months,
            "submitted": submitted_data,
            "completed": completed_data,
        }

    def _get_department_stats(self, start_date):
        """Get statistics by department"""
        from accounts.models import Department

        # Get distinct department IDs from users
        department_ids = User.objects.values_list("department", flat=True).distinct()
        stats = []

        for dept_id in department_ids:
            if not dept_id:
                continue

            # Look up department name
            try:
                department = Department.objects.get(id=dept_id)
                dept_name = department.name
            except Department.DoesNotExist:
                dept_name = str(dept_id)  # Fallback to ID if not found

            # Get all requests from users in this department
            dept_users = User.objects.filter(department=dept_id)

            total = (
                TravelRequest.objects.filter(
                    created_by__in=dept_users, created_at__gte=start_date
                ).count()
                + TransportRequest.objects.filter(
                    requestor__in=dept_users, created_at__gte=start_date
                ).count()
                + VisaApplication.objects.filter(
                    user__in=dept_users, created_at__gte=start_date
                ).count()
                + AccommodationRequest.objects.filter(
                    trf__created_by__in=dept_users, created_at__gte=start_date
                ).count()
            )

            if total == 0:
                continue

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

            completed = (
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

            # Calculate average processing time for this department
            dept_workflows = WorkflowInstance.objects.filter(
                initiated_by__in=dept_users,
                status="approved",
                completed_at__gte=start_date,
            )

            avg_time = 0
            if dept_workflows.exists():
                times = []
                for wf in dept_workflows:
                    if wf.started_at and wf.completed_at:
                        delta = wf.completed_at - wf.started_at
                        times.append(delta.total_seconds() / 3600)
                if times:
                    avg_time = sum(times) / len(times)

            stats.append(
                {
                    "department": dept_name,
                    "total": total,
                    "pending": pending,
                    "completed": completed,
                    "avgProcessingTime": round(avg_time, 1),
                }
            )

        # Sort by total requests
        stats.sort(key=lambda x: x["total"], reverse=True)
        return stats

    def _get_top_performers(self, start_date):
        """Get top performing approvers"""
        # Get users who have approved steps
        approvers = (
            WorkflowStepExecution.objects.filter(
                status="approved",
                action_date__gte=start_date,
                actioned_by__isnull=False,
            )
            .values("actioned_by")
            .annotate(processed=Count("id"))
            .order_by("-processed")[:5]
        )

        performers = []
        for approver in approvers:
            user = User.objects.get(id=approver["actioned_by"])

            # Calculate average processing time for this user
            user_steps = WorkflowStepExecution.objects.filter(
                actioned_by=user, status="approved", action_date__gte=start_date
            )

            times = []
            for step in user_steps:
                if step.created_at and step.action_date:
                    delta = step.action_date - step.created_at
                    times.append(delta.total_seconds() / 3600)

            avg_time = sum(times) / len(times) if times else 0

            performers.append(
                {
                    "name": user.get_full_name() or user.email,
                    "processed": approver["processed"],
                    "avgTime": round(avg_time, 1),
                }
            )

        return performers
