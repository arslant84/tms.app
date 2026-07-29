"""
Utility modules for the TMS backend
"""

from .api_response import (
    StandardizedResponseMixin,
    build_pagination_meta,
    created_response,
    error_response,
    forbidden_response,
    get_pagination_params,
    no_content_response,
    not_found_response,
    paginated_response,
    server_error_response,
    success_response,
    unauthorized_response,
    validation_error_response,
)
from .constants import (
    BOOKABLE_STATUSES,
    DRAFT_STATUSES,
    FINAL_STATUSES,
    PENDING_STATUSES,
    ApprovalStepStatus,
    RequestStatus,
    WorkflowAction,
    WorkflowStatus,
)
from .request_id_generator import (
    extract_context_from_country,
    extract_context_from_itinerary,
    extract_context_from_location,
    generate_request_id,
    parse_request_id,
)
from .validators import (  # Date validators; Status validators; File validators; String validators; Numeric validators
    DateRangeValidator,
    FileExtensionValidator,
    FileSizeValidator,
    FutureDateValidator,
    get_allowed_transitions,
    validate_date_range,
    validate_file_extension,
    validate_file_size,
    validate_future_date,
    validate_min_length,
    validate_not_blank,
    validate_past_date,
    validate_positive,
    validate_range,
    validate_status_transition,
)
from .viewset_mixins import (
    DualLookupMixin,
    RequestorPopulationMixin,
    WorkflowAwareQuerySetMixin,
)

__all__ = [
    # Request ID utilities
    "generate_request_id",
    "parse_request_id",
    "extract_context_from_itinerary",
    "extract_context_from_country",
    "extract_context_from_location",
    # API Response utilities
    "success_response",
    "error_response",
    "paginated_response",
    "validation_error_response",
    "created_response",
    "no_content_response",
    "unauthorized_response",
    "forbidden_response",
    "not_found_response",
    "server_error_response",
    "get_pagination_params",
    "build_pagination_meta",
    "StandardizedResponseMixin",
    # Status Constants
    "RequestStatus",
    "WorkflowAction",
    "WorkflowStatus",
    "ApprovalStepStatus",
    "PENDING_STATUSES",
    "DRAFT_STATUSES",
    "FINAL_STATUSES",
    "BOOKABLE_STATUSES",
    # ViewSet Mixins
    "DualLookupMixin",
    "WorkflowAwareQuerySetMixin",
    "RequestorPopulationMixin",
    # Validators
    "validate_date_range",
    "validate_future_date",
    "validate_past_date",
    "FutureDateValidator",
    "DateRangeValidator",
    "validate_status_transition",
    "get_allowed_transitions",
    "validate_file_extension",
    "validate_file_size",
    "FileExtensionValidator",
    "FileSizeValidator",
    "validate_not_blank",
    "validate_min_length",
    "validate_positive",
    "validate_range",
]
