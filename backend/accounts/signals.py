"""
Signals for audit logging of user-related actions.
Automatically logs security-relevant events for compliance and monitoring.
"""

from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from .models import User, Role, RolePermission, AdminActionLog
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def log_user_changes(sender, instance, created, **kwargs):
    """
    Log user creation and modifications.
    Tracks account creation, role changes, and status changes.
    """
    try:
        if created:
            # Log new user creation
            AdminActionLog.log_action(
                user=None,  # System action or will be set by view
                action_type='user_created',
                description=f"User account created: {instance.email} ({instance.name})",
                entity_type='User',
                entity_id=str(instance.id)
            )
            logger.info(f"Audit: User created - {instance.email}")
        else:
            # Check for status changes (activation/deactivation)
            if hasattr(instance, '_previous_is_active'):
                if instance._previous_is_active != instance.is_active:
                    action_type = 'user_activated' if instance.is_active else 'user_deactivated'
                    status_text = 'activated' if instance.is_active else 'deactivated'
                    AdminActionLog.log_action(
                        user=None,  # Will be set by view
                        action_type=action_type,
                        description=f"User account {status_text}: {instance.email}",
                        entity_type='User',
                        entity_id=str(instance.id)
                    )
                    logger.info(f"Audit: User {status_text} - {instance.email}")

            # Check for role changes
            if hasattr(instance, '_previous_role_id'):
                if instance._previous_role_id != (instance.role.id if instance.role else None):
                    old_role = "None" if not instance._previous_role_id else str(instance._previous_role_id)
                    new_role = "None" if not instance.role else instance.role.name
                    AdminActionLog.log_action(
                        user=None,  # Will be set by view
                        action_type='user_role_changed',
                        description=f"User role changed for {instance.email}: {old_role} → {new_role}",
                        entity_type='User',
                        entity_id=str(instance.id)
                    )
                    logger.info(f"Audit: User role changed - {instance.email}")

    except Exception as e:
        logger.error(f"Error logging user change: {e}", exc_info=True)


@receiver(post_delete, sender=User)
def log_user_deletion(sender, instance, **kwargs):
    """Log user account deletion."""
    try:
        AdminActionLog.log_action(
            user=None,  # Will be set by view or system
            action_type='user_deleted',
            description=f"User account deleted: {instance.email} ({instance.name})",
            entity_type='User',
            entity_id=str(instance.id)
        )
        logger.info(f"Audit: User deleted - {instance.email}")
    except Exception as e:
        logger.error(f"Error logging user deletion: {e}", exc_info=True)


@receiver(post_save, sender=Role)
def log_role_changes(sender, instance, created, **kwargs):
    """Log role creation and modifications."""
    try:
        if created:
            AdminActionLog.log_action(
                user=None,  # Will be set by view
                action_type='role_created',
                description=f"Role created: {instance.name}",
                entity_type='Role',
                entity_id=str(instance.id)
            )
            logger.info(f"Audit: Role created - {instance.name}")
    except Exception as e:
        logger.error(f"Error logging role change: {e}", exc_info=True)


@receiver(post_delete, sender=Role)
def log_role_deletion(sender, instance, **kwargs):
    """Log role deletion."""
    try:
        AdminActionLog.log_action(
            user=None,  # Will be set by view or system
            action_type='role_deleted',
            description=f"Role deleted: {instance.name}",
            entity_type='Role',
            entity_id=str(instance.id)
        )
        logger.info(f"Audit: Role deleted - {instance.name}")
    except Exception as e:
        logger.error(f"Error logging role deletion: {e}", exc_info=True)


@receiver(m2m_changed, sender=RolePermission)
def log_role_permission_changes(sender, instance, action, **kwargs):
    """
    Log changes to role permissions.
    Tracks when permissions are added or removed from roles.
    """
    try:
        if action in ['post_add', 'post_remove']:
            action_desc = 'added to' if action == 'post_add' else 'removed from'
            # instance is the Role when using reverse relation
            if isinstance(instance, Role):
                AdminActionLog.log_action(
                    user=None,  # Will be set by view
                    action_type='role_permissions_modified',
                    description=f"Permissions {action_desc} role: {instance.name}",
                    entity_type='Role',
                    entity_id=str(instance.id)
                )
                logger.info(f"Audit: Role permissions modified - {instance.name}")
    except Exception as e:
        logger.error(f"Error logging role permission change: {e}", exc_info=True)
