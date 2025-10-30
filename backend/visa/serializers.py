from rest_framework import serializers
from .models import VisaApplication, VisaApprovalStep, VisaDocument


class VisaDocumentSerializer(serializers.ModelSerializer):
    """Serializer for visa documents"""
    class Meta:
        model = VisaDocument
        fields = ['id', 'document_name', 'document_path', 'document_type', 'uploaded_at', 'uploaded_by']
        read_only_fields = ['id', 'uploaded_at']


class VisaApprovalStepSerializer(serializers.ModelSerializer):
    """Serializer for visa approval workflow steps"""
    class Meta:
        model = VisaApprovalStep
        fields = ['id', 'step_role', 'step_name', 'status', 'step_date', 'comments', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class VisaApplicationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing visa applications"""
    applicant_name = serializers.CharField(source='requestor_name', read_only=True)

    class Meta:
        model = VisaApplication
        fields = [
            'id', 'applicant_name', 'requestor_name', 'staff_id', 'destination', 'visa_type', 'request_type',
            'status', 'trip_start_date', 'trip_end_date', 'submitted_date',
            'last_updated_date'
        ]


class VisaApplicationDetailSerializer(serializers.ModelSerializer):
    """Complete serializer for visa application details with nested relationships"""
    applicant_name = serializers.CharField(source='requestor_name')
    approval_workflow = VisaApprovalStepSerializer(source='visaapprovalstep_set', many=True, read_only=True)
    documents = VisaDocumentSerializer(source='visadocument_set', many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True, allow_null=True)

    class Meta:
        model = VisaApplication
        fields = [
            # Basic Info
            'id', 'user', 'user_email', 'applicant_name', 'requestor_name', 'staff_id',
            'department', 'position', 'email',

            # Section A: Personal Information
            'date_of_birth', 'place_of_birth', 'citizenship',
            'passport_number', 'passport_place_of_issuance', 'passport_date_of_issuance',
            'passport_expiry_date', 'contact_telephone', 'home_address',
            'education_details', 'current_employer_name', 'current_employer_address',
            'marital_status', 'family_information',

            # Section B: Type of Request
            'request_type', 'approximately_arrival_date', 'duration_of_stay',
            'visa_entry_type', 'work_visit_category', 'application_fees_borne_by',
            'cost_centre_number',

            # Travel Details
            'destination', 'travel_purpose', 'visa_type',
            'trip_start_date', 'trip_end_date', 'itinerary_details',

            # Approvals
            'line_focal_person', 'line_focal_dept', 'line_focal_contact', 'line_focal_date',
            'sponsoring_dept_head', 'sponsoring_dept_head_dept', 'sponsoring_dept_head_contact',
            'sponsoring_dept_head_date', 'ceo_approval_name', 'ceo_approval_date',

            # Status & Processing
            'status', 'submitted_date', 'last_updated_date',
            'processing_details', 'processing_started_at', 'processing_completed_at',

            # Additional
            'additional_comments', 'supporting_documents_notes', 'trf_reference_number',
            'created_at', 'updated_at',

            # Nested
            'approval_workflow', 'documents'
        ]
        read_only_fields = ['id', 'submitted_date', 'created_at', 'updated_at', 'last_updated_date']


class VisaApplicationCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating visa applications"""

    class Meta:
        model = VisaApplication
        fields = [
            # Basic Info - user is set automatically in perform_create
            'requestor_name', 'staff_id', 'department', 'position', 'email',

            # Section A: Personal Information
            'date_of_birth', 'place_of_birth', 'citizenship',
            'passport_number', 'passport_place_of_issuance', 'passport_date_of_issuance',
            'passport_expiry_date', 'contact_telephone', 'home_address',
            'education_details', 'current_employer_name', 'current_employer_address',
            'marital_status', 'family_information',

            # Section B: Type of Request
            'request_type', 'approximately_arrival_date', 'duration_of_stay',
            'visa_entry_type', 'work_visit_category', 'application_fees_borne_by',
            'cost_centre_number',

            # Travel Details
            'destination', 'travel_purpose', 'visa_type',
            'trip_start_date', 'trip_end_date', 'itinerary_details',

            # Approvals (for admin/management use)
            'line_focal_person', 'line_focal_dept', 'line_focal_contact', 'line_focal_date',
            'sponsoring_dept_head', 'sponsoring_dept_head_dept', 'sponsoring_dept_head_contact',
            'sponsoring_dept_head_date', 'ceo_approval_name', 'ceo_approval_date',

            # Status
            'status',

            # Additional
            'additional_comments', 'supporting_documents_notes', 'trf_reference_number'
        ]

    def validate(self, data):
        """Validate visa application data"""
        from datetime import date

        # Check passport expiry
        if data.get('passport_expiry_date'):
            today = date.today()
            if data['passport_expiry_date'] < today:
                raise serializers.ValidationError({'passport_expiry_date': 'Passport has expired'})

        # Check trip dates
        if data.get('trip_start_date') and data.get('trip_end_date'):
            if data['trip_end_date'] < data['trip_start_date']:
                raise serializers.ValidationError({'trip_end_date': 'End date must be after start date'})

        return data
