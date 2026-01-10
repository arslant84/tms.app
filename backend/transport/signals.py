"""
Signal handlers for automatically starting workflows when transport requests are submitted.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import TransportRequest
from workflows.signals_base import start_workflow_on_status


@receiver(post_save, sender=TransportRequest)
def start_workflow_on_submit(sender, instance, created, **kwargs):
    """
    Automatically start workflow when transport request status changes to 'Submitted'.

    Uses the generic workflow trigger from workflows.signals_base to avoid code duplication.

    Args:
        sender: The model class (TransportRequest)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    start_workflow_on_status(
        instance=instance,
        status_field='status',
        trigger_status='Submitted',
        initiated_by_field='created_by',
        module_name='transport'
    )
