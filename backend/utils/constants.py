"""
Status Constants for TMS Application

Centralized status definitions to avoid hardcoded strings across viewsets.
Use these constants instead of raw strings for status comparisons.

Usage:
    from utils.constants import RequestStatus, PENDING_STATUSES

    if trf.status not in [RequestStatus.DRAFT]:
        # Start workflow

    if status_value in PENDING_STATUSES:
        # Handle pending requests
"""


class RequestStatus:
    """
    Standard request statuses used across all entity types
    (TRF, Transport, Visa, Accommodation)
    """

    # Initial States
    DRAFT = "Draft"

    # Pending States (Workflow)
    PENDING = "Pending"
    PENDING_DEPARTMENT_FOCAL = "Pending Department Focal"
    PENDING_LINE_MANAGER = "Pending Line Manager"
    PENDING_HOD = "Pending HOD"
    PENDING_TRAVEL_DESK = "Pending Travel Desk"
    PENDING_FINANCE = "Pending Finance"
    PENDING_VISA_CLERK = "Pending Visa Clerk"
    PENDING_TRANSPORT_ADMIN = "Pending Transport Admin"
    SUBMITTED = "Submitted"
    UNDER_REVIEW = "Under Review"

    # Processing States
    PROCESSING = "Processing"
    PROCESSING_TRAVEL_DESK = "Processing with Travel Desk"
    PROCESSING_VISA_CLERK = "Processing with Visa Clerk"
    PROCESSING_TRANSPORT_ADMIN = "Processing with Transport Admin"
    READY_FOR_BOOKING = "Ready for Booking"
    FLIGHT_BOOKED = "Flight Booked"

    # Final States
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"
    COMPLETED = "Completed"

    @classmethod
    def draft_statuses(cls) -> list:
        """Statuses considered as draft/unsubmitted"""
        return [cls.DRAFT]

    @classmethod
    def pending_statuses(cls) -> list:
        """Statuses that indicate request is pending approval"""
        return [
            cls.PENDING,
            cls.PENDING_DEPARTMENT_FOCAL,
            cls.PENDING_LINE_MANAGER,
            cls.PENDING_HOD,
            cls.PENDING_TRAVEL_DESK,
            cls.PENDING_FINANCE,
            cls.PENDING_VISA_CLERK,
            cls.PENDING_TRANSPORT_ADMIN,
            cls.SUBMITTED,
            cls.UNDER_REVIEW,
        ]

    @classmethod
    def processing_statuses(cls) -> list:
        """Statuses that indicate request is being processed"""
        return [
            cls.PROCESSING,
            cls.PROCESSING_TRAVEL_DESK,
            cls.PROCESSING_VISA_CLERK,
            cls.PROCESSING_TRANSPORT_ADMIN,
            cls.READY_FOR_BOOKING,
            cls.FLIGHT_BOOKED,
        ]

    @classmethod
    def bookable_statuses(cls) -> list:
        """Statuses that allow booking operations"""
        return [
            cls.APPROVED,
            cls.FLIGHT_BOOKED,
            cls.PROCESSING,
            cls.READY_FOR_BOOKING,
        ]

    @classmethod
    def final_statuses(cls) -> list:
        """Statuses that indicate request is finalized"""
        return [cls.APPROVED, cls.REJECTED, cls.CANCELLED, cls.COMPLETED]

    @classmethod
    def cancellable_statuses(cls) -> list:
        """Statuses from which a request can be cancelled"""
        # All except completed and already cancelled
        return (
            cls.draft_statuses()
            + cls.pending_statuses()
            + cls.processing_statuses()
            + [cls.APPROVED]
        )

    @classmethod
    def non_draft_submitted_statuses(cls) -> list:
        """Statuses that trigger workflow initiation"""
        return cls.pending_statuses()


class WorkflowAction:
    """Actions that can be performed on workflow steps"""

    APPROVE = "approve"
    REJECT = "reject"
    DELEGATE = "delegate"
    REQUEST_INFO = "request_info"


class WorkflowStatus:
    """Workflow instance statuses"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class ApprovalStepStatus:
    """Approval step statuses"""

    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    SKIPPED = "Skipped"


# Shortcut lists for common checks
PENDING_STATUSES = RequestStatus.pending_statuses()
DRAFT_STATUSES = RequestStatus.draft_statuses()
FINAL_STATUSES = RequestStatus.final_statuses()
BOOKABLE_STATUSES = RequestStatus.bookable_statuses()

# =============================================================================
# Password Configuration
# =============================================================================
PASSWORD_MIN_LENGTH = 15
