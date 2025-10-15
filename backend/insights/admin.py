from django.contrib import admin
from .models import TravelInsight, DestinationStat, CategorySpend, MonthlyTrend, TravelAnalytics


@admin.register(TravelInsight)
class TravelInsightAdmin(admin.ModelAdmin):
    """Admin configuration for TravelInsight model"""
    list_display = ['id', 'user', 'title', 'insight_type', 'potential_savings', 'relevance_score', 'created_at']
    list_filter = ['insight_type', 'created_at', 'expiry_date']
    search_fields = ['title', 'description', 'user__email', 'user__first_name', 'user__last_name']
    ordering = ['-relevance_score', '-created_at']
    readonly_fields = ['created_at']


@admin.register(DestinationStat)
class DestinationStatAdmin(admin.ModelAdmin):
    """Admin configuration for DestinationStat model"""
    list_display = ['id', 'destination', 'count', 'average_cost']
    search_fields = ['destination']
    ordering = ['-count']


@admin.register(CategorySpend)
class CategorySpendAdmin(admin.ModelAdmin):
    """Admin configuration for CategorySpend model"""
    list_display = ['id', 'category', 'amount', 'percentage']
    search_fields = ['category']
    ordering = ['-amount']


@admin.register(MonthlyTrend)
class MonthlyTrendAdmin(admin.ModelAdmin):
    """Admin configuration for MonthlyTrend model"""
    list_display = ['id', 'month', 'year', 'trip_count', 'total_spend']
    list_filter = ['year', 'month']
    ordering = ['-year', '-month']


@admin.register(TravelAnalytics)
class TravelAnalyticsAdmin(admin.ModelAdmin):
    """Admin configuration for TravelAnalytics model"""
    list_display = ['id', 'user', 'total_trips', 'total_spend', 'average_trip_cost', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']
