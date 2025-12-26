"""
Signal handlers for automatically starting workflows when visa applications are submitted.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import VisaApplication
from workflows.engine import WorkflowEngine


@receiver(post_save, sender=VisaApplication)
def start_workflow_on_submit(sender, instance, created, **kwargs):
    """
    Automatically start workflow when visa application status changes to 'Submitted'.

    Args:
        sender: The model class (VisaApplication)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    # Only start workflow when status is 'Submitted'
    if instance.status == 'Submitted':
        # Check if workflow already exists for this visa application
        from workflows.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(VisaApplication)
        existing_workflow = WorkflowInstance.objects.filter(
            content_type=content_type,
            object_id=instance.id
        ).first()

        # Only create workflow if it doesn't exist yet
        if not existing_workflow:
            try:
                # Start the workflow
                workflow_instance = WorkflowEngine.start_workflow(
                    entity=instance,
                    initiated_by=instance.user,  # Visa uses 'user' field
                    module_name='visaapplication'  # Must match WorkflowTemplate.entity_type
                )

                print(f"Workflow started for Visa Application #{instance.id}: {workflow_instance.id}")
            except Exception as e:
                print(f"Failed to start workflow for Visa Application #{instance.id}: {str(e)}")
