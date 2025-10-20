"""
Signal handlers for automatically starting workflows when expense claims are submitted.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ExpenseClaim
from workflows.engine import WorkflowEngine


@receiver(post_save, sender=ExpenseClaim)
def start_workflow_on_submit(sender, instance, created, **kwargs):
    """
    Automatically start workflow when expense claim status changes to 'Submitted'.

    Args:
        sender: The model class (ExpenseClaim)
        instance: The actual instance being saved
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    # Only start workflow when status is 'Submitted' or 'SUBMITTED'
    if instance.status in ['Submitted', 'SUBMITTED']:
        # Check if workflow already exists for this claim
        from workflows.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(ExpenseClaim)
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
                    module_name='claims'
                )

                print(f"✅ Workflow started for Expense Claim #{instance.id}: {workflow_instance.id}")
            except Exception as e:
                print(f"❌ Failed to start workflow for Expense Claim #{instance.id}: {str(e)}")
