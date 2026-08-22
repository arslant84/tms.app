"""
Regression tests for the 2026-07-24 fix: workflows.WorkflowStepNotificationConfigViewSet
was never registered in urls.py, and attempting to register it as originally
written crashed the app at import time - it imported 4 serializers that
don't exist (WorkflowStepNotificationConfigListSerializer, RoleSimpleSerializer,
UserSimpleSerializer, NotificationTemplateSimpleSerializer) and referenced
model fields (trigger_event, created_by, recipient_roles/users, cc_*, bcc_*)
that don't exist on the real WorkflowStepNotificationConfig model - it was
written against an abandoned schema. Rewrote the view against the real
model (event_type + a recipient_types JSONField) and added the 3
genuinely-needed simple serializers.
"""

import pytest
from accounts.models import Permission, Role, RolePermission
from rest_framework import status


@pytest.fixture
def notification_config_manager(db):
    """A user whose role has manage_notifications, matching the
    CanManageNotifications gate this ViewSet now shares with
    NotificationTemplateViewSet/NotificationEventTypeViewSet."""
    from accounts.models import User

    permission, _ = Permission.objects.get_or_create(
        name="manage_notifications", defaults={"description": "manage_notifications"}
    )
    role = Role.objects.create(name="Notification Config Manager Test")
    RolePermission.objects.create(role=role, permission=permission)
    return User.objects.create_user(
        email="notification-config-manager@example.com",
        password="testpass123",
        name="Notification Config Manager",
        role=role,
    )


@pytest.mark.django_db
class TestWorkflowStepNotificationConfigPermissions:
    def test_regular_user_without_permission_is_forbidden(
        self, api_client, regular_user
    ):
        api_client.force_authenticate(user=regular_user)
        response = api_client.get("/api/workflows/notification-configs/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_with_manage_notifications_succeeds(
        self, api_client, notification_config_manager
    ):
        api_client.force_authenticate(user=notification_config_manager)
        response = api_client.get("/api/workflows/notification-configs/")
        assert response.status_code == status.HTTP_200_OK

    def test_superuser_without_role_succeeds(self, admin_client):
        response = admin_client.get("/api/workflows/notification-configs/")
        assert response.status_code == status.HTTP_200_OK


@pytest.fixture
def trf_workflow_step(db):
    """Minimal WorkflowTemplate + WorkflowStep + one NotificationConfig for travelrequest."""
    from notifications.models import NotificationTemplate
    from workflows.models import (
        WorkflowStep,
        WorkflowStepNotificationConfig,
        WorkflowTemplate,
    )

    template = WorkflowTemplate.objects.create(
        name="TRF Test Workflow",
        entity_type="travelrequest",
        is_active=True,
    )
    step = WorkflowStep.objects.create(
        workflow_template=template,
        step_order=1,
        step_name="Line Manager",
        can_skip=True,
    )
    notif_template = NotificationTemplate.objects.filter(
        name="approval_required"
    ).first()
    if notif_template:
        WorkflowStepNotificationConfig.objects.create(
            workflow_step=step,
            event_type="approval",
            notification_template=notif_template,
            recipient_types=["current_approver"],
        )
    return step


@pytest.mark.django_db
class TestWorkflowStepNotificationConfigEndpoints:
    def test_list_returns_real_configs(self, admin_client):
        response = admin_client.get("/api/workflows/notification-configs/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) > 0

    def test_options_returns_expected_shape(self, admin_client):
        response = admin_client.get("/api/workflows/notification-configs/options/")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        for key in (
            "event_types",
            "recipient_types",
            "priorities",
            "roles",
            "users",
            "templates",
        ):
            assert key in body

    def test_by_step_returns_configs_for_that_step_only(
        self, admin_client, trf_workflow_step
    ):
        step = trf_workflow_step

        response = admin_client.get(
            f"/api/workflows/notification-configs/by_step/{step.id}/"
        )
        assert response.status_code == status.HTTP_200_OK
        results = response.json()
        assert len(results) > 0
        assert all(r["workflow_step"] == step.id for r in results)

    def test_create_update_delete_round_trip(self, admin_client, trf_workflow_step):
        from notifications.models import NotificationTemplate
        from workflows.models import WorkflowStepNotificationConfig

        step = trf_workflow_step
        template = NotificationTemplate.objects.filter(name="approval_required").first()
        assert step is not None
        assert template is not None

        payload = {
            "workflow_step": step.id,
            "event_type": "delegation",
            "notification_template": str(template.id),
            "recipient_types": ["current_approver"],
            "is_active": True,
            "send_email": True,
            "send_system_notification": True,
            "priority": "normal",
        }
        create_response = admin_client.post(
            "/api/workflows/notification-configs/", payload, format="json"
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        config_id = create_response.json()["id"]

        update_response = admin_client.patch(
            f"/api/workflows/notification-configs/{config_id}/",
            {"priority": "urgent"},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["priority"] == "urgent"

        delete_response = admin_client.delete(
            f"/api/workflows/notification-configs/{config_id}/"
        )
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
        assert not WorkflowStepNotificationConfig.objects.filter(id=config_id).exists()


@pytest.mark.django_db
class TestNotificationConfigConsistencyAcrossApps:
    """Regression test for the follow-up fix: travelrequest and
    combinedrequest previously had 0 WorkflowStepNotificationConfig rows
    while accommodation/transportrequest/visaapplication had 20 total -
    populate_default_notification_configs was only ever run for 3 of 5
    apps. Re-ran it for real to close the gap."""

    def test_every_active_template_entity_type_has_notification_configs(self):
        from workflows.models import WorkflowStepNotificationConfig, WorkflowTemplate

        entity_types_with_configs = set(
            WorkflowStepNotificationConfig.objects.values_list(
                "workflow_step__workflow_template__entity_type", flat=True
            ).distinct()
        )
        entity_types_active = set(
            WorkflowTemplate.objects.filter(is_active=True).values_list(
                "entity_type", flat=True
            )
        )

        missing = entity_types_active - entity_types_with_configs
        assert missing == set(), (
            f"These entity types have no WorkflowStepNotificationConfig rows "
            f"at all, inconsistent with the others: {missing}"
        )

    def test_every_active_step_has_all_six_event_types_configured(self):
        """Regression test for Fix 19: workflow_completed/workflow_cancelled
        previously had zero configs for every app (not just a
        travelrequest/combinedrequest gap) since nothing ever populated
        them - only assignment/approval/rejection/delegation were covered.
        Every active WorkflowStep should now have one config per event type.
        ('reminder' was a seventh event type here originally, retired along
        with the SLA due-date/reminder-email feature it powered.)

        'processing_completed' (added for Transport/Visa's post-approval
        admin processing step - see notify_processing_completed) is
        intentionally excluded from the "every step" check below: unlike
        the other six, it's only meaningful for the two modules that have
        a distinct complete() action after approval, so it's only seeded
        on those two templates' last step, not universally."""
        from workflows.models import WorkflowStep, WorkflowStepNotificationConfig

        universal_event_types = {
            "assignment",
            "approval",
            "rejection",
            "delegation",
            "workflow_completed",
            "workflow_cancelled",
        }
        all_event_types = {
            choice[0] for choice in WorkflowStepNotificationConfig.EVENT_TYPE_CHOICES
        }
        assert all_event_types == universal_event_types | {"processing_completed"}

        for step in WorkflowStep.objects.filter(
            workflow_template__is_active=True
        ).select_related("workflow_template"):
            configured = set(
                WorkflowStepNotificationConfig.objects.filter(
                    workflow_step=step
                ).values_list("event_type", flat=True)
            )
            missing = universal_event_types - configured
            assert missing == set(), (
                f"Step '{step.step_name}' on "
                f"'{step.workflow_template.name}' is missing configs for: {missing}"
            )
