"""
TRF nested sub-resource ViewSets - split out of trf/views.py (see
docs/CODEBASE_REFACTOR_ROADMAP.md item 9) alongside the dominant
TravelRequestViewSet. Pure file move, no logic changed.
"""

import logging

from accounts.utils import can_view_all
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from utils import error_response, not_found_response, success_response

from .models import (
    TravelRequest,
    TrfAdvanceAmountRequestedItem,
    TrfAdvanceBankDetail,
    TrfApprovalStep,
    TrfDailyMealSelection,
    TrfItinerarySegment,
    TrfMealProvision,
    TrfPassportDetail,
)
from .serializers import (
    TrfAdvanceAmountRequestedItemSerializer,
    TrfAdvanceBankDetailSerializer,
    TrfApprovalStepSerializer,
    TrfDailyMealSelectionSerializer,
    TrfItinerarySegmentSerializer,
    TrfMealProvisionSerializer,
    TrfPassportDetailSerializer,
)

logger = logging.getLogger(__name__)


class TrfChildOwnershipMixin:
    """
    Shared ownership/permission gating for TRF nested sub-resource
    ViewSets (itinerary segments, meal selections/provisions, bank
    details, advance amounts, passport details, approval steps).

    Previously each of these ViewSets filtered only by `?trf=<id>` (or
    returned everything with no `trf` param) - no ownership or permission
    check tied access back to the parent TravelRequest, so any
    authenticated user could read/modify/delete another user's TRF
    sub-records just by knowing/guessing the parent TRF's id. See docs/
    RBAC_AND_ADMIN_ACCESS_FIX_ROADMAP.md Fix 8.

    Mirrors the exact same rule TravelRequestViewSet.get_queryset()
    established rather than inventing a fifth variant:
    - Read actions (list/retrieve): admin (superuser/view_all_trf), the
      TRF's owner, or an approver with a pending step on it (matches Fix
      1's retrieve/export_pdf bypass).
    - Write actions (update/partial_update/destroy, plus each ViewSet's
      own detail actions like upload_passport/delete_passport_file):
      admin or the TRF's owner ONLY - deliberately not extended to
      pending-approval reviewers, same reasoning as Fix 2/3 (reviewing a
      TRF isn't the same as being allowed to modify its sub-records).
    - Create: get_queryset() is never consulted for CREATE by DRF's
      CreateModelMixin, so perform_create() below re-checks the same
      owner-or-admin rule against the `trf` the new row is being attached
      to - without this, the get_queryset() fix alone would still let
      anyone POST a fake sub-resource row into someone else's TRF.

    Confirmed via a frontend audit (2026-09-07) that every one of these
    endpoints is only ever called by trf.service.ts as part of the TRF
    owner's own wizard flow - no admin/approver-facing page calls any of
    them directly (trf-detail.component.ts reads this data embedded in the
    parent TRF's own serializer, not via these endpoints), so there's no
    known legitimate "editing on behalf of another user" pattern that an
    owner-or-admin-only write rule would break.
    """

    # Default ordering when no ViewSet-specific value is set. Override per
    # ViewSet to match its pre-existing final .order_by(...) argument.
    trf_ordering = "-created_at"

    # Extra ViewSet-specific action names (beyond the DRF defaults) that
    # modify an existing row and should therefore use the write (owner-or-
    # admin-only) rule rather than the read (plus-pending-approval) rule.
    extra_write_actions = ()

    def _owner_or_admin_trf_ids(self, user):
        """None means "unrestricted" (admin) - sentinel, not an empty set."""
        if user.is_superuser or can_view_all(user, "trf"):
            return None
        return TravelRequest.objects.filter(created_by=user).values_list(
            "id", flat=True
        )

    def _readable_trf_ids(self, user):
        """None means "unrestricted" (admin) - sentinel, not an empty set."""
        from workflows.services import WorkflowApprovalHelper

        if user.is_superuser or can_view_all(user, "trf"):
            return None
        pending_approval_ids = WorkflowApprovalHelper.get_pending_entity_ids_for_user(
            user, TravelRequest
        )
        return TravelRequest.objects.filter(
            Q(created_by=user) | Q(id__in=pending_approval_ids)
        ).values_list("id", flat=True)

    def get_queryset(self):
        user = self.request.user
        write_actions = ("update", "partial_update", "destroy") + tuple(
            self.extra_write_actions
        )

        if self.action in write_actions:
            visible_trf_ids = self._owner_or_admin_trf_ids(user)
        else:
            visible_trf_ids = self._readable_trf_ids(user)

        queryset = self.queryset
        if visible_trf_ids is not None:
            queryset = queryset.filter(trf_id__in=visible_trf_ids)

        trf_id_param = self.request.query_params.get("trf", None)
        if trf_id_param:
            queryset = queryset.filter(trf_id=trf_id_param)

        return queryset.order_by(self.trf_ordering)

    def perform_create(self, serializer):
        user = self.request.user
        trf = serializer.validated_data.get("trf")
        if trf is not None and not (
            user.is_superuser
            or can_view_all(user, "trf")
            or trf.created_by_id == user.id
        ):
            raise PermissionDenied(
                "You do not have permission to add records to this travel request."
            )
        serializer.save()


class TrfAdvanceAmountRequestedItemViewSet(
    TrfChildOwnershipMixin, viewsets.ModelViewSet
):
    """ViewSet for TRF Advance Amount Requested Items"""

    queryset = TrfAdvanceAmountRequestedItem.objects.all()
    serializer_class = TrfAdvanceAmountRequestedItemSerializer
    permission_classes = [IsAuthenticated]
    trf_ordering = "-created_at"


class TrfAdvanceBankDetailViewSet(TrfChildOwnershipMixin, viewsets.ModelViewSet):
    """ViewSet for TRF Advance Bank Details"""

    queryset = TrfAdvanceBankDetail.objects.all()
    serializer_class = TrfAdvanceBankDetailSerializer
    permission_classes = [IsAuthenticated]
    trf_ordering = "-created_at"


class TrfApprovalStepViewSet(TrfChildOwnershipMixin, viewsets.ModelViewSet):
    """ViewSet for TRF Approval Steps"""

    queryset = TrfApprovalStep.objects.all()
    serializer_class = TrfApprovalStepSerializer
    permission_classes = [IsAuthenticated]
    trf_ordering = "-created_at"


class TrfDailyMealSelectionViewSet(TrfChildOwnershipMixin, viewsets.ModelViewSet):
    """ViewSet for TRF Daily Meal Selections"""

    queryset = TrfDailyMealSelection.objects.all()
    serializer_class = TrfDailyMealSelectionSerializer
    permission_classes = [IsAuthenticated]
    trf_ordering = "meal_date"

    def create(self, request, *args, **kwargs):
        logger.debug("\n=== TrfDailyMealSelection CREATE ===")
        logger.debug(f"Request data: {request.data}")
        logger.debug(f"TRF field value: {request.data.get('trf')}")
        logger.debug(f"Meal date value: {request.data.get('meal_date')}")
        return super().create(request, *args, **kwargs)


class TrfItinerarySegmentViewSet(TrfChildOwnershipMixin, viewsets.ModelViewSet):
    """ViewSet for TRF Itinerary Segments"""

    queryset = TrfItinerarySegment.objects.all()
    serializer_class = TrfItinerarySegmentSerializer
    permission_classes = [IsAuthenticated]
    trf_ordering = "segment_date"

    def create(self, request, *args, **kwargs):
        logger.debug("\n=== TrfItinerarySegment CREATE ===")
        logger.debug(f"Request data: {request.data}")
        logger.debug(f"TRF field value: {request.data.get('trf')}")
        return super().create(request, *args, **kwargs)


class TrfMealProvisionViewSet(TrfChildOwnershipMixin, viewsets.ModelViewSet):
    """ViewSet for TRF Meal Provisions"""

    queryset = TrfMealProvision.objects.all()
    serializer_class = TrfMealProvisionSerializer
    permission_classes = [IsAuthenticated]
    trf_ordering = "-created_at"


class TrfPassportDetailViewSet(TrfChildOwnershipMixin, viewsets.ModelViewSet):
    """ViewSet for TRF Passport Details with file upload support"""

    queryset = TrfPassportDetail.objects.all()
    serializer_class = TrfPassportDetailSerializer
    permission_classes = [IsAuthenticated]
    trf_ordering = "-created_at"
    # upload_passport/delete_passport_file modify an existing row (file
    # attach/remove) - same write (owner-or-admin-only) rule as update/
    # destroy, not the read-plus-pending-approval rule.
    extra_write_actions = ("upload_passport", "delete_passport_file")

    def get_serializer_context(self):
        """Include request in serializer context for building absolute URLs"""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @action(detail=True, methods=["post"], url_path="upload-passport")
    def upload_passport(self, request, pk=None):
        """
        Upload or update passport file for an existing passport detail record.
        Accepts multipart/form-data with 'passport_file' field.
        """
        passport_detail = self.get_object()

        if "passport_file" not in request.FILES:
            return error_response(
                message="No passport file provided",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        passport_file = request.FILES["passport_file"]

        # Validate file type
        allowed_types = ["application/pdf", "image/jpeg", "image/jpg", "image/png"]
        if passport_file.content_type not in allowed_types:
            return error_response(
                message="Passport file must be PDF, JPG, or PNG format",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024
        if passport_file.size > max_size:
            return error_response(
                message="Passport file size must not exceed 10MB",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Delete old file if exists
        if passport_detail.passport_file:
            passport_detail.passport_file.delete(save=False)

        # Save new file
        passport_detail.passport_file = passport_file
        passport_detail.save()

        serializer = self.get_serializer(passport_detail)
        return success_response(
            data=serializer.data,
            message="Passport file uploaded successfully",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"], url_path="delete-passport-file")
    def delete_passport_file(self, request, pk=None):
        """Delete the passport file from an existing passport detail record."""
        passport_detail = self.get_object()

        if not passport_detail.passport_file:
            return error_response(
                message="No passport file to delete",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Delete the file
        passport_detail.passport_file.delete(save=True)

        serializer = self.get_serializer(passport_detail)
        return success_response(
            data=serializer.data,
            message="Passport file deleted successfully",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="upload-for-trf")
    def upload_for_trf(self, request):
        """
        Upload passport file for a TRF. Creates passport detail if it doesn't exist.
        Expects: trf (TRF ID) and passport_file in multipart/form-data
        """
        trf_id = request.data.get("trf")
        if not trf_id:
            return error_response(
                message="TRF ID is required", status_code=status.HTTP_400_BAD_REQUEST
            )

        if "passport_file" not in request.FILES:
            return error_response(
                message="No passport file provided",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        passport_file = request.FILES["passport_file"]

        # Validate file type
        allowed_types = ["application/pdf", "image/jpeg", "image/jpg", "image/png"]
        if passport_file.content_type not in allowed_types:
            return error_response(
                message="Passport file must be PDF, JPG, or PNG format",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024
        if passport_file.size > max_size:
            return error_response(
                message="Passport file size must not exceed 10MB",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Verify TRF exists
        try:
            trf = TravelRequest.objects.get(pk=trf_id)
        except TravelRequest.DoesNotExist:
            return not_found_response(message="TRF not found")

        # This action takes a raw trf id from request.data rather than a pk
        # in the URL, so it never goes through get_object()/get_queryset()
        # at all - unguarded until now, same bug as the other write actions
        # this mixin fixes (see docs/RBAC_AND_ADMIN_ACCESS_FIX_ROADMAP.md
        # Fix 8). Same owner-or-admin rule as perform_create.
        user = request.user
        if not (
            user.is_superuser
            or can_view_all(user, "trf")
            or trf.created_by_id == user.id
        ):
            return error_response(
                message="You do not have permission to upload a passport file for this travel request.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # Get or create passport detail for this TRF
        passport_detail, created = TrfPassportDetail.objects.get_or_create(
            trf=trf, defaults={}
        )

        # Delete old file if exists
        if passport_detail.passport_file:
            passport_detail.passport_file.delete(save=False)

        # Save new file
        passport_detail.passport_file = passport_file
        passport_detail.save()

        serializer = self.get_serializer(passport_detail)
        return success_response(
            data=serializer.data,
            message="Passport file uploaded successfully",
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
