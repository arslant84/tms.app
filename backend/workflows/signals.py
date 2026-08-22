"""
Cleanup signals for entities tracked by the generic workflow engine.

WorkflowInstance links to its entity (TravelRequest, TransportRequest,
VisaApplication, AccommodationRequest) via a GenericForeignKey
(content_type + object_id). Django cannot express `on_delete=CASCADE`
across a GenericForeignKey, so deleting one of these entities directly
(e.g. via the admin delete feature) silently left behind orphaned
WorkflowInstance rows (and their still-CASCADE-linked step
executions/delegations/audit logs). Found live via AdminActionLog after
a user-deleted TransportRequest produced a 404 on an old notification's
action_url.

UserNotification also has a content_type/object_id GenericForeignKey,
but NotificationService.create_notification() only populates it when the
caller passes content_object= - and workflows/notifications.py's calls
either pass the WorkflowInstance as content_object (not the underlying
entity) or omit it entirely, relying on action_url alone to point at the
entity's real detail page. So matching on content_type/object_id misses
most notifications; action_url is the only reliable link. Every
action_url workflows/notifications.py generates ends in
/<route-segment>/<object_id> (see _get_action_url in that module), so
match on that suffix instead.

pre_delete (not post_delete) is used so the content_type/object_id pair
is still meaningful at lookup time; the instance itself is deleted here,
before the entity row disappears.
"""

import logging

from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import pre_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)

_ROUTE_SEGMENT = {
    "TravelRequest": "trf",
    "TransportRequest": "transport",
    "VisaApplication": "visa",
    "AccommodationRequest": "accommodation",
}


def _cleanup_workflow_data(sender, instance, **kwargs):
    from notifications.models import UserNotification

    from .models import WorkflowInstance

    content_type = ContentType.objects.get_for_model(sender)

    workflow_count, _ = WorkflowInstance.objects.filter(
        content_type=content_type, object_id=instance.pk
    ).delete()

    route_segment = _ROUTE_SEGMENT[sender.__name__]
    notification_count, _ = UserNotification.objects.filter(
        content_type=content_type, object_id=instance.pk
    ).delete()
    url_notification_count, _ = UserNotification.objects.filter(
        action_url__regex=rf"/{route_segment}/{instance.pk}$"
    ).delete()
    notification_count += url_notification_count

    if workflow_count or notification_count:
        logger.info(
            "Cleaned up %d WorkflowInstance(s) and %d UserNotification(s) "
            "for deleted %s #%s",
            workflow_count,
            notification_count,
            sender.__name__,
            instance.pk,
        )


def register_cleanup_signals():
    from accommodation.models import AccommodationRequest
    from transport.models import TransportRequest
    from trf.models import TravelRequest
    from visa.models import VisaApplication

    for model in (
        TravelRequest,
        TransportRequest,
        VisaApplication,
        AccommodationRequest,
    ):
        receiver(pre_delete, sender=model)(_cleanup_workflow_data)
