"""
LangGraph workflow state definition.

Defines the TypedDict that flows through all nodes of the
document generation graph: extract → generate → draft → audit → (loop).
"""

from typing import Any, TypedDict


class WorkflowState(TypedDict, total=False):
    """
    State object that travels through the LangGraph document pipeline.

    Fields are populated progressively as the workflow advances
    through each node.
    """
    # --- Input parameters ---
    project_id: str
    doc_type: str  # 'rfp', 'project_history', 'meeting_minutes'

    # --- Seed data (populated by extract_seed_data) ---
    project: dict[str, Any]
    bank: dict[str, Any]
    personnel: list[dict[str, Any]]
    regulations: list[dict[str, Any]]

    # --- Schema skeleton (populated by generate_skeleton) ---
    skeleton: dict[str, Any]

    # --- Draft content (populated by draft_content) ---
    markdown: str

    # --- Audit results (populated by audit_compliance) ---
    audit_passed: bool
    audit_issues: list[str]
    audit_attempts: int

    # --- Final output ---
    final_markdown: str
    token_usage: dict[str, int]
