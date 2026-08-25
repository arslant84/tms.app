"""
Reports URL Configuration
"""

from django.urls import path

from .admin_reports_view import AdminReportsView
from .departmental_reports_view import DepartmentalReportsView
from .report_export_view import ReportExportView
from .user_activity_reports_view import UserActivityReportsView

urlpatterns = [
    path("analytics/", AdminReportsView.as_view(), name="admin-analytics"),
    path(
        "departmental/", DepartmentalReportsView.as_view(), name="departmental-reports"
    ),
    path(
        "user-activity/",
        UserActivityReportsView.as_view(),
        name="user-activity-reports",
    ),
    path("export/", ReportExportView.as_view(), name="report-export"),
]
