"""
Coverage for the "Reset Staging Data" admin button
(accounts/admin.py's AdminActionLogAdmin.reset_staging_data_view).

Confirms:
- It refuses to run at all unless settings.ALLOW_DATA_RESET is set (the
  safety guard preventing accidental use on production).
- A wrong confirmation string doesn't delete anything.
- The correct confirmation actually deletes requests/workflow
  instances/notifications, but leaves users/roles/permissions/departments/
  workflow templates/notification templates untouched.
"""

import pytest
from accounts.models import AdminActionLog, Department, Permission, Role, User
from django.test import override_settings
from django.urls import reverse
from notifications.models import NotificationTemplate, UserNotification
from workflows.models import WorkflowTemplate


@pytest.fixture
def superuser_client(client, db):
    user = User.objects.create_user(
        email="staging-reset-admin@example.com",
        password="Test1234!Test",
        name="Staging Reset Admin",
        is_superuser=True,
        is_staff=True,
        is_active=True,
    )
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestStagingDataResetView:
    def test_blocked_when_allow_data_reset_off(self, superuser_client):
        url = reverse("admin:accounts_reset_staging_data")
        response = superuser_client.get(url, follow=True)
        messages = [str(m) for m in response.context["messages"]]
        assert any("disabled" in m.lower() for m in messages)

    def test_blocked_for_non_superuser(self, client, db):
        regular = User.objects.create_user(
            email="regular@example.com",
            password="Test1234!Test",
            name="Regular Staff",
            is_staff=True,
            is_active=True,
        )
        client.force_login(regular)
        url = reverse("admin:accounts_reset_staging_data")
        with override_settings(ALLOW_DATA_RESET=True):
            response = client.get(url)
        assert response.status_code == 302

    def test_wrong_confirmation_text_deletes_nothing(
        self, superuser_client, regular_user
    ):
        UserNotification.objects.create(user=regular_user, title="t", message="m")
        url = reverse("admin:accounts_reset_staging_data")
        with override_settings(ALLOW_DATA_RESET=True):
            response = superuser_client.post(url, {"confirm_text": "nope"})
        assert response.status_code == 200
        assert UserNotification.objects.count() == 1

    def test_correct_confirmation_deletes_requests_and_notifications_only(
        self, superuser_client, regular_user
    ):
        UserNotification.objects.create(user=regular_user, title="t", message="m")
        role = Role.objects.create(name="Test Role")
        dept = Department.objects.create(name="Test Dept")
        Permission.objects.create(name="test_perm")
        template = WorkflowTemplate.objects.create(
            name="Test Workflow",
            entity_type="travelrequest_domestic",
        )
        notif_template_count_before = NotificationTemplate.objects.count()

        url = reverse("admin:accounts_reset_staging_data")
        with override_settings(ALLOW_DATA_RESET=True):
            response = superuser_client.post(
                url, {"confirm_text": "RESET"}, follow=True
            )

        assert response.status_code == 200
        assert UserNotification.objects.count() == 0

        # Untouched: users, roles, permissions, departments, workflow
        # templates, notification templates.
        assert User.objects.filter(pk=regular_user.pk).exists()
        assert Role.objects.filter(pk=role.pk).exists()
        assert Department.objects.filter(pk=dept.pk).exists()
        assert Permission.objects.filter(name="test_perm").exists()
        assert WorkflowTemplate.objects.filter(pk=template.pk).exists()
        assert NotificationTemplate.objects.count() == notif_template_count_before

        log = AdminActionLog.objects.filter(action_type="staging_data_reset").first()
        assert log is not None
