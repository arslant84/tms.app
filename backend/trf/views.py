from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from datetime import datetime

from .models import (
    TravelRequest,
    TrfAccommodationDetail,
    TrfAdvanceAmountRequestedItem,
    TrfAdvanceBankDetail,
    TrfApprovalStep,
    TrfCompanyTransportDetail,
    TrfDailyMealSelection,
    TrfFlightBooking,
    TrfItinerarySegment,
    TrfMealProvision,
    TrfPassportDetail
)
from .serializers import (
    TravelRequestSerializer,
    TravelRequestDetailSerializer,
    TravelRequestCreateSerializer,
    TravelRequestUpdateSerializer,
    ApprovalActionSerializer,
    TrfAccommodationDetailSerializer,
    TrfAdvanceAmountRequestedItemSerializer,
    TrfAdvanceBankDetailSerializer,
    TrfApprovalStepSerializer,
    TrfCompanyTransportDetailSerializer,
    TrfDailyMealSelectionSerializer,
    TrfFlightBookingSerializer,
    TrfItinerarySegmentSerializer,
    TrfMealProvisionSerializer,
    TrfPassportDetailSerializer
)


class TravelRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Travel Requests (TRF)

    Endpoints:
    - GET /api/trf/travel-requests/ - List all TRFs
    - POST /api/trf/travel-requests/ - Create a new TRF
    - GET /api/trf/travel-requests/{id}/ - Retrieve TRF details
    - PUT /api/trf/travel-requests/{id}/ - Update TRF
    - PATCH /api/trf/travel-requests/{id}/ - Partial update
    - DELETE /api/trf/travel-requests/{id}/ - Delete TRF
    - POST /api/trf/travel-requests/{id}/submit/ - Submit TRF for approval
    - POST /api/trf/travel-requests/{id}/approve/ - Approve TRF
    - POST /api/trf/travel-requests/{id}/reject/ - Reject TRF
    - POST /api/trf/travel-requests/{id}/cancel/ - Cancel TRF
    """
    queryset = TravelRequest.objects.all()
    serializer_class = TravelRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use appropriate serializer based on action"""
        if self.action == 'retrieve':
            return TravelRequestDetailSerializer
        elif self.action == 'create':
            return TravelRequestCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TravelRequestUpdateSerializer
        return TravelRequestSerializer

    def get_queryset(self):
        """Filter TRFs based on query parameters"""
        queryset = self.queryset

        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by travel type
        travel_type = self.request.query_params.get('travel_type', None)
        if travel_type:
            queryset = queryset.filter(travel_type=travel_type)

        # Filter by department
        department = self.request.query_params.get('department', None)
        if department:
            queryset = queryset.filter(department__icontains=department)

        # Filter by requestor name
        requestor_name = self.request.query_params.get('requestor_name', None)
        if requestor_name:
            queryset = queryset.filter(requestor_name__icontains=requestor_name)

        # Search across multiple fields
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(requestor_name__icontains=search) |
                Q(department__icontains=search) |
                Q(purpose__icontains=search) |
                Q(staff_id__icontains=search)
            )

        return queryset.order_by('-created_at')

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit a TRF for approval"""
        trf = self.get_object()

        if trf.status != 'Draft':
            return Response(
                {'error': 'Only draft TRFs can be submitted'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status to first approval stage
        trf.status = 'Pending Department Focal'
        trf.submitted_at = datetime.now()
        trf.save()

        # Create initial approval step
        TrfApprovalStep.objects.create(
            trf=trf,
            step_role='Department Focal',
            step_name='Department Focal Review',
            status='Pending'
        )

        serializer = self.get_serializer(trf)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a TRF at current approval step"""
        trf = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        step_role = serializer.validated_data['step_role']
        comments = serializer.validated_data.get('comments', '')

        # Find or create approval step for this role
        approval_step, created = TrfApprovalStep.objects.get_or_create(
            trf=trf,
            step_role=step_role,
            defaults={
                'step_name': f'{step_role} Approval',
                'status': 'Pending'
            }
        )

        # Update approval step
        approval_step.status = 'Approved'
        approval_step.comments = comments
        approval_step.step_date = datetime.now()
        approval_step.save()

        # Update TRF status based on approval workflow
        status_progression = {
            'Department Focal': 'Pending HOD',
            'HOD': 'Pending Travel Desk',
            'Travel Desk': 'Pending Finance',
            'Finance': 'Approved'
        }

        if step_role in status_progression:
            trf.status = status_progression[step_role]
            trf.save()

            # Create next approval step if not final
            if trf.status != 'Approved':
                next_role = trf.status.replace('Pending ', '')
                TrfApprovalStep.objects.get_or_create(
                    trf=trf,
                    step_role=next_role,
                    defaults={
                        'step_name': f'{next_role} Review',
                        'status': 'Pending'
                    }
                )

        trf_serializer = TravelRequestDetailSerializer(trf)
        return Response(trf_serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a TRF"""
        trf = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        step_role = serializer.validated_data['step_role']
        comments = serializer.validated_data.get('comments', '')

        # Find or create approval step for this role
        approval_step, created = TrfApprovalStep.objects.get_or_create(
            trf=trf,
            step_role=step_role,
            defaults={
                'step_name': f'{step_role} Approval',
                'status': 'Pending'
            }
        )

        # Update approval step
        approval_step.status = 'Rejected'
        approval_step.comments = comments
        approval_step.step_date = datetime.now()
        approval_step.save()

        # Update TRF status
        trf.status = 'Rejected'
        trf.save()

        trf_serializer = TravelRequestDetailSerializer(trf)
        return Response(trf_serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a TRF"""
        trf = self.get_object()

        if trf.status in ['Approved', 'Completed']:
            return Response(
                {'error': 'Approved or completed TRFs cannot be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        trf.status = 'Cancelled'
        trf.save()

        serializer = self.get_serializer(trf)
        return Response(serializer.data)


# =============== NESTED RESOURCE VIEWSETS ===============

class TrfAccommodationDetailViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Accommodation Details"""
    queryset = TrfAccommodationDetail.objects.all()
    serializer_class = TrfAccommodationDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by('-created_at')


class TrfAdvanceAmountRequestedItemViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Advance Amount Requested Items"""
    queryset = TrfAdvanceAmountRequestedItem.objects.all()
    serializer_class = TrfAdvanceAmountRequestedItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by('-created_at')


class TrfAdvanceBankDetailViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Advance Bank Details"""
    queryset = TrfAdvanceBankDetail.objects.all()
    serializer_class = TrfAdvanceBankDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by('-created_at')


class TrfApprovalStepViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Approval Steps"""
    queryset = TrfApprovalStep.objects.all()
    serializer_class = TrfApprovalStepSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by('-created_at')


class TrfCompanyTransportDetailViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Company Transport Details"""
    queryset = TrfCompanyTransportDetail.objects.all()
    serializer_class = TrfCompanyTransportDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by('-created_at')


class TrfDailyMealSelectionViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Daily Meal Selections"""
    queryset = TrfDailyMealSelection.objects.all()
    serializer_class = TrfDailyMealSelectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by('meal_date')


class TrfFlightBookingViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Flight Bookings"""
    queryset = TrfFlightBooking.objects.all()
    serializer_class = TrfFlightBookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by('departure_date', 'departure_time')


class TrfItinerarySegmentViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Itinerary Segments"""
    queryset = TrfItinerarySegment.objects.all()
    serializer_class = TrfItinerarySegmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by('segment_date')


class TrfMealProvisionViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Meal Provisions"""
    queryset = TrfMealProvision.objects.all()
    serializer_class = TrfMealProvisionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by('-created_at')


class TrfPassportDetailViewSet(viewsets.ModelViewSet):
    """ViewSet for TRF Passport Details"""
    queryset = TrfPassportDetail.objects.all()
    serializer_class = TrfPassportDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        trf_id = self.request.query_params.get('trf', None)
        if trf_id:
            return self.queryset.filter(trf_id=trf_id)
        return self.queryset.order_by('-created_at')
