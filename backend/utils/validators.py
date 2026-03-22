"""
Custom Validators for TMS Application

Provides reusable validation functions and classes for common validation scenarios.
These validators can be used in serializers, models, and views.

Usage:
    from utils.validators import (
        validate_date_range,
        validate_future_date,
        validate_status_transition,
        validate_file_extension,
        validate_file_size,
        DateRangeValidator,
        FutureDateValidator,
    )

    # In a serializer
    class TravelRequestSerializer(serializers.ModelSerializer):
        departure_date = serializers.DateField(validators=[FutureDateValidator()])

        def validate(self, attrs):
            validate_date_range(attrs['departure_date'], attrs['return_date'])
            return attrs

    # In a view
    if not validate_status_transition(instance.status, new_status, ALLOWED_TRANSITIONS):
        raise ValidationError("Invalid status transition")
"""

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Set, Any
import os


# =============================================================================
# Date Validators
# =============================================================================

def validate_date_range(
    start_date: date,
    end_date: date,
    field_names: tuple = ('start_date', 'end_date'),
    allow_same_day: bool = True
) -> None:
    """
    Validate that end_date is after (or equal to) start_date.

    Args:
        start_date: The start date
        end_date: The end date
        field_names: Tuple of (start_field_name, end_field_name) for error messages
        allow_same_day: If True, start_date == end_date is valid

    Raises:
        ValidationError: If end_date is before start_date

    Example:
        validate_date_range(departure_date, return_date)
        validate_date_range(check_in, check_out, ('check_in', 'check_out'), allow_same_day=False)
    """
    if start_date is None or end_date is None:
        return

    if allow_same_day:
        if end_date < start_date:
            raise ValidationError({
                field_names[1]: f"{field_names[1].replace('_', ' ').title()} must be on or after {field_names[0].replace('_', ' ')}."
            })
    else:
        if end_date <= start_date:
            raise ValidationError({
                field_names[1]: f"{field_names[1].replace('_', ' ').title()} must be after {field_names[0].replace('_', ' ')}."
            })


def validate_future_date(
    date_value: date,
    field_name: str = 'date',
    allow_today: bool = True,
    min_days_ahead: int = 0
) -> None:
    """
    Validate that a date is in the future.

    Args:
        date_value: The date to validate
        field_name: Field name for error messages
        allow_today: If True, today's date is valid
        min_days_ahead: Minimum number of days in the future

    Raises:
        ValidationError: If date is not in the future

    Example:
        validate_future_date(departure_date, 'departure_date')
        validate_future_date(booking_date, 'booking_date', min_days_ahead=3)
    """
    if date_value is None:
        return

    today = timezone.now().date()
    min_date = today + timedelta(days=min_days_ahead)

    if allow_today and min_days_ahead == 0:
        if date_value < today:
            raise ValidationError({
                field_name: f"{field_name.replace('_', ' ').title()} cannot be in the past."
            })
    else:
        if date_value < min_date:
            if min_days_ahead > 0:
                raise ValidationError({
                    field_name: f"{field_name.replace('_', ' ').title()} must be at least {min_days_ahead} day(s) in the future."
                })
            else:
                raise ValidationError({
                    field_name: f"{field_name.replace('_', ' ').title()} must be in the future."
                })


def validate_past_date(
    date_value: date,
    field_name: str = 'date',
    allow_today: bool = True
) -> None:
    """
    Validate that a date is in the past.

    Args:
        date_value: The date to validate
        field_name: Field name for error messages
        allow_today: If True, today's date is valid

    Raises:
        ValidationError: If date is not in the past

    Example:
        validate_past_date(birth_date, 'birth_date')
    """
    if date_value is None:
        return

    today = timezone.now().date()

    if allow_today:
        if date_value > today:
            raise ValidationError({
                field_name: f"{field_name.replace('_', ' ').title()} cannot be in the future."
            })
    else:
        if date_value >= today:
            raise ValidationError({
                field_name: f"{field_name.replace('_', ' ').title()} must be in the past."
            })


@deconstructible
class FutureDateValidator:
    """
    Django validator class for future date validation.
    Can be used directly in model fields or serializer fields.

    Usage:
        departure_date = models.DateField(validators=[FutureDateValidator()])
        departure_date = models.DateField(validators=[FutureDateValidator(min_days_ahead=7)])
    """

    def __init__(self, allow_today: bool = True, min_days_ahead: int = 0):
        self.allow_today = allow_today
        self.min_days_ahead = min_days_ahead

    def __call__(self, value):
        validate_future_date(
            value,
            field_name='this field',
            allow_today=self.allow_today,
            min_days_ahead=self.min_days_ahead
        )

    def __eq__(self, other):
        return (
            isinstance(other, FutureDateValidator) and
            self.allow_today == other.allow_today and
            self.min_days_ahead == other.min_days_ahead
        )


@deconstructible
class DateRangeValidator:
    """
    Django validator class for date range validation.
    Use in serializer's validate() method.

    Usage:
        def validate(self, attrs):
            DateRangeValidator('departure_date', 'return_date')(attrs)
            return attrs
    """

    def __init__(
        self,
        start_field: str,
        end_field: str,
        allow_same_day: bool = True
    ):
        self.start_field = start_field
        self.end_field = end_field
        self.allow_same_day = allow_same_day

    def __call__(self, attrs: dict):
        start_date = attrs.get(self.start_field)
        end_date = attrs.get(self.end_field)

        if start_date and end_date:
            validate_date_range(
                start_date,
                end_date,
                (self.start_field, self.end_field),
                self.allow_same_day
            )


# =============================================================================
# Status/Workflow Validators
# =============================================================================

def validate_status_transition(
    current_status: str,
    new_status: str,
    allowed_transitions: Dict[str, List[str]],
    field_name: str = 'status'
) -> bool:
    """
    Validate that a status transition is allowed.

    Args:
        current_status: The current status value
        new_status: The proposed new status
        allowed_transitions: Dict mapping current status to list of allowed new statuses
        field_name: Field name for error messages

    Returns:
        True if transition is valid

    Raises:
        ValidationError: If transition is not allowed

    Example:
        ALLOWED_TRANSITIONS = {
            'Draft': ['Pending', 'Cancelled'],
            'Pending': ['Approved', 'Rejected', 'Cancelled'],
            'Approved': ['Processing', 'Completed'],
        }

        validate_status_transition(instance.status, 'Approved', ALLOWED_TRANSITIONS)
    """
    # Same status is always allowed (no change)
    if current_status == new_status:
        return True

    # Check if current status has defined transitions
    if current_status not in allowed_transitions:
        raise ValidationError({
            field_name: f"Cannot transition from '{current_status}' status."
        })

    # Check if new status is in allowed transitions
    allowed = allowed_transitions.get(current_status, [])
    if new_status not in allowed:
        raise ValidationError({
            field_name: f"Cannot transition from '{current_status}' to '{new_status}'. "
                       f"Allowed transitions: {', '.join(allowed) if allowed else 'none'}."
        })

    return True


def get_allowed_transitions(
    current_status: str,
    allowed_transitions: Dict[str, List[str]]
) -> List[str]:
    """
    Get list of allowed status transitions from current status.

    Args:
        current_status: The current status value
        allowed_transitions: Dict mapping current status to list of allowed new statuses

    Returns:
        List of allowed status values to transition to

    Example:
        allowed = get_allowed_transitions('Draft', ALLOWED_TRANSITIONS)
        # Returns: ['Pending', 'Cancelled']
    """
    return allowed_transitions.get(current_status, [])


# =============================================================================
# File Validators
# =============================================================================

def validate_file_extension(
    filename: str,
    allowed_extensions: List[str],
    field_name: str = 'file'
) -> None:
    """
    Validate that a file has an allowed extension.

    Args:
        filename: The filename to validate
        allowed_extensions: List of allowed extensions (without dots)
        field_name: Field name for error messages

    Raises:
        ValidationError: If extension is not allowed

    Example:
        validate_file_extension('document.pdf', ['pdf', 'doc', 'docx'])
    """
    if not filename:
        return

    ext = os.path.splitext(filename)[1].lower().lstrip('.')

    if ext not in [e.lower() for e in allowed_extensions]:
        raise ValidationError({
            field_name: f"File type '.{ext}' is not allowed. "
                       f"Allowed types: {', '.join(allowed_extensions)}."
        })


def validate_file_size(
    file_size: int,
    max_size_bytes: int,
    field_name: str = 'file'
) -> None:
    """
    Validate that a file size is within the allowed limit.

    Args:
        file_size: The file size in bytes
        max_size_bytes: Maximum allowed size in bytes
        field_name: Field name for error messages

    Raises:
        ValidationError: If file is too large

    Example:
        validate_file_size(file.size, 10 * 1024 * 1024)  # 10MB
    """
    if file_size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        actual_mb = file_size / (1024 * 1024)
        raise ValidationError({
            field_name: f"File size ({actual_mb:.2f} MB) exceeds maximum allowed size ({max_mb:.2f} MB)."
        })


@deconstructible
class FileExtensionValidator:
    """
    Django validator class for file extension validation.

    Usage:
        document = models.FileField(validators=[FileExtensionValidator(['pdf', 'doc', 'docx'])])
    """

    def __init__(self, allowed_extensions: List[str]):
        self.allowed_extensions = [e.lower() for e in allowed_extensions]

    def __call__(self, value):
        if hasattr(value, 'name'):
            validate_file_extension(value.name, self.allowed_extensions)

    def __eq__(self, other):
        return (
            isinstance(other, FileExtensionValidator) and
            self.allowed_extensions == other.allowed_extensions
        )


@deconstructible
class FileSizeValidator:
    """
    Django validator class for file size validation.

    Usage:
        document = models.FileField(validators=[FileSizeValidator(max_mb=10)])
    """

    def __init__(self, max_mb: float = 10):
        self.max_size_bytes = int(max_mb * 1024 * 1024)

    def __call__(self, value):
        if hasattr(value, 'size'):
            validate_file_size(value.size, self.max_size_bytes)

    def __eq__(self, other):
        return (
            isinstance(other, FileSizeValidator) and
            self.max_size_bytes == other.max_size_bytes
        )


# =============================================================================
# String Validators
# =============================================================================

def validate_not_blank(
    value: str,
    field_name: str = 'field'
) -> None:
    """
    Validate that a string is not blank (empty or whitespace only).

    Args:
        value: The string to validate
        field_name: Field name for error messages

    Raises:
        ValidationError: If string is blank

    Example:
        validate_not_blank(request.data.get('name'), 'name')
    """
    if value is not None and not value.strip():
        raise ValidationError({
            field_name: f"{field_name.replace('_', ' ').title()} cannot be blank."
        })


def validate_min_length(
    value: str,
    min_length: int,
    field_name: str = 'field'
) -> None:
    """
    Validate that a string has a minimum length.

    Args:
        value: The string to validate
        min_length: Minimum required length
        field_name: Field name for error messages

    Raises:
        ValidationError: If string is too short

    Example:
        from utils.constants import PASSWORD_MIN_LENGTH
        validate_min_length(password, PASSWORD_MIN_LENGTH, 'password')
    """
    if value is not None and len(value) < min_length:
        raise ValidationError({
            field_name: f"{field_name.replace('_', ' ').title()} must be at least {min_length} characters."
        })


# =============================================================================
# Numeric Validators
# =============================================================================

def validate_positive(
    value: Any,
    field_name: str = 'field',
    allow_zero: bool = False
) -> None:
    """
    Validate that a number is positive.

    Args:
        value: The number to validate
        field_name: Field name for error messages
        allow_zero: If True, zero is valid

    Raises:
        ValidationError: If number is not positive

    Example:
        validate_positive(quantity, 'quantity')
        validate_positive(amount, 'amount', allow_zero=True)
    """
    if value is None:
        return

    if allow_zero:
        if value < 0:
            raise ValidationError({
                field_name: f"{field_name.replace('_', ' ').title()} cannot be negative."
            })
    else:
        if value <= 0:
            raise ValidationError({
                field_name: f"{field_name.replace('_', ' ').title()} must be greater than zero."
            })


def validate_range(
    value: Any,
    min_value: Any,
    max_value: Any,
    field_name: str = 'field'
) -> None:
    """
    Validate that a number is within a range.

    Args:
        value: The number to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        field_name: Field name for error messages

    Raises:
        ValidationError: If number is outside the range

    Example:
        validate_range(age, 18, 120, 'age')
        validate_range(rating, 1, 5, 'rating')
    """
    if value is None:
        return

    if value < min_value or value > max_value:
        raise ValidationError({
            field_name: f"{field_name.replace('_', ' ').title()} must be between {min_value} and {max_value}."
        })
