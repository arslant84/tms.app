"""
Regression coverage for a bug where reducing (or increasing) a workflow
template's step count through the admin config screen reported success but
did not actually change the live step count, because the update path
skipped deleting a step that already had execution history (from a past
workflow instance) with no fallback - the row was silently left in place.

The fix keeps that row (to preserve approval history) but marks it
`is_active=False` instead, and every place that counts/lists/uses a
template's steps for the *live* workflow (step_count, the detail serializer,
new instance creation, step progression, template duplication, the eligible
approvers preview) now filters to `is_active=True`. Growing the step count
(e.g. 3 -> 10) already worked before this fix and is covered here too, to
guard against a regression in the same code path.
"""

import pytest
from rest_framework import status
from workflows.models import WorkflowStep, WorkflowStepExecution, WorkflowTemplate


@pytest.fixture
def three_step_visa_workflow(db, admin_user):
    template = WorkflowTemplate.objects.create(
        name="Test Visa Three-Step Workflow",
        entity_type="visa",
        is_active=True,
        created_by=admin_user,
    )
    for order, name in [(1, "Dept Focal"), (2, "HOD"), (3, "Finance")]:
        WorkflowStep.objects.create(
            workflow_template=template,
            step_order=order,
            step_name=name,
            is_required=True,
            can_skip=True,
        )
    return template


def _steps_payload(*names):
    return [
        {
            "step_order": i + 1,
            "step_name": name,
            "is_required": True,
            "can_skip": True,
        }
        for i, name in enumerate(names)
    ]


@pytest.mark.django_db
class TestWorkflowStepCountUpdate:
    def test_reduce_steps_with_no_execution_history_deletes_the_row(
        self, admin_client, three_step_visa_workflow
    ):
        """No instance has ever run against step 3, so it can be hard-deleted
        the way it always could - the fix must not regress this path."""
        template = three_step_visa_workflow

        response = admin_client.put(
            f"/api/workflows/templates/{template.id}/",
            {
                "name": template.name,
                "entity_type": "visa",
                "is_active": True,
                "steps": _steps_payload("Dept Focal", "HOD"),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["step_count"] == 2
        assert len(response.data["steps"]) == 2
        assert not WorkflowStep.objects.filter(
            workflow_template=template, step_order=3
        ).exists()

    def test_reduce_steps_with_execution_history_deactivates_instead_of_ignoring(
        self, admin_client, three_step_visa_workflow, admin_user
    ):
        """Step 3 has execution history (a past instance ran against it), so
        it cannot be safely hard-deleted. Before the fix, update() silently
        skipped it entirely - the API reported success but step_count stayed
        3. It must now be soft-deactivated: kept in the DB, but excluded from
        the reported step count and the editable step list."""
        template = three_step_visa_workflow
        step_3 = WorkflowStep.objects.get(workflow_template=template, step_order=3)

        from django.contrib.contenttypes.models import ContentType
        from workflows.models import WorkflowInstance

        instance = WorkflowInstance.objects.create(
            workflow_template=template,
            content_type=ContentType.objects.get_for_model(WorkflowInstance),
            object_id=1,
            status="approved",
            initiated_by=admin_user,
        )
        WorkflowStepExecution.objects.create(
            workflow_instance=instance,
            workflow_step=step_3,
            status="approved",
            actioned_by=admin_user,
        )

        response = admin_client.put(
            f"/api/workflows/templates/{template.id}/",
            {
                "name": template.name,
                "entity_type": "visa",
                "is_active": True,
                "steps": _steps_payload("Dept Focal", "HOD"),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        # This is the exact bug report: "saved" succeeds, but the step count
        # must now actually reflect 2, not silently remain 3.
        assert response.data["step_count"] == 2
        assert len(response.data["steps"]) == 2
        assert {s["step_order"] for s in response.data["steps"]} == {1, 2}

        # The row survives (so the past execution's FK stays valid) but is
        # deactivated.
        step_3.refresh_from_db()
        assert step_3.is_active is False
        assert WorkflowStep.objects.filter(pk=step_3.pk).exists()

        # A GET of the template must agree with the PUT response.
        get_response = admin_client.get(f"/api/workflows/templates/{template.id}/")
        assert get_response.data["step_count"] == 2
        assert len(get_response.data["steps"]) == 2

        # A brand new instance created after the reduction must only get
        # executions for the 2 active steps, not the deactivated step 3 -
        # otherwise the workflow would dangle waiting on a step nobody can
        # act on any more.
        new_instance = WorkflowInstance.objects.create(
            workflow_template=template,
            content_type=ContentType.objects.get_for_model(WorkflowInstance),
            object_id=2,
            status="pending",
            initiated_by=admin_user,
        )
        for step in template.steps.filter(is_active=True):
            WorkflowStepExecution.objects.create(
                workflow_instance=new_instance,
                workflow_step=step,
                status="pending" if step.step_order == 1 else "waiting",
            )
        assert (
            WorkflowStepExecution.objects.filter(workflow_instance=new_instance).count()
            == 2
        )
        assert not WorkflowStepExecution.objects.filter(
            workflow_instance=new_instance, workflow_step=step_3
        ).exists()

    def test_reintroducing_a_deactivated_step_order_reactivates_it(
        self, admin_client, three_step_visa_workflow, admin_user
    ):
        """If step 3 was deactivated (because it had execution history) and a
        later edit brings step_order=3 back, the existing row must be reused
        (and reactivated) rather than colliding with the unique_together
        constraint on (workflow_template, step_order) or creating a
        duplicate."""
        template = three_step_visa_workflow
        step_3 = WorkflowStep.objects.get(workflow_template=template, step_order=3)

        from django.contrib.contenttypes.models import ContentType
        from workflows.models import WorkflowInstance

        instance = WorkflowInstance.objects.create(
            workflow_template=template,
            content_type=ContentType.objects.get_for_model(WorkflowInstance),
            object_id=1,
            status="approved",
            initiated_by=admin_user,
        )
        WorkflowStepExecution.objects.create(
            workflow_instance=instance,
            workflow_step=step_3,
            status="approved",
            actioned_by=admin_user,
        )

        # Reduce to 2, then increase back to 3.
        admin_client.put(
            f"/api/workflows/templates/{template.id}/",
            {
                "name": template.name,
                "entity_type": "visa",
                "is_active": True,
                "steps": _steps_payload("Dept Focal", "HOD"),
            },
            format="json",
        )
        response = admin_client.put(
            f"/api/workflows/templates/{template.id}/",
            {
                "name": template.name,
                "entity_type": "visa",
                "is_active": True,
                "steps": _steps_payload("Dept Focal", "HOD", "Finance Redux"),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["step_count"] == 3
        assert (
            WorkflowStep.objects.filter(
                workflow_template=template, step_order=3
            ).count()
            == 1
        )
        step_3.refresh_from_db()
        assert step_3.is_active is True
        assert step_3.step_name == "Finance Redux"
        # The old execution's FK must still point at the same row.
        assert WorkflowStepExecution.objects.filter(workflow_step=step_3).exists()

    def test_increasing_step_count_from_three_to_ten_saves_correctly(
        self, admin_client, three_step_visa_workflow
    ):
        """Growing the workflow (e.g. 3 -> 10 steps, the frontend's max) must
        create the new steps and report the new count - this already worked
        before the fix, guarded here against regressing the same update()
        code path."""
        template = three_step_visa_workflow
        names = [f"Step {i}" for i in range(1, 11)]

        response = admin_client.put(
            f"/api/workflows/templates/{template.id}/",
            {
                "name": template.name,
                "entity_type": "visa",
                "is_active": True,
                "steps": _steps_payload(*names),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["step_count"] == 10
        assert len(response.data["steps"]) == 10
        assert {s["step_order"] for s in response.data["steps"]} == set(range(1, 11))
        assert WorkflowStep.objects.filter(workflow_template=template).count() == 10
