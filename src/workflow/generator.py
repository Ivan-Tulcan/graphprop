"""
DocumentGenerator: high-level orchestrator for the generation pipeline.

Provides a clean interface to trigger the LangGraph workflow and
collect the resulting Markdown and metadata.
"""

from typing import Any

from src.logger import setup_logger
from src.workflow.graph import build_document_graph
from src.workflow.state import WorkflowState

logger = setup_logger("workflow.generator")


class DocumentGenerator:
    """
    High-level document generation orchestrator.

    Usage:
        generator = DocumentGenerator()
        result = generator.generate(project_id="PRJ-001", doc_type="rfp")
        print(result["final_markdown"])
    """

    def __init__(self) -> None:
        self.graph = build_document_graph()

    def generate(
        self,
        project_id: str,
        doc_type: str,
    ) -> dict[str, Any]:
        """
        Run the full document generation pipeline for a single document.

        Args:
            project_id: The seed project ID (e.g. 'PRJ-001').
            doc_type: Document type ('rfp', 'project_history', 'meeting_minutes').

        Returns:
            Final workflow state dict containing 'final_markdown',
            'skeleton', 'token_usage', etc.
        """
        logger.info(
            "Starting document generation | project=%s type=%s",
            project_id, doc_type,
        )

        initial_state: WorkflowState = {
            "project_id": project_id,
            "doc_type": doc_type,
            "audit_attempts": 0,
            "audit_issues": [],
        }

        # Run the compiled LangGraph
        final_state = self.graph.invoke(initial_state)

        # If audit never fully passed but retries exhausted, use last markdown.
        # Also handle edge cases where final_markdown exists but is None/empty.
        final_markdown = final_state.get("final_markdown")
        if (not final_markdown) and ("markdown" in final_state):
            logger.warning("Using unaudited draft as final output.")
            final_state["final_markdown"] = final_state["markdown"]

        logger.info(
            "Document generation complete | project=%s type=%s tokens=%s",
            project_id,
            doc_type,
            final_state.get("token_usage", {}),
        )

        return final_state
