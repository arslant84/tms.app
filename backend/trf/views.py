from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone
from datetime import datetime
from workflows.router import WorkflowRouter
from utils.request_id_generator import generate_request_id, extract_context_from_itinerary

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

    def create(self, request, *args, **kwargs):
        """Create a new TRF with logging"""
        print(f"\n=== TravelRequest CREATE ===")
        print(f"Request data: {request.data}")
        response = super().create(request, *args, **kwargs)
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.data}")
        print(f"Response data keys: {list(response.data.keys()) if hasattr(response.data, 'keys') else 'N/A'}")
        return response

    def perform_create(self, serializer):
        """Set creator and auto-populate requestor info, start workflow if submitted"""
        user = self.request.user

        # Auto-populate requestor information if not provided
        validated_data = serializer.validated_data
        if not validated_data.get('requestor_name'):
            validated_data['requestor_name'] = user.get_full_name() or user.email
        if not validated_data.get('staff_id'):
            validated_data['staff_id'] = getattr(user, 'employee_id', '') or getattr(user, 'staff_id', '')
        if not validated_data.get('department'):
            validated_data['department'] = getattr(user, 'department', '')
        if not validated_data.get('position'):
            validated_data['position'] = getattr(user, 'position', '') or getattr(user, 'job_title', '')

        # Get status from request data, default to 'Draft' if not provided
        status_value = validated_data.get('status', 'Draft')

        # Set submitted_at timestamp if status is being submitted (not Draft)
        extra_kwargs = {}
        if status_value not in ['Draft']:
            extra_kwargs['submitted_at'] = timezone.now()

        # Save the travel request
        trf = serializer.save(created_by=user, **extra_kwargs)

        # Start workflow if status is submitted (not Draft)
        if status_value not in ['Draft']:
            try:
                workflow_instance = WorkflowRouter.start_workflow_for_request(
                    entity=trf,
                    entity_type='travelrequest',
                    initiated_by=user
                )

                if workflow_instance:
                    # Reload the TRF to get the updated status from workflow
                    trf.refresh_from_db()
                    print(f"✅ Workflow started for TRF #{trf.id}: Workflow Instance #{workflow_instance.id}")
                    print(f"✅ Status updated to: {trf.status}")
                else:
                    print(f"⚠️ No active workflow configured for travelrequest - using legacy approval system")
            except Exception as e:
                print(f"❌ Error starting workflow for TRF #{trf.id}: {str(e)}")
                # Don't fail the request creation if workflow fails
                pass

    def get_queryset(self):
        """Filter TRFs based on query parameters"""
        queryset = self.queryset

        print(f"\n=== TravelRequest GET_QUERYSET ===")
        print(f"Total TRFs in database: {TravelRequest.objects.count()}")
        print(f"Query params: {dict(self.request.query_params)}")
        print(f"User: {self.request.user}")

        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            # Use startswith to match workflow statuses like "Pending Line Manager"
            # when filter is "Pending"
            queryset = queryset.filter(status__istartswith=status_filter)

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

        result = queryset.order_by('-created_at')
        print(f"Filtered queryset count: {result.count()}")
        print(f"=== END GET_QUERYSET ===\n")
        return result

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """
        Submit a TRF for approval
        Changes status from Draft to Pending and starts workflow
        """
        trf = self.get_object()

        if trf.status != 'Draft':
            return Response(
                {'error': 'Only draft TRFs can be submitted'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate request number if it doesn't exist
        if not trf.request_number:
            try:
                # Get itinerary segments to extract context
                itinerary_segments = list(trf.trfitinerarysegment_set.all().values(
                    'to_location', 'from_location', 'departure_time', 'arrival_time'
                ))

                print(f"🔍 Itinerary segments for TRF #{trf.id}: {itinerary_segments}")

                # Extract context from itinerary (first destination)
                context = extract_context_from_itinerary(itinerary_segments) if itinerary_segments else 'TRF'
                print(f"🔍 Extracted context: {context}")

                # Generate unique request number
                request_number = generate_request_id('TSR', context)
                trf.request_number = request_number
                print(f"✅ Generated request number: {request_number}")
            except Exception as e:
                print(f"❌ Error generating request number: {str(e)}")
                import traceback
                traceback.print_exc()
                # Fallback to simple format
                from datetime import datetime
                trf.request_number = f"TSR-{datetime.now().strftime('%Y%m%d-%H%M')}-TRF-{trf.id}"
                print(f"⚠️ Using fallback request number: {trf.request_number}")

        # Update status and submitted_at
        trf.status = 'Pending'
        trf.submitted_at = timezone.now()
        trf.save()

        # Start workflow using WorkflowRouter
        try:
            workflow_instance = WorkflowRouter.start_workflow_for_request(
                entity=trf,
                entity_type='travelrequest',
                initiated_by=request.user
            )

            if workflow_instance:
                # Reload the TRF to get the updated status from workflow
                trf.refresh_from_db()
                print(f"✅ Workflow started for TRF #{trf.id}: Workflow Instance #{workflow_instance.id}")
                print(f"✅ Status updated to: {trf.status}")
            else:
                # Fallback to legacy approval system if no workflow configured
                print(f"⚠️ No active workflow configured - creating legacy approval step")
                TrfApprovalStep.objects.create(
                    trf=trf,
                    step_role='Department Focal',
                    step_name='Department Focal Review',
                    status='Pending'
                )
                trf.status = 'Pending Department Focal'
                trf.save()
        except Exception as e:
            print(f"❌ Error starting workflow: {str(e)}")
            # Fallback to legacy system on error
            TrfApprovalStep.objects.create(
                trf=trf,
                step_role='Department Focal',
                step_name='Department Focal Review',
                status='Pending'
            )
            trf.status = 'Pending Department Focal'
            trf.save()

        # Ensure we have the latest status before serializing
        trf.refresh_from_db()
        serializer = TravelRequestDetailSerializer(trf)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a TRF at current approval step using WorkflowEngine"""
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType

        trf = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        step_role = serializer.validated_data['step_role']
        comments = serializer.validated_data.get('comments', '')

        try:
            # Get the workflow instance for this TRF
            content_type = ContentType.objects.get_for_model(trf)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=trf.id,
                status='in_progress'
            ).first()

            print(f"[DEBUG] Approving TRF #{trf.id}")
            print(f"[DEBUG] User: {request.user.email}, is_staff={request.user.is_staff}, is_superuser={request.user.is_superuser}")
            print(f"[DEBUG] Workflow instance found: {workflow_instance is not None}")

            if workflow_instance:
                # Find the current pending step (by order)
                # The WorkflowEngine will validate if the user is authorized
                current_step = workflow_instance.step_executions.filter(
                    status='pending'
                ).order_by('workflow_step__step_order').first()

                print(f"[DEBUG] Pending step found: {current_step is not None}")
                if current_step:
                    print(f"[DEBUG] Step: {current_step.workflow_step.step_name}, assigned_to: {current_step.assigned_to}")

                if current_step:
                    # Use workflow engine to process approval
                    result = WorkflowEngine.process_action(
                        step_execution_id=current_step.id,
                        action='approve',
                        actioned_by=request.user,
                        comments=comments
                    )

                    # Reload TRF to get updated status
                    trf.refresh_from_db()

                    # Also update legacy approval step for backward compatibility
                    approval_step, created = TrfApprovalStep.objects.get_or_create(
                        trf=trf,
                        step_role=step_role,
                        defaults={
                            'step_name': f'{step_role} Approval',
                            'status': 'Pending'
                        }
                    )
                    approval_step.status = 'Approved'
                    approval_step.comments = comments
                    approval_step.step_date = timezone.now()
                    approval_step.save()

                    trf_serializer = TravelRequestDetailSerializer(trf)
                    return Response(trf_serializer.data)
                else:
                    return Response(
                        {'error': 'No pending approval step found for this role'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Fallback to legacy manual approval if no workflow found
                print(f"⚠️ No workflow instance found for TRF #{trf.id}, using legacy approval")

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

        except ValueError as e:
            # ValueError is raised by WorkflowEngine for authorization failures
            print(f"❌ ValueError in approve workflow: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
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
        """Reject a TRF using WorkflowEngine"""
        from workflows.engine import WorkflowEngine
        from workflows.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType

        trf = self.get_object()
        serializer = ApprovalActionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        step_role = serializer.validated_data['step_role']
        comments = serializer.validated_data.get('comments', '')

        try:
            # Get the workflow instance for this TRF
            content_type = ContentType.objects.get_for_model(trf)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=trf.id,
                status='in_progress'
            ).first()

            if workflow_instance:
                # Find the current step execution for the given role
                current_step = workflow_instance.step_executions.filter(
                    status='pending'
                ).order_by('workflow_step__step_order').first()

                if current_step:
                    # Use workflow engine to process rejection
                    result = WorkflowEngine.process_action(
                        step_execution_id=current_step.id,
                        action='reject',
                        actioned_by=request.user,
                        comments=comments
                    )

                    # Reload TRF to get updated status
                    trf.refresh_from_db()

                    # Also update legacy approval step for backward compatibility
                    approval_step, created = TrfApprovalStep.objects.get_or_create(
                        trf=trf,
                        step_role=step_role,
                        defaults={
                            'step_name': f'{step_role} Approval',
                            'status': 'Pending'
                        }
                    )
                    approval_step.status = 'Rejected'
                    approval_step.comments = comments
                    approval_step.step_date = datetime.now()
                    approval_step.save()

                    trf_serializer = TravelRequestDetailSerializer(trf)
                    return Response(trf_serializer.data)
                else:
                    return Response(
                        {'error': 'No pending approval step found'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Fallback to legacy manual rejection if no workflow found
                print(f"⚠️ No workflow instance found for TRF #{trf.id}, using legacy rejection")

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

        except Exception as e:
            print(f"❌ Error in reject workflow: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Failed to process rejection: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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

    @action(detail=True, methods=['delete'], url_path='delete-itinerary')
    def delete_itinerary(self, request, pk=None):
        """Delete all itinerary segments for a TRF"""
        trf = self.get_object()
        count = TrfItinerarySegment.objects.filter(trf=trf).delete()[0]
        return Response({'deleted': count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='delete-meals')
    def delete_meals(self, request, pk=None):
        """Delete all meal selections for a TRF"""
        trf = self.get_object()
        count = TrfDailyMealSelection.objects.filter(trf=trf).delete()[0]
        return Response({'deleted': count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='delete-accommodation')
    def delete_accommodation(self, request, pk=None):
        """Delete all accommodation details for a TRF"""
        trf = self.get_object()
        count = TrfAccommodationDetail.objects.filter(trf=trf).delete()[0]
        return Response({'deleted': count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='delete-transport')
    def delete_transport(self, request, pk=None):
        """Delete all transport details for a TRF"""
        trf = self.get_object()
        count = TrfCompanyTransportDetail.objects.filter(trf=trf).delete()[0]
        return Response({'deleted': count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='delete-passport')
    def delete_passport(self, request, pk=None):
        """Delete all passport details for a TRF"""
        trf = self.get_object()
        count = TrfPassportDetail.objects.filter(trf=trf).delete()[0]
        return Response({'deleted': count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='delete-bank')
    def delete_bank(self, request, pk=None):
        """Delete bank details for a TRF"""
        trf = self.get_object()
        count = TrfAdvanceBankDetail.objects.filter(trf=trf).delete()[0]
        return Response({'deleted': count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='delete-advance-amounts')
    def delete_advance_amounts(self, request, pk=None):
        """Delete all advance amount items for a TRF"""
        trf = self.get_object()
        count = TrfAdvanceAmountRequestedItem.objects.filter(trf=trf).delete()[0]
        return Response({'deleted': count}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='pending-approvals')
    def pending_approvals(self, request):
        """Get TRFs pending approval for the current user"""
        user = request.user

        # Filter based on user role/permissions
        # For now, return all pending TRFs (can be refined based on user role)
        queryset = TravelRequest.objects.filter(
            status__in=[
                'Pending Department Focal',
                'Pending HOD',
                'Pending Travel Desk',
                'Pending Finance'
            ]
        ).order_by('-submitted_at')

        # Use detail serializer to include nested data (itinerary, accommodation, etc.)
        serializer = TravelRequestDetailSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='admin/book-flight')
    def book_flight(self, request, pk=None):
        """
        Book a flight for an approved TRF
        Creates a FlightBooking record and links it to the TRF

        Expected payload:
        {
            "pnr": "ABC123",
            "airline": "MH",
            "flightNumber": "MH123",
            "departureAirport": "KUL",
            "arrivalAirport": "LHR",
            "departureDateTime": "2025-12-01T10:00:00",
            "arrivalDateTime": "2025-12-01T18:00:00",
            "flightNotes": "Optional notes"
        }
        """
        from bookings.models import FlightBooking
        from datetime import datetime
        import traceback

        trf = self.get_object()

        print(f"\n=== BOOK FLIGHT DEBUG ===")
        print(f"TRF ID: {trf.id}")
        print(f"TRF Status: [{trf.status}]")
        print(f"TRF Travel Type: {trf.travel_type}")
        print(f"Request Data: {request.data}")
        print(f"========================\n")

        # Validate TRF status
        if trf.status != 'Approved':
            error_msg = f'Flights can only be booked for Approved TRFs. Current status: {trf.status}'
            print(f"❌ Status validation failed: {error_msg}")
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extract booking data from request
        pnr = request.data.get('pnr', '')
        airline = request.data.get('airline', '')
        flight_number = request.data.get('flightNumber', '')
        departure_airport = request.data.get('departureAirport', '')
        arrival_airport = request.data.get('arrivalAirport', '')
        departure_datetime_str = request.data.get('departureDateTime')
        arrival_datetime_str = request.data.get('arrivalDateTime')
        flight_notes = request.data.get('flightNotes', '')

        print(f"Extracted data:")
        print(f"  PNR: {pnr}")
        print(f"  Airline: {airline}")
        print(f"  Flight Number: {flight_number}")
        print(f"  Departure Airport: {departure_airport}")
        print(f"  Arrival Airport: {arrival_airport}")
        print(f"  Departure DateTime: {departure_datetime_str}")
        print(f"  Arrival DateTime: {arrival_datetime_str}")

        # Validate required fields
        if not all([pnr, airline, flight_number, departure_airport, arrival_airport]):
            missing = []
            if not pnr: missing.append('pnr')
            if not airline: missing.append('airline')
            if not flight_number: missing.append('flightNumber')
            if not departure_airport: missing.append('departureAirport')
            if not arrival_airport: missing.append('arrivalAirport')
            error_msg = f'Missing required fields: {", ".join(missing)}'
            print(f"❌ Field validation failed: {error_msg}")
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse datetime strings
        try:
            if departure_datetime_str:
                # Handle both with and without timezone
                departure_time = datetime.fromisoformat(departure_datetime_str.replace('Z', '+00:00'))
                if departure_time.tzinfo is None:
                    from django.utils import timezone as django_tz
                    departure_time = django_tz.make_aware(departure_time)
            else:
                departure_time = timezone.now()

            if arrival_datetime_str:
                arrival_time = datetime.fromisoformat(arrival_datetime_str.replace('Z', '+00:00'))
                if arrival_time.tzinfo is None:
                    from django.utils import timezone as django_tz
                    arrival_time = django_tz.make_aware(arrival_time)
            else:
                arrival_time = timezone.now()

            print(f"Parsed datetimes:")
            print(f"  Departure: {departure_time}")
            print(f"  Arrival: {arrival_time}")
        except (ValueError, TypeError) as e:
            error_msg = f'Invalid datetime format: {str(e)}'
            print(f"❌ DateTime parsing failed: {error_msg}")
            traceback.print_exc()
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create FlightBooking
        flight_booking = FlightBooking.objects.create(
            trf=trf,
            user=trf.created_by if trf.created_by else request.user,
            airline=airline,
            flight_number=flight_number,
            departure_airport=departure_airport,
            arrival_airport=arrival_airport,
            departure_time=departure_time,
            arrival_time=arrival_time,
            booking_reference=pnr,
            status='CONFIRMED',
            cost=0,  # Can be added later
            booked_by=request.user,
            booking_date=timezone.now(),
            confirmation_date=timezone.now(),
            notes=flight_notes
        )

        # Update TRF status to indicate flight is booked
        trf.status = 'Flight Booked'
        trf.save()

        # Return updated TRF data
        serializer = TravelRequestDetailSerializer(trf)
        return Response({
            'trf': serializer.data,
            'flight_booking': {
                'id': flight_booking.id,
                'booking_reference': flight_booking.booking_reference,
                'status': flight_booking.status
            }
        }, status=status.HTTP_201_CREATED)


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

    def create(self, request, *args, **kwargs):
        print(f"\n=== TrfDailyMealSelection CREATE ===")
        print(f"Request data: {request.data}")
        print(f"TRF field value: {request.data.get('trf')}")
        print(f"Meal date value: {request.data.get('meal_date')}")
        return super().create(request, *args, **kwargs)

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

    def create(self, request, *args, **kwargs):
        print(f"\n=== TrfItinerarySegment CREATE ===")
        print(f"Request data: {request.data}")
        print(f"TRF field value: {request.data.get('trf')}")
        return super().create(request, *args, **kwargs)

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
