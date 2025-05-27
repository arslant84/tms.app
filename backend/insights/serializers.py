from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    TravelInsight, DestinationStat, CategorySpend, 
    MonthlyTrend, TravelAnalytics, InsightType
)

User = get_user_model()


class DestinationStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = DestinationStat
        fields = ['id', 'destination', 'count', 'average_cost']
        read_only_fields = ['id']


class CategorySpendSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategorySpend
        fields = ['id', 'category', 'amount', 'percentage']
        read_only_fields = ['id']


class MonthlyTrendSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyTrend
        fields = ['id', 'month', 'year', 'trip_count', 'total_spend']
        read_only_fields = ['id']


class TravelInsightSerializer(serializers.ModelSerializer):
    user_id = serializers.ReadOnlyField()
    
    class Meta:
        model = TravelInsight
        fields = [
            'id', 'user', 'user_id', 'title', 'description', 'insight_type',
            'potential_savings', 'relevance_score', 'expiry_date', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TravelAnalyticsSerializer(serializers.ModelSerializer):
    top_destinations = DestinationStatSerializer(many=True, read_only=True)
    spend_by_category = CategorySpendSerializer(many=True, read_only=True)
    monthly_trend = MonthlyTrendSerializer(many=True, read_only=True)
    
    class Meta:
        model = TravelAnalytics
        fields = [
            'id', 'user', 'total_trips', 'total_spend', 'average_trip_cost',
            'savings_opportunities', 'top_destinations', 'spend_by_category',
            'monthly_trend', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
