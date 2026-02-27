from django.contrib import admin
from .models import (
    TravelRequest,
    TrfAdvanceAmountRequestedItem,
    TrfAdvanceBankDetail,
    TrfApprovalStep,
    TrfDailyMealSelection,
    TrfFlightBooking,
    TrfItinerarySegment,
    TrfMealProvision,
    TrfPassportDetail
)


@admin.register(TravelRequest)
class TravelRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'requestor_name', 'department', 'travel_type', 'status', 'estimated_cost', 'submitted_at', 'created_at']
    search_fields = ['requestor_name', 'staff_id', 'department', 'purpose', 'email']
    list_filter = ['status', 'travel_type', 'department', 'created_at']
    ordering = ['-created_at']
    readonly_fields = ['submitted_at', 'created_at', 'updated_at']


@admin.register(TrfAdvanceAmountRequestedItem)
class TrfAdvanceAmountRequestedItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'trf', 'date_from', 'date_to', 'lh', 'ma', 'oa', 'tr', 'oe', 'usd']
    list_filter = ['date_from', 'date_to']
    ordering = ['-created_at']


@admin.register(TrfAdvanceBankDetail)
class TrfAdvanceBankDetailAdmin(admin.ModelAdmin):
    list_display = ['id', 'trf', 'bank_name', 'account_number', 'currency', 'amount']
    search_fields = ['bank_name', 'account_number', 'account_name']
    list_filter = ['currency']
    ordering = ['-created_at']


@admin.register(TrfApprovalStep)
class TrfApprovalStepAdmin(admin.ModelAdmin):
    list_display = ['id', 'trf', 'step_role', 'step_name', 'status', 'step_date']
    search_fields = ['step_role', 'step_name', 'comments']
    list_filter = ['status', 'step_role', 'step_date']
    ordering = ['-created_at']


@admin.register(TrfDailyMealSelection)
class TrfDailyMealSelectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'trf', 'meal_date', 'breakfast', 'lunch', 'dinner', 'supper', 'refreshment']
    list_filter = ['meal_date', 'breakfast', 'lunch', 'dinner']
    ordering = ['meal_date']


@admin.register(TrfFlightBooking)
class TrfFlightBookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'trf', 'flight_number', 'airline', 'departure_location', 'arrival_location', 'departure_date', 'status']
    search_fields = ['flight_number', 'airline', 'booking_reference', 'departure_location', 'arrival_location']
    list_filter = ['status', 'departure_date', 'flight_class']
    ordering = ['departure_date', 'departure_time']


@admin.register(TrfItinerarySegment)
class TrfItinerarySegmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'trf', 'segment_date', 'from_location', 'to_location', 'flight_number']
    search_fields = ['from_location', 'to_location', 'flight_number', 'purpose']
    list_filter = ['segment_date', 'flight_class']
    ordering = ['segment_date']


@admin.register(TrfMealProvision)
class TrfMealProvisionAdmin(admin.ModelAdmin):
    list_display = ['id', 'trf', 'date_from_to', 'breakfast', 'lunch', 'dinner', 'supper', 'refreshment']
    search_fields = ['date_from_to', 'remarks']
    ordering = ['-created_at']


@admin.register(TrfPassportDetail)
class TrfPassportDetailAdmin(admin.ModelAdmin):
    list_display = ['id', 'trf', 'full_name', 'passport_number', 'nationality', 'passport_expiry_date']
    search_fields = ['full_name', 'passport_number', 'nationality']
    list_filter = ['nationality', 'passport_expiry_date']
    ordering = ['-created_at']
