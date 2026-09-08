"""
TransportApprovalStepViewSet and VehicleAssignmentViewSet - small,
self-contained viewsets split out of transport/views.py (see
docs/CODEBASE_REFACTOR_ROADMAP.md item 7) alongside the dominant
TransportRequestViewSet. Pure file move, no logic changed.
"""

from accounts.utils import is_module_admin
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import TransportApprovalStep, VehicleAssignment
from .serializers import TransportApprovalStepSerializer, VehicleAssignmentSerializer


class TransportApprovalStepViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for transport approval steps
    """

    queryset = TransportApprovalStep.objects.all()
    serializer_class = TransportApprovalStepSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter approval steps by transport request if specified"""
        queryset = super().get_queryset()
        transport_request_id = self.request.query_params.get("transport_request", None)

        if transport_request_id:
            queryset = queryset.filter(transport_request_id=transport_request_id)

        return queryset.select_related("transport_request")


class VehicleAssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing vehicle assignments (admin only)
    """

    queryset = VehicleAssignment.objects.all()
    serializer_class = VehicleAssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by transport request and status"""
        queryset = super().get_queryset()

        transport_request_id = self.request.query_params.get("transport_request", None)
        if transport_request_id:
            queryset = queryset.filter(transport_request_id=transport_request_id)

        assignment_status = self.request.query_params.get("status", None)
        if assignment_status:
            queryset = queryset.filter(status=assignment_status)

        vehicle_number = self.request.query_params.get("vehicle_number", None)
        if vehicle_number:
            queryset = queryset.filter(vehicle_number__icontains=vehicle_number)

        return queryset.select_related("transport_request", "assigned_by")

    def perform_create(self, serializer):
        """
        Create vehicle assignment
        Only transport admin can assign vehicles
        """
        user = self.request.user
        if not user.is_superuser and not is_module_admin(user, "transport"):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only transport admin can assign vehicles")

        serializer.save(assigned_by=user)

    @action(detail=True, methods=["post"])
    def start_journey(self, request, pk=None):
        """
        Mark vehicle assignment as In Progress and record starting odometer
        """
        assignment = self.get_object()

        if assignment.status != "Assigned":
            return Response(
                {
                    "error": f"Cannot start journey for assignment with status {assignment.status}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        odometer_start = request.data.get("odometer_start")
        if not odometer_start:
            return Response(
                {"error": "Starting odometer reading is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment.status = "In Progress"
        assignment.odometer_start = odometer_start
        assignment.save()

        serializer = self.get_serializer(assignment)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def complete_journey(self, request, pk=None):
        """
        Mark vehicle assignment as Completed and record ending odometer and fuel used
        """
        assignment = self.get_object()

        if assignment.status != "In Progress":
            return Response(
                {
                    "error": f"Cannot complete journey for assignment with status {assignment.status}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        odometer_end = request.data.get("odometer_end")
        fuel_used = request.data.get("fuel_used_liters")

        if not odometer_end:
            return Response(
                {"error": "Ending odometer reading is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if odometer_end < assignment.odometer_start:
            return Response(
                {"error": "Ending odometer cannot be less than starting odometer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment.status = "Completed"
        assignment.odometer_end = odometer_end
        assignment.fuel_used_liters = fuel_used
        assignment.completion_date = timezone.now()
        assignment.save()

        serializer = self.get_serializer(assignment)
        return Response(serializer.data)
