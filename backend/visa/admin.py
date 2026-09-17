from django.contrib import admin

from .models import VisaApplication, VisaApprovalStep, VisaDocument


@admin.register(VisaApplication)
class VisaApplicationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "request_number",
        "requestor_name",
        "department",
        "destination",
        "visa_type",
        "status",
        "submitted_date",
        "created_at",
    ]
    search_fields = [
        "request_number",
        "requestor_name",
        "staff_id",
        "department",
        "destination",
        "passport_number",
        "email",
    ]
    list_filter = ["status", "visa_type", "department", "created_at"]
    ordering = ["-created_at"]
    readonly_fields = [
        "submitted_date",
        "last_updated_date",
        "created_at",
        "updated_at",
    ]


@admin.register(VisaApprovalStep)
class VisaApprovalStepAdmin(admin.ModelAdmin):
    list_display = ["id", "visa", "step_role", "step_name", "status", "step_date"]
    search_fields = ["step_role", "step_name", "comments"]
    list_filter = ["status", "step_role", "step_date"]
    ordering = ["-created_at"]


@admin.register(VisaDocument)
class VisaDocumentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "visa",
        "document_name",
        "document_type",
        "uploaded_by",
        "uploaded_at",
    ]
    search_fields = ["document_name", "document_type", "uploaded_by"]
    list_filter = ["document_type", "uploaded_at"]
    ordering = ["-uploaded_at"]
