"""
Unit tests for the LangGraph workflow routing and node logic.

Tests the audit compliance node and the conditional routing
logic without making actual LLM API calls.
"""

import pytest

from src.workflow.nodes import audit_compliance
from src.workflow.state import WorkflowState


class TestAuditCompliance:
    """Tests for the audit_compliance workflow node."""

    def _make_state(
        self,
        markdown: str,
        project_id: str = "PRJ-001",
        bank_name: str = "Meridian Continental Bank",
        personnel: list | None = None,
        regulations: list | None = None,
        budget: float = 12_500_000.0,
        attempts: int = 0,
    ) -> WorkflowState:
        """Helper to construct a minimal WorkflowState for audit testing."""
        if personnel is None:
            personnel = [
                {"full_name": "Dr. Elena Vasquez", "personnel_id": "PER-001"},
                {"full_name": "Marcus Chen", "personnel_id": "PER-002"},
            ]
        if regulations is None:
            regulations = [{"code": "Basel III"}]

        return WorkflowState(
            project_id=project_id,
            doc_type="rfp",
            project={
                "project_id": project_id,
                "budget_usd": budget,
                "bank_id": "BNK-001",
            },
            bank={"bank_id": "BNK-001", "name": bank_name},
            personnel=personnel,
            regulations=regulations,
            markdown=markdown,
            audit_attempts=attempts,
        )

    def test_audit_passes_when_all_entities_present(self) -> None:
        """Audit should pass when all seed entities are referenced in the text."""
        markdown = (
            "# RFP for PRJ-001\n\n"
            "Prepared by Meridian Continental Bank.\n\n"
            "Stakeholders: Dr. Elena Vasquez (CTO), Marcus Chen (PM).\n\n"
            "Budget: $12,500,000.00\n\n"
            "Compliant with Basel III requirements."
        )
        state = self._make_state(markdown=markdown)
        result = audit_compliance(state)

        assert result["audit_passed"] is True
        assert result["audit_issues"] == []
        assert "final_markdown" in result

    def test_audit_fails_missing_project_id(self) -> None:
        """Audit should fail when the project ID is missing from text."""
        markdown = (
            "# RFP Document\n\n"
            "Prepared by Meridian Continental Bank.\n"
            "Vasquez, Chen. Budget: $12,500,000. Basel III."
        )
        state = self._make_state(markdown=markdown)
        result = audit_compliance(state)

        assert result["audit_passed"] is False
        assert any("PRJ-001" in issue for issue in result["audit_issues"])

    def test_audit_fails_missing_personnel(self) -> None:
        """Audit should fail when a stakeholder is not mentioned."""
        markdown = (
            "# RFP for PRJ-001\n\n"
            "Meridian Continental Bank.\n"
            "Dr. Elena Vasquez only mentioned.\n"
            "Budget: $12,500,000. Basel III."
        )
        state = self._make_state(markdown=markdown)
        result = audit_compliance(state)

        assert result["audit_passed"] is False
        assert any("Marcus Chen" in issue for issue in result["audit_issues"])

    def test_audit_increments_attempt_counter(self) -> None:
        """Each audit call should increment the attempt counter."""
        markdown = "Empty document"
        state = self._make_state(markdown=markdown, attempts=2)
        result = audit_compliance(state)

        assert result["audit_attempts"] == 3

    def test_audit_passes_with_last_name_reference(self) -> None:
        """Audit should accept last-name-only references to personnel."""
        markdown = (
            "# RFP for PRJ-001\n\n"
            "Meridian Continental Bank.\n"
            "Led by Vasquez and Chen.\n"
            "Budget: $12,500,000. Basel III."
        )
        state = self._make_state(markdown=markdown)
        result = audit_compliance(state)

        assert result["audit_passed"] is True


class TestWorkflowRouting:
    """Tests for the conditional routing logic in the graph."""

    def test_routing_returns_end_on_pass(self) -> None:
        """When audit passes, routing should send to END."""
        from src.workflow.graph import _should_redraft

        state = WorkflowState(
            audit_passed=True,
            audit_attempts=1,
        )
        result = _should_redraft(state)
        assert result == "__end__"

    def test_routing_returns_draft_on_fail_with_retries(self) -> None:
        """When audit fails and retries remain, route back to draft."""
        from src.workflow.graph import _should_redraft

        state = WorkflowState(
            audit_passed=False,
            audit_attempts=1,
        )
        result = _should_redraft(state)
        assert result == "draft_content"

    def test_routing_returns_end_when_retries_exhausted(self) -> None:
        """When max retries exhausted, route to END regardless of audit."""
        from src.workflow.graph import _should_redraft
        from config.settings import settings

        state = WorkflowState(
            audit_passed=False,
            audit_attempts=settings.MAX_AUDIT_RETRIES,
        )
        result = _should_redraft(state)
        assert result == "__end__"
