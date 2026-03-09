"""
LangGraph state graph for the document generation pipeline.

Defines the cyclical workflow:
  extract_seed_data → generate_skeleton → draft_content → audit_compliance
                                           ↑                    ↓
                                           └── (if audit fails) ┘

If audit passes, the workflow terminates with the final Markdown.
If audit fails and max retries are exhausted, the last draft is used.
"""

from langgraph.graph import END, StateGraph

from config.settings import settings
from src.logger import setup_logger
from src.workflow.nodes import (
    audit_compliance,
    draft_content,
    extract_seed_data,
    generate_skeleton,
)
from src.workflow.state import WorkflowState

logger = setup_logger("workflow.graph")


def _should_redraft(state: WorkflowState) -> str:
    """
    Conditional edge: decide whether to loop back to drafting or finish.

    Returns 'draft_content' if the audit failed and retries remain,
    otherwise returns '__end__' to terminate the workflow.
    """
    if state.get("audit_passed", False):
        return END

    attempts = state.get("audit_attempts", 0)
    max_retries = settings.MAX_AUDIT_RETRIES

    if attempts < max_retries:
        logger.info(
            "Routing back to draft_content (attempt %d/%d)", attempts, max_retries
        )
        return "draft_content"

    # Max retries exhausted — accept the last draft with a warning
    logger.warning(
        "Max audit retries (%d) exhausted. Accepting last draft.", max_retries
    )
    return END


def build_document_graph() -> StateGraph:
    """
    Construct and compile the LangGraph state graph for document generation.

    The graph follows an Entity-First pipeline:
      1. Extract seed data from the database
      2. Generate a structured JSON skeleton (GPT-5.2 Pro)
      3. Draft long-form Markdown prose (Claude 3.7 Sonnet)
      4. Audit the draft against seed constraints
      5. Loop back to step 3 if audit fails (up to MAX_AUDIT_RETRIES)

    Returns:
        A compiled StateGraph ready to be invoked.
    """
    graph = StateGraph(WorkflowState)

    # --- Add nodes ---
    graph.add_node("extract_seed_data", extract_seed_data)
    graph.add_node("generate_skeleton", generate_skeleton)
    graph.add_node("draft_content", draft_content)
    graph.add_node("audit_compliance", audit_compliance)

    # --- Define edges ---
    # Linear flow: extract → skeleton → draft → audit
    graph.set_entry_point("extract_seed_data")
    graph.add_edge("extract_seed_data", "generate_skeleton")
    graph.add_edge("generate_skeleton", "draft_content")
    graph.add_edge("draft_content", "audit_compliance")

    # Conditional edge: audit → (draft_content | END)
    graph.add_conditional_edges(
        "audit_compliance",
        _should_redraft,
        {
            "draft_content": "draft_content",
            END: END,
        },
    )

    return graph.compile()


# Module-level compiled graph for reuse
document_graph = build_document_graph()
