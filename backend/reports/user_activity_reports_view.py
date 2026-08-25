"""
UserActivityReportsView - per-user activity reports.

Split out of reports/views.py (see docs/CODEBASE_REFACTOR_ROADMAP.md
item 3) - a pure file move, no logic changed. Admin/departmental/export
views moved to their own sibling modules in the same split.
"""

from datetime import timedelta

from accounts.models import User
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from transport.models import TransportRequest
from trf.models import TravelRequest
from utils.api_response import error_response, success_response
from visa.models import VisaApplication
from workflows.models import WorkflowStepExecution

from .permissions import _require_admin_reports_permission


class UserActivityReportsView(APIView):
    """
    User activity reports
    Shows detailed activity for individual users or all users
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get user activity reports
        Query params:
        - user_id: specific user ID (optional)
        - date_range: week, month, quarter, year (default: month)
        - activity_type: requests, approvals, all (default: all)
        """
        forbidden = _require_admin_reports_permission(request)
        if forbidden:
            return forbidden

        date_range = request.query_params.get("date_range", "month")
        user_id = request.query_params.get("user_id")
        activity_type = request.query_params.get("activity_type", "all")

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

        # Get users
        if user_id:
            try:
                users = [User.objects.get(id=user_id)]
            except User.DoesNotExist:
                return error_response(message="User not found", status_code=404)
        else:
            users = User.objects.all()[:50]  # Limit to 50 users for performance

        user_activities = []
        for user in users:
            # Get department name
            dept_name = user.department.name if user.department else None

            activity = {
                "userId": user.id,
                "name": user.get_full_name() or user.email,
                "email": user.email,
                "department": dept_name,
            }

            # Requests submitted
            if activity_type in ["requests", "all"]:
                travel_requests = TravelRequest.objects.filter(
                    created_by=user, created_at__gte=start_date
                ).count()

                transport_requests = TransportRequest.objects.filter(
                    requestor=user, created_at__gte=start_date
                ).count()

                visa_requests = VisaApplication.objects.filter(
                    user=user, created_at__gte=start_date
                ).count()

                activity["requestsSubmitted"] = {
                    "total": travel_requests + transport_requests + visa_requests,
                    "travel": travel_requests,
                    "transport": transport_requests,
                    "visa": visa_requests,
                }

            # Approvals processed
            if activity_type in ["approvals", "all"]:
                approvals = WorkflowStepExecution.objects.filter(
                    actioned_by=user, action_date__gte=start_date
                )

                approved_count = approvals.filter(status="approved").count()
                rejected_count = approvals.filter(status="rejected").count()
                pending_count = approvals.filter(status="pending").count()

                # Calculate average approval time
                approval_times = []
                for approval in approvals.filter(status__in=["approved", "rejected"]):
                    if approval.created_at and approval.action_date:
                        delta = approval.action_date - approval.created_at
                        approval_times.append(delta.total_seconds() / 3600)

                avg_approval_time = (
                    sum(approval_times) / len(approval_times) if approval_times else 0
                )

                activity["approvalsProcessed"] = {
                    "total": approvals.count(),
                    "approved": approved_count,
                    "rejected": rejected_count,
                    "pending": pending_count,
                    "avgTimeHours": round(avg_approval_time, 1),
                }

            # Last activity
            last_request = (
                TravelRequest.objects.filter(created_by=user)
                .order_by("-created_at")
                .first()
            )
            last_approval = (
                WorkflowStepExecution.objects.filter(actioned_by=user)
                .order_by("-action_date")
                .first()
            )

            last_activity_date = None
            if last_request and last_approval:
                last_activity_date = max(
                    last_request.created_at,
                    last_approval.action_date or last_approval.created_at,
                )
            elif last_request:
                last_activity_date = last_request.created_at
            elif last_approval:
                last_activity_date = (
                    last_approval.action_date or last_approval.created_at
                )

            activity["lastActivityDate"] = (
                last_activity_date.isoformat() if last_activity_date else None
            )

            user_activities.append(activity)

        # Sort by total activity (requests + approvals)
        user_activities.sort(
            key=lambda x: x.get("requestsSubmitted", {}).get("total", 0)
            + x.get("approvalsProcessed", {}).get("total", 0),
            reverse=True,
        )

        return success_response(
            data={
                "users": user_activities,
                "dateRange": date_range,
                "activityType": activity_type,
                "startDate": start_date.isoformat(),
                "endDate": now.isoformat(),
            },
            message="User activity reports retrieved successfully",
            status_code=200,
        )
