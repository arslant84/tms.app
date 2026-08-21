"""
Generic Celery task status endpoint.

Allows the frontend to poll for the result of any async task by task_id.
Only authenticated users can query task status.
"""

import logging

from celery.result import AsyncResult
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def task_status(request, task_id):
    """
    Return the current status of a Celery task.

    Possible statuses: PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED.

    On SUCCESS, `result` contains the task's return value.
    On FAILURE, `error` contains the exception message.
    """
    result = AsyncResult(task_id)
    data = {
        "task_id": task_id,
        "status": result.status,
    }
    if result.successful():
        data["result"] = result.result
    elif result.failed():
        data["error"] = str(result.result)

    return Response(data)
