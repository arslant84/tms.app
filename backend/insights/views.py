from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Q, Sum, Avg, Count, F, Max
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from .models import (
    TravelInsight, DestinationStat, CategorySpend,
    MonthlyTrend, TravelAnalytics, InsightType
)
from .serializers import (
    TravelInsightSerializer, TravelAnalyticsSerializer,
    DestinationStatSerializer, CategorySpendSerializer, MonthlyTrendSerializer,
    DashboardSummarySerializer, TravelSpendAnalyticsSerializer,
    TravelPatternAnalyticsSerializer, BookingAnalyticsSerializer,
    ExpenseAnalyticsSerializer, DepartmentAnalyticsSerializer,
    UserActivitySerializer, ComplianceReportSerializer
)

# Import models from other apps for analytics
from trf.models import TravelRequest
from expenses.models import ExpenseClaim
from bookings.models import FlightBooking, HotelBooking
from accounts.models import User


class TravelInsightViewSet(viewsets.ModelViewSet):
    """ViewSet for travel insights"""
    queryset = TravelInsight.objects.all()
    serializer_class = TravelInsightSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'relevance_score', 'insight_type']
    ordering = ['-relevance_score']

    def get_queryset(self):
        user = self.request.user

        # Admin can see all insights
        if user.is_staff:
            queryset = TravelInsight.objects.all()
        else:
            # Regular users can only see their own insights
            queryset = TravelInsight.objects.filter(user=user)

        # Filter by insight type
        insight_type = self.request.query_params.get('insight_type', None)
        if insight_type:
            queryset = queryset.filter(insight_type=insight_type)

        # Filter by expiry
        include_expired = self.request.query_params.get('include_expired', 'false')
        if include_expired.lower() != 'true':
            today = timezone.now().date()
            queryset = queryset.filter(Q(expiry_date__gte=today) | Q(expiry_date__isnull=True))

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TravelAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for travel analytics"""
    queryset = TravelAnalytics.objects.all()
    serializer_class = TravelAnalyticsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Admin can see all analytics
        if user.is_staff:
            return TravelAnalytics.objects.all()

        # Regular users can only see their own analytics
        return TravelAnalytics.objects.filter(user=user)

    @action(detail=False, methods=['get'])
    def my_analytics(self, request):
        """Get the current user's analytics"""
        user = request.user
        analytics = TravelAnalytics.objects.filter(user=user).first()

        if not analytics:
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
        if not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to view company-wide analytics'},
                status=status.HTTP_403_FORBIDDEN
            )

        analytics = TravelAnalytics.objects.filter(user=None).first()

        if not analytics:
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    """
    Get dashboard summary statistics
    """
    user = request.user

    # Filter data based on user role
    if user.is_staff:
        trfs = TravelRequest.objects.all()
        claims = ExpenseClaim.objects.all()
        flights = FlightBooking.objects.all()
        hotels = HotelBooking.objects.all()
    else:
        trfs = TravelRequest.objects.filter(user=user)
        claims = ExpenseClaim.objects.filter(user=user)
        flights = FlightBooking.objects.filter(user=user)
        hotels = HotelBooking.objects.filter(user=user)

    # Calculate statistics
    total_trfs = trfs.count()
    # Use case-insensitive contains for dynamic workflow statuses
    pending_trfs = trfs.filter(status__icontains='Pending').count()
    approved_trfs = trfs.filter(status='Approved').count()
    rejected_trfs = trfs.filter(status='Rejected').count()

    # Calculate total travel cost from TRFs
    total_travel_cost = trfs.aggregate(
        total=Sum('estimated_cost')
    )['total'] or Decimal('0.00')

    # Calculate total expense claims (count of draft claims, not sum)
    total_expense_claims = claims.filter(status='Draft').count()

    # Active bookings
    active_bookings = flights.filter(status__in=['CONFIRMED', 'TICKETED']).count()
    active_bookings += hotels.filter(status__in=['CONFIRMED']).count()

    # Pending approvals (use case-insensitive contains for dynamic statuses)
    pending_approvals = trfs.filter(status__icontains='Pending').count()
    pending_approvals += claims.filter(status__icontains='Pending').count()

    # Recent activities (last 5)
    recent_activities = []
    recent_trfs = trfs.order_by('-created_at')[:3]
    for trf in recent_trfs:
        recent_activities.append({
            'type': 'trf',
            'id': trf.id,
            'title': f"TRF #{trf.id}",
            'status': trf.status,
            'date': trf.created_at
        })

    data = {
        'total_trfs': total_trfs,
        'pending_trfs': pending_trfs,
        'approved_trfs': approved_trfs,
        'rejected_trfs': rejected_trfs,
        'total_travel_cost': total_travel_cost,
        'total_expense_claims': total_expense_claims,
        'active_bookings': active_bookings,
        'pending_approvals': pending_approvals,
        'recent_activities': recent_activities
    }

    serializer = DashboardSummarySerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def travel_spend_analytics(request):
    """
    Get travel spend analytics
    """
    user = request.user

    # Get date range from query params
    date_from = request.query_params.get('date_from', None)
    date_to = request.query_params.get('date_to', None)

    # Base queryset
    if user.is_staff:
        trfs = TravelRequest.objects.all()
        claims = ExpenseClaim.objects.all()
    else:
        trfs = TravelRequest.objects.filter(user=user)
        claims = ExpenseClaim.objects.filter(user=user)

    # Apply date filters
    if date_from:
        trfs = trfs.filter(created_at__gte=date_from)
        claims = claims.filter(created_at__gte=date_from)
    if date_to:
        trfs = trfs.filter(created_at__lte=date_to)
        claims = claims.filter(created_at__lte=date_to)

    # Total spend
    total_spend = trfs.aggregate(total=Sum('estimated_cost'))['total'] or Decimal('0.00')
    total_spend += claims.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    # By category (from expenses)
    by_category = dict(
        claims.values('category')
        .annotate(total=Sum('total_amount'))
        .values_list('category', 'total')
    )

    # By department (from user's department)
    by_department = {}
    if user.is_staff:
        dept_data = trfs.values('user__department__name').annotate(
            total=Sum('estimated_cost')
        )
        for item in dept_data:
            dept_name = item['user__department__name'] or 'Unknown'
            by_department[dept_name] = float(item['total'] or 0)

    # By month (last 12 months)
    by_month = []
    for i in range(12):
        month_start = timezone.now().date() - timedelta(days=30*i)
        month_trfs = trfs.filter(
            created_at__year=month_start.year,
            created_at__month=month_start.month
        )
        month_total = month_trfs.aggregate(total=Sum('estimated_cost'))['total'] or Decimal('0.00')

        by_month.append({
            'month': month_start.strftime('%b %Y'),
            'amount': float(month_total)
        })

    by_month.reverse()

    # Top spenders (admin only)
    top_spenders = []
    if user.is_staff:
        top_users = trfs.values('user__id', 'user__first_name', 'user__last_name').annotate(
            total=Sum('estimated_cost')
        ).order_by('-total')[:10]

        for item in top_users:
            top_spenders.append({
                'user_id': item['user__id'],
                'user_name': f"{item['user__first_name']} {item['user__last_name']}",
                'total_spend': float(item['total'] or 0)
            })

    data = {
        'total_spend': total_spend,
        'by_category': by_category,
        'by_department': by_department,
        'by_month': by_month,
        'top_spenders': top_spenders,
        'budget_utilization': Decimal('0.00')  # Can be calculated if budget is defined
    }

    serializer = TravelSpendAnalyticsSerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def travel_pattern_analytics(request):
    """
    Get travel pattern analytics
    """
    user = request.user

    # Base queryset
    if user.is_staff:
        trfs = TravelRequest.objects.all()
    else:
        trfs = TravelRequest.objects.filter(user=user)

    # Total trips
    total_trips = trfs.count()
    domestic_trips = trfs.filter(travel_type='DOMESTIC').count()
    international_trips = trfs.filter(travel_type='OVERSEAS').count()

    # Top destinations (would need to parse from TRF data)
    top_destinations = []

    # Average trip duration (would need start/end dates from TRF)
    average_trip_duration = 5.0  # Default

    # Most frequent travelers (admin only)
    most_frequent_travelers = []
    if user.is_staff:
        freq_travelers = User.objects.annotate(
            trip_count=Count('travel_requests')
        ).order_by('-trip_count')[:10]

        for traveler in freq_travelers:
            if traveler.trip_count > 0:
                most_frequent_travelers.append({
                    'user_id': traveler.id,
                    'user_name': traveler.get_full_name(),
                    'trip_count': traveler.trip_count
                })

    # Travel by purpose
    travel_by_purpose = dict(
        trfs.values('purpose_of_travel')
        .annotate(count=Count('id'))
        .values_list('purpose_of_travel', 'count')
    )

    data = {
        'total_trips': total_trips,
        'domestic_trips': domestic_trips,
        'international_trips': international_trips,
        'top_destinations': top_destinations,
        'average_trip_duration': average_trip_duration,
        'most_frequent_travelers': most_frequent_travelers,
        'travel_by_purpose': travel_by_purpose
    }

    serializer = TravelPatternAnalyticsSerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def booking_analytics(request):
    """
    Get booking analytics
    """
    user = request.user

    # Base queryset
    if user.is_staff:
        flights = FlightBooking.objects.all()
        hotels = HotelBooking.objects.all()
    else:
        flights = FlightBooking.objects.filter(user=user)
        hotels = HotelBooking.objects.filter(user=user)

    # Counts
    total_flight_bookings = flights.count()
    total_hotel_bookings = hotels.count()

    # Costs
    flight_cost = flights.aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
    hotel_cost = hotels.aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

    # Average booking lead time (days between booking and departure)
    average_booking_lead_time = 14.0  # Default

    # Preferred airlines
    preferred_airlines = list(
        flights.values('airline')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
        .values_list('airline', flat=True)
    )

    # Preferred hotels
    preferred_hotels = list(
        hotels.values('hotel_name')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
        .values_list('hotel_name', flat=True)
    )

    # Booking class distribution
    booking_class_distribution = dict(
        flights.values('booking_class')
        .annotate(count=Count('id'))
        .values_list('booking_class', 'count')
    )

    data = {
        'total_flight_bookings': total_flight_bookings,
        'total_hotel_bookings': total_hotel_bookings,
        'flight_cost': flight_cost,
        'hotel_cost': hotel_cost,
        'average_booking_lead_time': average_booking_lead_time,
        'preferred_airlines': preferred_airlines,
        'preferred_hotels': preferred_hotels,
        'booking_class_distribution': booking_class_distribution
    }

    serializer = BookingAnalyticsSerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def expense_analytics(request):
    """
    Get expense analytics
    """
    user = request.user

    # Base queryset
    if user.is_staff:
        claims = ExpenseClaim.objects.all()
    else:
        claims = ExpenseClaim.objects.filter(user=user)

    # Counts and totals
    total_claims = claims.count()
    total_amount = claims.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    approved_amount = claims.filter(status='APPROVED').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    pending_amount = claims.filter(status='PENDING').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    # By category
    by_category = dict(
        claims.values('category')
        .annotate(total=Sum('total_amount'))
        .values_list('category', 'total')
    )

    # By status
    by_status = dict(
        claims.values('status')
        .annotate(count=Count('id'))
        .values_list('status', 'count')
    )

    # Average claim amount
    average_claim_amount = claims.aggregate(avg=Avg('total_amount'))['avg'] or Decimal('0.00')

    # Top expense categories
    top_expense_categories = list(
        claims.values('category')
        .annotate(total=Sum('total_amount'))
        .order_by('-total')[:5]
        .values('category', 'total')
    )

    data = {
        'total_claims': total_claims,
        'total_amount': total_amount,
        'approved_amount': approved_amount,
        'pending_amount': pending_amount,
        'by_category': by_category,
        'by_status': by_status,
        'average_claim_amount': average_claim_amount,
        'top_expense_categories': top_expense_categories
    }

    serializer = ExpenseAnalyticsSerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def department_analytics(request):
    """
    Get department-wise analytics (admin only)
    """
    departments = []

    # Get all unique departments
    dept_users = User.objects.exclude(department__isnull=True).values('department__name').distinct()

    for dept in dept_users:
        dept_name = dept['department__name']
        users_in_dept = User.objects.filter(department__name=dept_name)

        # Get TRFs for this department
        dept_trfs = TravelRequest.objects.filter(user__in=users_in_dept)

        total_trips = dept_trfs.count()
        total_spend = dept_trfs.aggregate(total=Sum('estimated_cost'))['total'] or Decimal('0.00')
        active_travelers = users_in_dept.filter(travel_requests__isnull=False).distinct().count()
        average_trip_cost = dept_trfs.aggregate(avg=Avg('estimated_cost'))['avg'] or Decimal('0.00')
        pending_approvals = dept_trfs.filter(status='PENDING').count()

        departments.append({
            'department_name': dept_name,
            'total_trips': total_trips,
            'total_spend': total_spend,
            'active_travelers': active_travelers,
            'average_trip_cost': average_trip_cost,
            'pending_approvals': pending_approvals
        })

    serializer = DepartmentAnalyticsSerializer(departments, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def user_activity_report(request):
    """
    Get user activity report (admin only)
    """
    users = User.objects.all()
    user_activities = []

    for user in users[:50]:  # Limit to 50 users for performance
        total_trfs = user.travel_requests.count()
        total_bookings = user.flight_bookings.count() + user.hotel_bookings.count()
        total_claims = user.expense_claims.count()
        total_spend = user.travel_requests.aggregate(total=Sum('estimated_cost'))['total'] or Decimal('0.00')

        # Last activity
        last_activity = max(
            user.travel_requests.aggregate(Max('created_at'))['created_at__max'] or timezone.now(),
            user.expense_claims.aggregate(Max('created_at'))['created_at__max'] or timezone.now()
        )

        if total_trfs > 0 or total_bookings > 0 or total_claims > 0:
            user_activities.append({
                'user_id': user.id,
                'user_name': user.get_full_name(),
                'email': user.email,
                'total_trfs': total_trfs,
                'total_bookings': total_bookings,
                'total_claims': total_claims,
                'total_spend': total_spend,
                'last_activity': last_activity
            })

    serializer = UserActivitySerializer(user_activities, many=True)
    return Response(serializer.data)
