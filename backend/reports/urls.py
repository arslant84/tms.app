"""
Reports URL Configuration
"""
from django.urls import path
from .views import (
    AdminReportsView,
    DepartmentalReportsView,
    UserActivityReportsView,
    FinancialSummaryReportsView,
    ReportExportView
)

urlpatterns = [
    path('analytics/', AdminReportsView.as_view(), name='admin-analytics'),
    path('departmental/', DepartmentalReportsView.as_view(), name='departmental-reports'),
    path('user-activity/', UserActivityReportsView.as_view(), name='user-activity-reports'),
    path('financial/', FinancialSummaryReportsView.as_view(), name='financial-reports'),
    path('export/', ReportExportView.as_view(), name='report-export'),
]
