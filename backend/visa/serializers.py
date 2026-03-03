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
    passport_file_url = serializers.SerializerMethodField()

    class Meta:
        model = VisaApplication
        fields = [
            'id', 'request_number', 'applicant_name', 'requestor_name', 'staff_id', 'department', 'destination', 'visa_type', 'request_type',
            'travel_purpose', 'passport_number', 'passport_file_url', 'status', 'trip_start_date', 'trip_end_date', 'submitted_date',
            'last_updated_date', 'processing_started_at', 'processing_completed_at', 'processing_details', 'additional_comments', 'created_at', 'updated_at'
        ]

    def get_passport_file_url(self, obj):
        """Return the full URL for the passport file if it exists"""
        if obj.passport_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.passport_file.url)
            return obj.passport_file.url
        return None


class VisaApplicationDetailSerializer(serializers.ModelSerializer):
    """Complete serializer for visa application details with nested relationships"""
    applicant_name = serializers.CharField(source='requestor_name')
    approval_workflow = VisaApprovalStepSerializer(source='visaapprovalstep_set', many=True, read_only=True)
    documents = VisaDocumentSerializer(source='visadocument_set', many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True, allow_null=True)
    passport_file = serializers.FileField(required=False, allow_null=True)
    passport_file_url = serializers.SerializerMethodField()
    selected_approvers = serializers.SerializerMethodField()

    class Meta:
        model = VisaApplication
        fields = [
            # Basic Info
            'id', 'request_number', 'user', 'user_email', 'applicant_name', 'requestor_name', 'staff_id',
            'department', 'position', 'email',

            # Section A: Personal Information
            'date_of_birth', 'place_of_birth', 'citizenship',
            'passport_number', 'passport_place_of_issuance', 'passport_date_of_issuance',
            'passport_expiry_date', 'passport_file', 'passport_file_url', 'contact_telephone', 'home_address',
            'education_details', 'current_employer_name', 'current_employer_address',
            'marital_status', 'family_information',

            # Section B: Type of Request
            'request_type', 'approximately_arrival_date', 'duration_of_stay',
            'visa_entry_type', 'work_visit_category', 'application_fees_borne_by',
            'cost_centre_number',

            # Travel Details
            'destination', 'travel_purpose', 'visa_type',
            'trip_start_date', 'trip_end_date', 'itinerary_details',

            # Status & Processing
            'status', 'submitted_date', 'last_updated_date',
            'processing_details', 'processing_started_at', 'processing_completed_at',

            # Additional
            'additional_comments', 'supporting_documents_notes', 'trf_reference_number',
            'created_at', 'updated_at',

            # Nested
            'approval_workflow', 'documents',

            # Approver selections
            'selected_approvers'
        ]
        read_only_fields = ['id', 'request_number', 'submitted_date', 'created_at', 'updated_at', 'last_updated_date', 'passport_file_url', 'selected_approvers']

    def get_selected_approvers(self, obj):
        """Get selected approvers from workflow instance additional_data"""
        from workflows.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType
        try:
            content_type = ContentType.objects.get_for_model(obj)
            workflow_instance = WorkflowInstance.objects.filter(
                content_type=content_type,
                object_id=obj.id
            ).order_by('-created_at').first()
            if workflow_instance and workflow_instance.additional_data:
                stored_approvers = workflow_instance.additional_data.get('selected_approvers', {})
                # Convert string keys to integers for frontend compatibility
                return {int(k): v for k, v in stored_approvers.items()}
        except Exception:
            pass
        return {}

    def get_passport_file_url(self, obj):
        """Return the full URL for the passport file if it exists"""
        if obj.passport_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.passport_file.url)
            return obj.passport_file.url
        return None

    def validate_passport_file(self, value):
        """Validate passport file type and size"""
        if value:
            # Check file size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB in bytes
            if value.size > max_size:
                raise serializers.ValidationError(
                    "Passport file size must not exceed 10MB."
                )

            # Check file type
            allowed_types = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']
            content_type = getattr(value, 'content_type', None)
            if content_type and content_type not in allowed_types:
                raise serializers.ValidationError(
                    "Passport file must be PDF, JPG, or PNG format."
                )

            # Also check by extension as fallback
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
            file_name = value.name.lower()
            if not any(file_name.endswith(ext) for ext in allowed_extensions):
                raise serializers.ValidationError(
                    "Passport file must be PDF, JPG, or PNG format."
                )

        return value


class VisaApplicationCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating visa applications"""
    passport_file = serializers.FileField(required=False, allow_null=True)
    passport_file_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = VisaApplication
        fields = [
            # Basic Info - user is set automatically in perform_create
            'requestor_name', 'staff_id', 'department', 'position', 'email',

            # Section A: Personal Information
            'date_of_birth', 'place_of_birth', 'citizenship',
            'passport_number', 'passport_place_of_issuance', 'passport_date_of_issuance',
            'passport_expiry_date', 'passport_file', 'passport_file_url', 'contact_telephone', 'home_address',
            'education_details', 'current_employer_name', 'current_employer_address',
            'marital_status', 'family_information',

            # Section B: Type of Request
            'request_type', 'approximately_arrival_date', 'duration_of_stay',
            'visa_entry_type', 'work_visit_category', 'application_fees_borne_by',
            'cost_centre_number',

            # Travel Details
            'destination', 'travel_purpose', 'visa_type',
            'trip_start_date', 'trip_end_date', 'itinerary_details',

            # Status & Processing
            'status', 'processing_started_at', 'processing_completed_at', 'processing_details',

            # Additional
            'additional_comments', 'supporting_documents_notes', 'trf_reference_number'
        ]

    def get_passport_file_url(self, obj):
        """Return the full URL for the passport file if it exists"""
        if obj.passport_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.passport_file.url)
            return obj.passport_file.url
        return None

    def validate_passport_file(self, value):
        """Validate passport file type and size"""
        if value:
            # Check file size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB in bytes
            if value.size > max_size:
                raise serializers.ValidationError(
                    "Passport file size must not exceed 10MB."
                )

            # Check file type
            allowed_types = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']
            content_type = getattr(value, 'content_type', None)
            if content_type and content_type not in allowed_types:
                raise serializers.ValidationError(
                    "Passport file must be PDF, JPG, or PNG format."
                )

            # Also check by extension as fallback
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
            file_name = value.name.lower()
            if not any(file_name.endswith(ext) for ext in allowed_extensions):
                raise serializers.ValidationError(
                    "Passport file must be PDF, JPG, or PNG format."
                )

        return value

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
