"""
Signal handlers for automatically starting workflows when transport requests are submitted.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import TransportRequest
from workflows.engine import WorkflowEngine


@receiver(post_save, sender=TransportRequest)
def start_workflow_on_submit(sender, instance, created, **kwargs):
    """
    Automatically start workflow when transport request status changes to 'Submitted'.

    Args:
        sender: The model class (TransportRequest)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    # Only start workflow when status is 'Submitted' and not already processing
    if instance.status == 'Submitted':
        # Check if workflow already exists for this request
        from workflows.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(TransportRequest)
        existing_workflow = WorkflowInstance.objects.filter(
            entity_content_type=content_type,
            entity_id=instance.id
        ).first()

        # Only create workflow if it doesn't exist yet
        if not existing_workflow:
            try:
                # Start the workflow
                workflow_instance = WorkflowEngine.start_workflow(
                    entity=instance,
                    initiated_by=instance.created_by,
                    module_name='transport'
                )

                print(f"✅ Workflow started for Transport Request #{instance.id}: {workflow_instance.id}")
            except Exception as e:
                print(f"❌ Failed to start workflow for Transport Request #{instance.id}: {str(e)}")
