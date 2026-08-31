"""
Regression coverage for Phase 1 of docs/TSR_SUBMODULE_WORKFLOW_ROADMAP.md -
per-travel-type workflow entity_type resolution with a fallback to the
existing shared "travelrequest" template.
"""

import pytest
from trf.models import TravelRequest
from workflows.engine import WorkflowEngine
from workflows.models import WorkflowStep, WorkflowTemplate
from workflows.router import WorkflowRouter


@pytest.fixture
def shared_trf_workflow(db, admin_user):
    """The existing shared template every travel type falls back to today."""
    template = WorkflowTemplate.objects.create(
        name="Shared TRF Workflow",
        entity_type="travelrequest",
        is_active=True,
        created_by=admin_user,
    )
    WorkflowStep.objects.create(
        workflow_template=template,
        step_order=1,
        step_name="Manager Approval",
        is_required=True,
        can_skip=False,
    )
    return template


@pytest.mark.django_db
class TestWorkflowEntityTypeProperty:
    def test_maps_each_canonical_travel_type(self, regular_user):
        expected = {
            "Domestic": "travelrequest_domestic",
            "Overseas": "travelrequest_overseas",
            "External Parties": "travelrequest_external",
        }
        for travel_type, expected_entity_type in expected.items():
            trf = TravelRequest(
                requestor_name=regular_user.name,
                travel_type=travel_type,
                status="Draft",
                created_by=regular_user,
            )
            assert trf.workflow_entity_type == expected_entity_type

    def test_unknown_travel_type_falls_back_to_generic(self, regular_user):
        trf = TravelRequest(
            requestor_name=regular_user.name,
            travel_type="Something Unexpected",
            status="Draft",
            created_by=regular_user,
        )
        assert trf.workflow_entity_type == "travelrequest"


@pytest.mark.django_db
class TestWorkflowTemplateGetActiveFor:
    def test_returns_none_when_neither_exists(self):
        assert WorkflowTemplate.get_active_for("travelrequest_domestic") is None

    def test_falls_back_when_specific_missing(self, shared_trf_workflow):
        result = WorkflowTemplate.get_active_for(
            "travelrequest_domestic", fallback="travelrequest"
        )
        assert result.id == shared_trf_workflow.id

    def test_prefers_specific_over_fallback(self, shared_trf_workflow, admin_user):
        domestic_template = WorkflowTemplate.objects.create(
            name="Domestic-Specific Workflow",
            entity_type="travelrequest_domestic",
            is_active=True,
            created_by=admin_user,
        )
        WorkflowStep.objects.create(
            workflow_template=domestic_template,
            step_order=1,
            step_name="Domestic Manager Approval",
            is_required=True,
            can_skip=False,
        )

        result = WorkflowTemplate.get_active_for(
            "travelrequest_domestic", fallback="travelrequest"
        )
        assert result.id == domestic_template.id


@pytest.mark.django_db
class TestStartWorkflowForRequestFallback:
    def test_no_subtype_template_routes_through_shared_template(
        self, shared_trf_workflow, regular_user
    ):
        """
        Day-one guarantee from the roadmap: with no sub-type template
        configured, every travel type must still route through the existing
        shared "travelrequest" template - byte-identical to today's behavior.
        """
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending",
            created_by=regular_user,
        )

        instance = WorkflowRouter.start_workflow_for_request(
            entity=trf,
            entity_type=trf.workflow_entity_type,
            initiated_by=regular_user,
            fallback_entity_type="travelrequest",
        )

        assert instance is not None
        assert instance.workflow_template_id == shared_trf_workflow.id

    def test_subtype_template_is_used_once_configured(
        self, shared_trf_workflow, admin_user, regular_user
    ):
        """Once an admin configures a dedicated template for one travel type,
        that type - and only that type - uses it; others keep falling back."""
        domestic_template = WorkflowTemplate.objects.create(
            name="Domestic-Specific Workflow",
            entity_type="travelrequest_domestic",
            is_active=True,
            created_by=admin_user,
        )
        WorkflowStep.objects.create(
            workflow_template=domestic_template,
            step_order=1,
            step_name="Domestic Manager Approval",
            is_required=True,
            can_skip=False,
        )

        domestic_trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Domestic",
            status="Pending",
            created_by=regular_user,
        )
        overseas_trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="Overseas",
            status="Pending",
            created_by=regular_user,
        )

        domestic_instance = WorkflowRouter.start_workflow_for_request(
            entity=domestic_trf,
            entity_type=domestic_trf.workflow_entity_type,
            initiated_by=regular_user,
            fallback_entity_type="travelrequest",
        )
        overseas_instance = WorkflowRouter.start_workflow_for_request(
            entity=overseas_trf,
            entity_type=overseas_trf.workflow_entity_type,
            initiated_by=regular_user,
            fallback_entity_type="travelrequest",
        )

        assert domestic_instance.workflow_template_id == domestic_template.id
        assert overseas_instance.workflow_template_id == shared_trf_workflow.id


@pytest.mark.django_db
class TestEngineFallbackConsistency:
    def test_engine_start_workflow_honors_fallback_directly(
        self, shared_trf_workflow, regular_user
    ):
        """WorkflowEngine.start_workflow itself (not just the router wrapper)
        must resolve the same fallback, since it does its own independent
        lookup."""
        trf = TravelRequest.objects.create(
            requestor_name=regular_user.name,
            travel_type="External Parties",
            status="Pending",
            created_by=regular_user,
        )

        instance = WorkflowEngine.start_workflow(
            entity=trf,
            initiated_by=regular_user,
            module_name=trf.workflow_entity_type,
            fallback_module_name="travelrequest",
        )

        assert instance.workflow_template_id == shared_trf_workflow.id
