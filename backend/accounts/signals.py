"""
Signals for audit logging of user-related actions.
Automatically logs security-relevant events for compliance and monitoring.
"""

import logging

from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import AdminActionLog, Role, RolePermission, User

logger = logging.getLogger(__name__)


def _cleanup_stale_approval_notifications(user):
    """
    A pending "Action Required: Approve ..." notification is tied to a
    WorkflowStepExecution.assigned_to that was resolved once, at the moment
    the step activated (see workflows/engine.py's _resolve_step_assignee) -
    it is never re-resolved when the recipient's role changes later. Left
    alone, the notification (and the approver assignment behind it) stays
    pointed at a user who has since lost the role/permission that made them
    an eligible approver in the first place.

    There's no cheap way to re-check per-notification whether the *new*
    role happens to still grant the same permission, so on any role change
    every unread notification in the 'approval' category (APPROVAL_REQUESTED
    / APPROVAL_DELEGATED - the only categories that ask the recipient to
    take an approval action) is deleted outright rather than left to pile up
    pointing at access the user may no longer have.
    """
    from notifications.models import UserNotification

    count, _ = UserNotification.objects.filter(
        user=user, is_read=False, event_type__category="approval"
    ).delete()

    if count:
        logger.info(
            "Cleaned up %d stale approval notification(s) for %s after role change",
            count,
            user.email,
        )


@receiver(pre_save, sender=User)
def capture_previous_user_state(sender, instance, **kwargs):
    """Snapshot role and active status before save so post_save can detect changes."""
    if instance.pk:
        try:
            previous = User.objects.get(pk=instance.pk)
            instance._previous_role_id = previous.role.id if previous.role else None
            instance._previous_is_active = previous.is_active
        except User.DoesNotExist:
            pass


@receiver(post_save, sender=User)
def log_user_changes(sender, instance, created, **kwargs):
    """
    Log user creation and modifications.
    Tracks account creation, role changes, and status changes.
    """
    try:
        req = getattr(instance, "_update_request", None)
        if created:
            logger.info(f"Audit: User created - {instance.email}")
        else:
            # Check for status changes (activation/deactivation)
            if hasattr(instance, "_previous_is_active"):
                if instance._previous_is_active != instance.is_active:
                    action_type = (
                        "user_activated" if instance.is_active else "user_deactivated"
                    )
                    status_text = "activated" if instance.is_active else "deactivated"
                    AdminActionLog.log_action(
                        user=req.user if req else None,
                        action_type=action_type,
                        description=f"User account {status_text}: {instance.email}",
                        entity_type="User",
                        entity_id=str(instance.id),
                        request=req,
                    )
                    logger.info(f"Audit: User {status_text} - {instance.email}")

            # Check for role changes
            if hasattr(instance, "_previous_role_id"):
                if instance._previous_role_id != (
                    instance.role.id if instance.role else None
                ):
                    req = getattr(instance, "_update_request", None)
                    old_role = (
                        "None"
                        if not instance._previous_role_id
                        else str(instance._previous_role_id)
                    )
                    new_role = "None" if not instance.role else instance.role.name
                    AdminActionLog.log_action(
                        user=req.user if req else None,
                        action_type="user_role_changed",
                        description=f"User role changed for {instance.email}: {old_role} → {new_role}",
                        entity_type="User",
                        entity_id=str(instance.id),
                        request=req,
                    )
                    logger.info(f"Audit: User role changed - {instance.email}")
                    _cleanup_stale_approval_notifications(instance)

    except Exception as e:
        logger.error(f"Error logging user change: {e}", exc_info=True)


@receiver(post_delete, sender=User)
def log_user_deletion(sender, instance, **kwargs):
    """Log user account deletion — only for paths that don't log via perform_destroy (e.g. Django admin)."""
    try:
        req = getattr(instance, "_update_request", None)
        if not getattr(instance, "_deletion_logged", False):
            AdminActionLog.log_action(
                user=req.user if (req and req.user.is_authenticated) else None,
                action_type="user_deleted",
                description=f"User account deleted: {instance.email} ({instance.name})",
                entity_type="User",
                entity_id=str(instance.id),
                request=req,
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
                action_type="role_created",
                description=f"Role created: {instance.name}",
                entity_type="Role",
                entity_id=str(instance.id),
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
            action_type="role_deleted",
            description=f"Role deleted: {instance.name}",
            entity_type="Role",
            entity_id=str(instance.id),
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
        if action in ["post_add", "post_remove"]:
            action_desc = "added to" if action == "post_add" else "removed from"
            # instance is the Role when using reverse relation
            if isinstance(instance, Role):
                AdminActionLog.log_action(
                    user=None,  # Will be set by view
                    action_type="role_permissions_modified",
                    description=f"Permissions {action_desc} role: {instance.name}",
                    entity_type="Role",
                    entity_id=str(instance.id),
                )
                logger.info(f"Audit: Role permissions modified - {instance.name}")
    except Exception as e:
        logger.error(f"Error logging role permission change: {e}", exc_info=True)
