"""
Standardized API Response Utility

Provides consistent response formatting across all API endpoints:
- Success/error status
- Human-readable messages
- Structured data payload
- Metadata (timestamp, request_id, pagination)
- Validation errors

Usage:
    from utils.api_response import success_response, error_response, paginated_response

    # Success response
    return success_response(
        data=serializer.data,
        message="User created successfully",
        status_code=status.HTTP_201_CREATED
    )

    # Error response
    return error_response(
        message="Invalid credentials",
        errors={"email": ["This field is required"]},
        status_code=status.HTTP_400_BAD_REQUEST
    )

    # Paginated response
    return paginated_response(
        data=serializer.data,
        request=request,
        total_count=100,
        message="Users retrieved successfully"
    )
"""

from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.core.paginator import Paginator, Page
from typing import Any, Dict, List, Optional, Union
import uuid


def generate_request_id() -> str:
    """Generate a unique request ID for tracking"""
    return str(uuid.uuid4())


def get_pagination_params(request) -> tuple:
    """
    Extract pagination parameters from request

    Returns:
        tuple: (page, limit) - page number and items per page
    """
    try:
        page = int(request.query_params.get('page', 1))
        page = max(1, page)  # Ensure page is at least 1
    except (ValueError, TypeError):
        page = 1

    try:
        limit = int(request.query_params.get('limit', 20))
        limit = min(max(1, limit), 100)  # Clamp between 1 and 100
    except (ValueError, TypeError):
        limit = 20

    return page, limit


def build_pagination_meta(page: int, limit: int, total_count: int) -> Dict[str, Any]:
    """
    Build pagination metadata

    Args:
        page: Current page number (1-indexed)
        limit: Items per page
        total_count: Total number of items

    Returns:
        dict: Pagination metadata
    """
    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    return {
        'page': page,
        'limit': limit,
        'total_count': total_count,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_previous': page > 1
    }


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = status.HTTP_200_OK,
    meta: Optional[Dict[str, Any]] = None
) -> Response:
    """
    Create a standardized success response

    Args:
        data: Response payload (serializer data, list, dict, etc.)
        message: Human-readable success message
        status_code: HTTP status code (default: 200)
        meta: Additional metadata (pagination, etc.)

    Returns:
        Response: DRF Response object with standardized format

    Example:
        return success_response(
            data={'id': 1, 'name': 'John'},
            message="User retrieved successfully",
            status_code=status.HTTP_200_OK
        )
    """
    response_data = {
        'success': True,
        'message': message,
        'data': data,
        'meta': {
            'timestamp': timezone.now().isoformat(),
            'request_id': generate_request_id(),
            **(meta or {})
        }
    }

    return Response(response_data, status=status_code)


def error_response(
    message: str = "An error occurred",
    errors: Optional[Union[Dict, List, str]] = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    data: Any = None
) -> Response:
    """
    Create a standardized error response

    Args:
        message: Human-readable error message
        errors: Detailed error information (validation errors, etc.)
        status_code: HTTP status code (default: 400)
        data: Optional additional data

    Returns:
        Response: DRF Response object with standardized error format

    Example:
        return error_response(
            message="Validation failed",
            errors={"email": ["This field is required"]},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    """
    response_data = {
        'success': False,
        'message': message,
        'data': data,
        'errors': errors,
        'meta': {
            'timestamp': timezone.now().isoformat(),
            'request_id': generate_request_id()
        }
    }

    return Response(response_data, status=status_code)


def paginated_response(
    data: List[Any],
    request,
    total_count: Optional[int] = None,
    message: str = "Data retrieved successfully",
    status_code: int = status.HTTP_200_OK,
    extra_meta: Optional[Dict[str, Any]] = None
) -> Response:
    """
    Create a standardized paginated response

    Args:
        data: List of items (already paginated or full list)
        request: Django request object (for extracting pagination params)
        total_count: Total number of items (if None, uses len(data))
        message: Human-readable message
        status_code: HTTP status code (default: 200)
        extra_meta: Additional metadata to include

    Returns:
        Response: DRF Response object with pagination metadata

    Example:
        queryset = User.objects.all()
        page, limit = get_pagination_params(request)
        offset = (page - 1) * limit
        paginated_data = queryset[offset:offset + limit]

        return paginated_response(
            data=UserSerializer(paginated_data, many=True).data,
            request=request,
            total_count=queryset.count(),
            message="Users retrieved successfully"
        )
    """
    page, limit = get_pagination_params(request)

    # If total_count not provided, use length of data
    if total_count is None:
        total_count = len(data) if isinstance(data, list) else 0

    pagination_meta = build_pagination_meta(page, limit, total_count)

    response_data = {
        'success': True,
        'message': message,
        'data': data,
        'meta': {
            'timestamp': timezone.now().isoformat(),
            'request_id': generate_request_id(),
            'pagination': pagination_meta,
            **(extra_meta or {})
        }
    }

    return Response(response_data, status=status_code)


def validation_error_response(
    serializer_errors: Dict[str, List[str]],
    message: str = "Validation failed"
) -> Response:
    """
    Create a standardized validation error response from serializer errors

    Args:
        serializer_errors: Serializer validation errors (serializer.errors)
        message: Human-readable error message

    Returns:
        Response: DRF Response object with validation errors

    Example:
        serializer = UserSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors,
                message="Invalid user data"
            )
    """
    return error_response(
        message=message,
        errors=serializer_errors,
        status_code=status.HTTP_400_BAD_REQUEST
    )


def created_response(
    data: Any,
    message: str = "Resource created successfully"
) -> Response:
    """
    Shorthand for 201 Created response

    Args:
        data: Created resource data
        message: Success message

    Returns:
        Response: 201 Created response
    """
    return success_response(data=data, message=message, status_code=status.HTTP_201_CREATED)


def no_content_response(message: str = "Operation completed successfully") -> Response:
    """
    Shorthand for 204 No Content response (for deletions)

    Args:
        message: Success message

    Returns:
        Response: 204 No Content response
    """
    return success_response(data=None, message=message, status_code=status.HTTP_204_NO_CONTENT)


def unauthorized_response(message: str = "Authentication required") -> Response:
    """
    Shorthand for 401 Unauthorized response

    Args:
        message: Error message

    Returns:
        Response: 401 Unauthorized response
    """
    return error_response(message=message, status_code=status.HTTP_401_UNAUTHORIZED)


def forbidden_response(message: str = "Permission denied") -> Response:
    """
    Shorthand for 403 Forbidden response

    Args:
        message: Error message

    Returns:
        Response: 403 Forbidden response
    """
    return error_response(message=message, status_code=status.HTTP_403_FORBIDDEN)


def not_found_response(message: str = "Resource not found") -> Response:
    """
    Shorthand for 404 Not Found response

    Args:
        message: Error message

    Returns:
        Response: 404 Not Found response
    """
    return error_response(message=message, status_code=status.HTTP_404_NOT_FOUND)


def server_error_response(
    message: str = "Internal server error",
    error_details: Optional[str] = None
) -> Response:
    """
    Shorthand for 500 Internal Server Error response

    Args:
        message: Error message
        error_details: Detailed error information (for logging/debugging)

    Returns:
        Response: 500 Internal Server Error response
    """
    return error_response(
        message=message,
        errors={'detail': error_details} if error_details else None,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


class StandardizedResponseMixin:
    """
    Mixin for ViewSets to add standardized response methods

    Usage:
        class UserViewSet(StandardizedResponseMixin, viewsets.ModelViewSet):
            queryset = User.objects.all()
            serializer_class = UserSerializer

            def list(self, request, *args, **kwargs):
                queryset = self.filter_queryset(self.get_queryset())
                page, limit = get_pagination_params(request)
                offset = (page - 1) * limit
                paginated_data = queryset[offset:offset + limit]
                serializer = self.get_serializer(paginated_data, many=True)

                return self.paginated_success_response(
                    data=serializer.data,
                    request=request,
                    total_count=queryset.count()
                )
    """

    def success_response(self, data=None, message="Success", status_code=status.HTTP_200_OK, **kwargs):
        """Convenience method for success responses"""
        return success_response(data=data, message=message, status_code=status_code, meta=kwargs.get('meta'))

    def error_response(self, message="Error", errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        """Convenience method for error responses"""
        return error_response(message=message, errors=errors, status_code=status_code)

    def paginated_success_response(self, data, request, total_count=None, message="Success"):
        """Convenience method for paginated responses"""
        return paginated_response(data=data, request=request, total_count=total_count, message=message)

    def validation_error_response(self, serializer_errors, message="Validation failed"):
        """Convenience method for validation errors"""
        return validation_error_response(serializer_errors=serializer_errors, message=message)

    def created_response(self, data, message="Created successfully"):
        """Convenience method for 201 responses"""
        return created_response(data=data, message=message)

    def forbidden_response(self, message="Permission denied"):
        """Convenience method for 403 responses"""
        return forbidden_response(message=message)

    def not_found_response(self, message="Not found"):
        """Convenience method for 404 responses"""
        return not_found_response(message=message)
