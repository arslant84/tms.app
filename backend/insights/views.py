from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Sum, Avg, Count
from django.contrib.auth import get_user_model

from .models import (
    TravelInsight, DestinationStat, CategorySpend, 
    MonthlyTrend, TravelAnalytics, InsightType
)
from .serializers import (
    TravelInsightSerializer, TravelAnalyticsSerializer,
    DestinationStatSerializer, CategorySpendSerializer, MonthlyTrendSerializer
)

User = get_user_model()


class TravelInsightViewSet(viewsets.ModelViewSet):
    queryset = TravelInsight.objects.all()
    serializer_class = TravelInsightSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'relevance_score', 'insight_type']
    ordering = ['-relevance_score']
    
    def get_queryset(self):
        user = self.request.user
        
        # Admin can see all insights
        if user.is_admin:
            return TravelInsight.objects.all()
        
        # Regular users can only see their own insights
        return TravelInsight.objects.filter(user=user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TravelAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TravelAnalytics.objects.all()
    serializer_class = TravelAnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Admin and managers can see all analytics
        if user.is_admin or user.role in ['focal', 'hod']:
            return TravelAnalytics.objects.all()
        
        # Regular users can only see their own analytics
        return TravelAnalytics.objects.filter(user=user)
    
    @action(detail=False, methods=['get'])
    def my_analytics(self, request):
        """Get the current user's analytics"""
        user = request.user
        analytics = TravelAnalytics.objects.filter(user=user).first()
        
        if not analytics:
            # If no analytics exist, return empty data
            return Response({
                'total_trips': 0,
                'total_spend': 0,
                'average_trip_cost': 0,
                'savings_opportunities': 0,
                'top_destinations': [],
                'spend_by_category': [],
                'monthly_trend': []
            })
        
        serializer = self.get_serializer(analytics)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def company_analytics(self, request):
        """Get company-wide analytics (admin only)"""
        user = request.user
        
        if not (user.is_admin or user.role in ['focal', 'hod']):
            return Response(
                {'error': 'You do not have permission to view company-wide analytics'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get company-wide analytics (where user is null)
        analytics = TravelAnalytics.objects.filter(user=None).first()
        
        if not analytics:
            # If no analytics exist, return empty data
            return Response({
                'total_trips': 0,
                'total_spend': 0,
                'average_trip_cost': 0,
                'savings_opportunities': 0,
                'top_destinations': [],
                'spend_by_category': [],
                'monthly_trend': []
            })
        
        serializer = self.get_serializer(analytics)
        return Response(serializer.data)
