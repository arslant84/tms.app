from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    AccommodationStaffHouse,
    AccommodationRoom,
    AccommodationRequest,
    AccommodationBooking
)
from .serializers import (
    AccommodationStaffHouseSerializer,
    AccommodationRoomSerializer,
    AccommodationRequestSerializer,
    AccommodationBookingSerializer,
    AccommodationBookingDetailSerializer,
    RoomAvailabilitySerializer
)
from workflows.router import WorkflowRouter
from utils.request_id_generator import generate_request_id


class AccommodationStaffHouseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Staff Houses

    Endpoints:
    - GET /api/accommodation/staff-houses/ - List all staff houses
    - POST /api/accommodation/staff-houses/ - Create a new staff house
    - GET /api/accommodation/staff-houses/{id}/ - Retrieve staff house details
    - PUT /api/accommodation/staff-houses/{id}/ - Update staff house
    - PATCH /api/accommodation/staff-houses/{id}/ - Partial update
    - DELETE /api/accommodation/staff-houses/{id}/ - Delete staff house
    """
    queryset = AccommodationStaffHouse.objects.all()
    serializer_class = AccommodationStaffHouseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter staff houses by location if provided"""
        queryset = self.queryset
        location = self.request.query_params.get('location', None)
        search = self.request.query_params.get('search', None)

        if location:
            queryset = queryset.filter(location__icontains=location)

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(location__icontains=search) |
                Q(description__icontains=search)
            )

        return queryset.order_by('-created_at')

    @action(detail=True, methods=['get'])
    def rooms(self, request, pk=None):
        """Get all rooms for a specific staff house"""
        staff_house = self.get_object()
        rooms = AccommodationRoom.objects.filter(staff_house=staff_house)
        serializer = AccommodationRoomSerializer(rooms, many=True)
        return Response(serializer.data)


class AccommodationRoomViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Rooms

    Endpoints:
    - GET /api/accommodation/rooms/ - List all rooms
    - POST /api/accommodation/rooms/ - Create a new room
    - GET /api/accommodation/rooms/{id}/ - Retrieve room details
    - PUT /api/accommodation/rooms/{id}/ - Update room
    - PATCH /api/accommodation/rooms/{id}/ - Partial update
    - DELETE /api/accommodation/rooms/{id}/ - Delete room
    - GET /api/accommodation/rooms/available/ - List available rooms
    """
    queryset = AccommodationRoom.objects.all()
    serializer_class = AccommodationRoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter rooms by staff_house, status, or availability"""
        queryset = self.queryset.select_related('staff_house')

        staff_house = self.request.query_params.get('staff_house', None)
        status = self.request.query_params.get('status', None)
        room_type = self.request.query_params.get('room_type', None)

        if staff_house:
            queryset = queryset.filter(staff_house_id=staff_house)

        if status:
            queryset = queryset.filter(status=status)

        if room_type:
            queryset = queryset.filter(room_type__icontains=room_type)

        return queryset.order_by('staff_house', 'name')

    @action(detail=False, methods=['get'])
    def available(self, request):
        """List all available rooms"""
        available_rooms = self.queryset.filter(status='Available')
        serializer = self.get_serializer(available_rooms, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def bookings(self, request, pk=None):
        """Get all bookings for a specific room"""
        room = self.get_object()
        date_from = request.query_params.get('date_from', None)
        date_to = request.query_params.get('date_to', None)

        bookings = AccommodationBooking.objects.filter(room=room)

        if date_from:
            bookings = bookings.filter(date__gte=date_from)
        if date_to:
            bookings = bookings.filter(date__lte=date_to)

        serializer = AccommodationBookingSerializer(bookings, many=True)
        return Response(serializer.data)


class AccommodationRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Accommodation Requests

    Endpoints:
    - GET /api/accommodation/requests/ - List all requests
    - POST /api/accommodation/requests/ - Create a new request
    - GET /api/accommodation/requests/{id}/ - Retrieve request details
    - PUT /api/accommodation/requests/{id}/ - Update request
    - PATCH /api/accommodation/requests/{id}/ - Partial update
    - DELETE /api/accommodation/requests/{id}/ - Delete request
    - POST /api/accommodation/requests/{id}/submit/ - Submit request
    - POST /api/accommodation/requests/{id}/approve/ - Approve request
    - POST /api/accommodation/requests/{id}/reject/ - Reject request
    """
    queryset = AccommodationRequest.objects.all()
    serializer_class = AccommodationRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter requests by status, department, etc."""
        queryset = self.queryset

        status_filter = self.request.query_params.get('status', None)
        department = self.request.query_params.get('department', None)
        requestor_name = self.request.query_params.get('requestor_name', None)

        if status_filter:
            # Use startswith to match workflow statuses like "Pending Line Manager"
            # when filter is "Pending"
            queryset = queryset.filter(status__istartswith=status_filter)

        if department:
            queryset = queryset.filter(department__icontains=department)

        if requestor_name:
            queryset = queryset.filter(requestor_name__icontains=requestor_name)

        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        """Create accommodation request and optionally start workflow if submitted"""
        # Get status from request data, default to 'Draft' if not provided
        status_value = serializer.validated_data.get('status', 'Draft')

        # Set submitted_at timestamp if status is being submitted (not Draft)
        extra_kwargs = {}
        if status_value in ['Pending', 'Submitted']:
            extra_kwargs['submitted_at'] = timezone.now()

        # Save the accommodation request
        accommodation_request = serializer.save(**extra_kwargs)

        # Start workflow if status is submitted (not Draft)
        if status_value in ['Pending', 'Submitted']:
            try:
                workflow_instance = WorkflowRouter.start_workflow_for_request(
                    entity=accommodation_request,
                    entity_type='accommodation',
                    initiated_by=self.request.user
                )

                if workflow_instance:
                    # Reload the accommodation request to get the updated status from workflow
                    accommodation_request.refresh_from_db()
                    print(f"✅ Workflow started for Accommodation Request #{accommodation_request.id}: Workflow Instance #{workflow_instance.id}")
                    print(f"✅ Status updated to: {accommodation_request.status}")
                else:
                    print(f"⚠️ No active workflow configured for accommodation - using legacy approval system")
            except Exception as e:
                print(f"❌ Error starting workflow for Accommodation Request #{accommodation_request.id}: {str(e)}")
                # Don't fail the request creation if workflow fails
                pass

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """
        Submit an accommodation request for approval
        Changes status from Draft to Pending and starts workflow
        """
        accommodation_request = self.get_object()

        # Validate status
        if accommodation_request.status != 'Draft':
            return Response(
                {'error': f'Cannot submit accommodation request with status {accommodation_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate request number if it doesn't exist
        if not accommodation_request.request_number:
            try:
                # Extract context from additional_data location or use generic context
                context = 'ACCOM'
                if accommodation_request.additional_data and isinstance(accommodation_request.additional_data, dict):
                    location = accommodation_request.additional_data.get('location', '')
                    if location:
                        context = location  # Let generate_request_id handle validation and length

                print(f"🔍 Extracted context for Accommodation Request #{accommodation_request.id}: {context}")

                # Generate unique request number (will auto-validate and limit context to 5 chars)
                request_number = generate_request_id('ACCOM', context)
                accommodation_request.request_number = request_number
                print(f"✅ Generated request number: {request_number}")
            except Exception as e:
                print(f"❌ Error generating request number: {str(e)}")
                import traceback
                traceback.print_exc()
                # Fallback to simple format
                accommodation_request.request_number = f"ACCOM-{datetime.now().strftime('%Y%m%d-%H%M')}-ACCOM-{accommodation_request.id}"
                print(f"⚠️ Using fallback request number: {accommodation_request.request_number}")

        # Update status and submitted_at
        accommodation_request.status = 'Pending'
        accommodation_request.submitted_at = timezone.now()
        accommodation_request.save()

        # Start workflow using WorkflowRouter
        try:
            workflow_instance = WorkflowRouter.start_workflow_for_request(
                entity=accommodation_request,
                entity_type='accommodation',
                initiated_by=request.user
            )

            if workflow_instance:
                # Reload the accommodation request to get the updated status from workflow
                accommodation_request.refresh_from_db()
                print(f"✅ Workflow started for Accommodation Request #{accommodation_request.id}: Workflow Instance #{workflow_instance.id}")
                print(f"✅ Status updated to: {accommodation_request.status}")
            else:
                # Fallback to legacy approval system if no workflow configured
                print(f"⚠️ No active workflow configured - keeping status as Pending")
        except Exception as e:
            print(f"❌ Error starting workflow: {str(e)}")
            # Fallback to legacy system on error - status remains 'Pending'
            pass

        # Ensure we have the latest status before serializing
        accommodation_request.refresh_from_db()
        serializer = self.get_serializer(accommodation_request)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve an accommodation request using WorkflowEngine"""
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType

        accommodation_request = self.get_object()
        comments = request.data.get('comments', '')

        try:
            # Get the workflow instance for this accommodation request
            content_type = ContentType.objects.get_for_model(accommodation_request)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=accommodation_request.id,
                status='in_progress'
            ).first()

            if workflow_instance:
                # Find the current pending step
                current_step = workflow_instance.step_executions.filter(
                    status='pending'
                ).order_by('workflow_step__step_order').first()

                if current_step:
                    # Use workflow engine to process approval
                    result = WorkflowEngine.process_action(
                        step_execution_id=current_step.id,
                        action='approve',
                        actioned_by=request.user,
                        comments=comments
                    )

                    # Reload to get updated status
                    accommodation_request.refresh_from_db()

                    serializer = self.get_serializer(accommodation_request)
                    return Response(serializer.data)
                else:
                    return Response(
                        {'error': 'No pending approval step found'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Fallback to legacy approval logic
                print(f"⚠️ No workflow instance found for Accommodation #{accommodation_request.id}, using legacy approval")

                if accommodation_request.status not in ['Pending', 'Pending Department Focal', 'Pending HOD']:
                    return Response(
                        {'error': 'Cannot approve request with current status'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                accommodation_request.status = 'Approved'
                accommodation_request.save()

                serializer = self.get_serializer(accommodation_request)
                return Response(serializer.data)

        except Exception as e:
            print(f"❌ Error in approve workflow: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Failed to process approval: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject an accommodation request using WorkflowEngine"""
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType

        accommodation_request = self.get_object()
        comments = request.data.get('comments', '')

        try:
            content_type = ContentType.objects.get_for_model(accommodation_request)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=accommodation_request.id,
                status='in_progress'
            ).first()

            if workflow_instance:
                current_step = workflow_instance.step_executions.filter(
                    status='pending'
                ).order_by('workflow_step__step_order').first()

                if current_step:
                    result = WorkflowEngine.process_action(
                        step_execution_id=current_step.id,
                        action='reject',
                        actioned_by=request.user,
                        comments=comments
                    )

                    accommodation_request.refresh_from_db()

                    serializer = self.get_serializer(accommodation_request)
                    return Response(serializer.data)
            else:
                # Fallback to legacy rejection
                if accommodation_request.status not in ['Pending', 'Pending Department Focal', 'Pending HOD']:
                    return Response(
                        {'error': 'Cannot reject request with current status'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                accommodation_request.status = 'Rejected'
                accommodation_request.save()

                serializer = self.get_serializer(accommodation_request)
                return Response(serializer.data)

        except Exception as e:
            print(f"❌ Error in reject workflow: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Failed to process rejection: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='pending-approvals')
    def pending_approvals(self, request):
        """Get accommodation requests pending approval"""
        queryset = AccommodationRequest.objects.filter(
            status='Pending'
        ).order_by('-submitted_at')

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class AccommodationBookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Accommodation Bookings

    Endpoints:
    - GET /api/accommodation/bookings/ - List all bookings
    - POST /api/accommodation/bookings/ - Create a new booking
    - GET /api/accommodation/bookings/{id}/ - Retrieve booking details
    - PUT /api/accommodation/bookings/{id}/ - Update booking
    - PATCH /api/accommodation/bookings/{id}/ - Partial update
    - DELETE /api/accommodation/bookings/{id}/ - Delete booking
    - POST /api/accommodation/bookings/check-availability/ - Check room availability
    - POST /api/accommodation/bookings/{id}/cancel/ - Cancel booking
    """
    queryset = AccommodationBooking.objects.all()
    serializer_class = AccommodationBookingSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use detailed serializer for retrieve action"""
        if self.action == 'retrieve':
            return AccommodationBookingDetailSerializer
        return AccommodationBookingSerializer

    def get_queryset(self):
        """Filter bookings by various parameters"""
        queryset = self.queryset.select_related(
            'staff_house', 'room', 'staff', 'trf'
        )

        staff_house = self.request.query_params.get('staff_house', None)
        room = self.request.query_params.get('room', None)
        staff = self.request.query_params.get('staff', None)
        status = self.request.query_params.get('status', None)
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)

        if staff_house:
            queryset = queryset.filter(staff_house_id=staff_house)

        if room:
            queryset = queryset.filter(room_id=room)

        if staff:
            queryset = queryset.filter(staff_id=staff)

        if status:
            queryset = queryset.filter(status=status)

        if date_from:
            queryset = queryset.filter(date__gte=date_from)

        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        return queryset.order_by('-date', '-created_at')

    @action(detail=False, methods=['post'])
    def check_availability(self, request):
        """
        Check room availability for a given date range

        Expected payload:
        {
            "staff_house": 1,
            "start_date": "2025-10-15",
            "end_date": "2025-10-20"
        }
        """
        serializer = RoomAvailabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        staff_house_id = serializer.validated_data['staff_house']
        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']

        # Get all rooms in the staff house
        rooms = AccommodationRoom.objects.filter(
            staff_house_id=staff_house_id
        )

        # Get bookings for the date range
        bookings = AccommodationBooking.objects.filter(
            staff_house_id=staff_house_id,
            date__gte=start_date,
            date__lte=end_date,
            status__in=['Confirmed', 'Pending']
        )

        # Build availability response
        availability = []
        for room in rooms:
            room_bookings = bookings.filter(room=room)
            booked_dates = [booking.date.strftime('%Y-%m-%d') for booking in room_bookings]

            availability.append({
                'room_id': room.id,
                'room_name': room.name,
                'room_type': room.room_type,
                'capacity': room.capacity,
                'status': room.status,
                'booked_dates': booked_dates,
                'is_fully_booked': len(booked_dates) == (end_date - start_date).days + 1
            })

        return Response({
            'staff_house_id': staff_house_id,
            'start_date': start_date,
            'end_date': end_date,
            'rooms': availability
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking"""
        booking = self.get_object()

        if booking.status == 'Cancelled':
            return Response(
                {'error': 'Booking is already cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        booking.status = 'Cancelled'
        booking.save()

        serializer = self.get_serializer(booking)
        return Response(serializer.data)
