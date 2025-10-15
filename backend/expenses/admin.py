from django.contrib import admin
from .models import ExpenseClaim, ExpenseItem, ClaimsApprovalStep


@admin.register(ExpenseClaim)
class ExpenseClaimAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'user', 'category', 'total_amount', 'currency', 'status', 'expense_date', 'created_at']
    search_fields = ['title', 'description', 'user__email']
    list_filter = ['status', 'category', 'currency', 'created_at']
    ordering = ['-created_at']
    readonly_fields = ['user_id', 'trf_id', 'created_at', 'updated_at']
    filter_horizontal = ['items']


@admin.register(ExpenseItem)
class ExpenseItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'description', 'amount', 'category', 'date']
    search_fields = ['description']
    list_filter = ['category', 'date']
    ordering = ['-date']


@admin.register(ClaimsApprovalStep)
class ClaimsApprovalStepAdmin(admin.ModelAdmin):
    list_display = ['id', 'claim', 'step_role', 'step_name', 'status', 'step_date', 'created_at']
    search_fields = ['step_role', 'step_name', 'comments']
    list_filter = ['status', 'step_role', 'step_date']
    ordering = ['-created_at']
