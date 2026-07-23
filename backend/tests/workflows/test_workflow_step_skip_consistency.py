"""
Regression test for the 2026-07-23 TRF-can_skip data-consistency fix
(workflows/migrations/0012_fix_travelrequest_can_skip.py).

TRF was the only entity type where every active WorkflowStep disallowed
skipping (can_skip=False), so the shared "Skip this approver" option
(ApproverSelectionComponent, used identically by all 5 request apps) never
appeared for TRF even though the same real-world justification (a role
being vacant/unavailable) applies there as much as anywhere else. This is
the third time this exact drift has happened - migration 0009 originally
set can_skip=True for every step, and 0011 had to re-apply the same fix
for combinedrequest after its steps drifted back to False.
"""

import pytest
from workflows.models import WorkflowTemplate


@pytest.mark.django_db
class TestWorkflowStepSkipConsistency:
    def test_all_active_templates_allow_skip_on_every_step(self):
        templates = WorkflowTemplate.objects.filter(is_active=True)
        assert templates.exists()

        non_skippable = []
        for template in templates:
            for step in template.steps.all():
                if not step.can_skip:
                    non_skippable.append(f"{template.entity_type}:{step.step_name}")

        assert non_skippable == [], (
            "These active workflow steps disallow skipping, inconsistent "
            f"with every other entity type: {non_skippable}"
        )

    def test_travelrequest_steps_specifically_allow_skip(self):
        template = WorkflowTemplate.objects.filter(
            entity_type__iexact="travelrequest", is_active=True
        ).first()
        assert template is not None

        steps = list(template.steps.all())
        assert len(steps) > 0
        assert all(step.can_skip for step in steps)
