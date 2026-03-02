"""
Utility modules for the TMS backend
"""

from .request_id_generator import (
    generate_request_id,
    parse_request_id,
    extract_context_from_itinerary,
    extract_context_from_country,
    extract_context_from_location,
)

from .api_response import (
    success_response,
    error_response,
    paginated_response,
    validation_error_response,
    created_response,
    no_content_response,
    unauthorized_response,
    forbidden_response,
    not_found_response,
    server_error_response,
    get_pagination_params,
    build_pagination_meta,
    StandardizedResponseMixin,
)

from .constants import (
    RequestStatus,
    WorkflowAction,
    WorkflowStatus,
    ApprovalStepStatus,
    LEGACY_STATUS_PROGRESSION,
    PENDING_STATUSES,
    DRAFT_STATUSES,
    FINAL_STATUSES,
    BOOKABLE_STATUSES,
)

from .viewset_mixins import (
    DualLookupMixin,
    WorkflowAwareQuerySetMixin,
    RequestorPopulationMixin,
)

from .validators import (
    # Date validators
    validate_date_range,
    validate_future_date,
    validate_past_date,
    FutureDateValidator,
    DateRangeValidator,
    # Status validators
    validate_status_transition,
    get_allowed_transitions,
    # File validators
    validate_file_extension,
    validate_file_size,
    FileExtensionValidator,
    FileSizeValidator,
    # String validators
    validate_not_blank,
    validate_min_length,
    # Numeric validators
    validate_positive,
    validate_range,
)

__all__ = [
    # Request ID utilities
    'generate_request_id',
    'parse_request_id',
    'extract_context_from_itinerary',
    'extract_context_from_country',
    'extract_context_from_location',
    # API Response utilities
    'success_response',
    'error_response',
    'paginated_response',
    'validation_error_response',
    'created_response',
    'no_content_response',
    'unauthorized_response',
    'forbidden_response',
    'not_found_response',
    'server_error_response',
    'get_pagination_params',
    'build_pagination_meta',
    'StandardizedResponseMixin',
    # Status Constants
    'RequestStatus',
    'WorkflowAction',
    'WorkflowStatus',
    'ApprovalStepStatus',
    'LEGACY_STATUS_PROGRESSION',
    'PENDING_STATUSES',
    'DRAFT_STATUSES',
    'FINAL_STATUSES',
    'BOOKABLE_STATUSES',
    # ViewSet Mixins
    'DualLookupMixin',
    'WorkflowAwareQuerySetMixin',
    'RequestorPopulationMixin',
    # Validators
    'validate_date_range',
    'validate_future_date',
    'validate_past_date',
    'FutureDateValidator',
    'DateRangeValidator',
    'validate_status_transition',
    'get_allowed_transitions',
    'validate_file_extension',
    'validate_file_size',
    'FileExtensionValidator',
    'FileSizeValidator',
    'validate_not_blank',
    'validate_min_length',
    'validate_positive',
    'validate_range',
]
