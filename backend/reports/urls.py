"""
Reports URL Configuration
"""
from django.urls import path
from .views import AdminReportsView

urlpatterns = [
    path('analytics/', AdminReportsView.as_view(), name='admin-analytics'),
]
