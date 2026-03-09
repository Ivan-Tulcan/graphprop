"""
Document schema models for structured skeleton generation.

These Pydantic models define the JSON structure of each document type.
PydanticAI + GPT-5.2 Pro generates instances of these schemas which
are then expanded into full prose by Claude 3.7 Sonnet.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Common building blocks
# ---------------------------------------------------------------------------


class DocumentMetadata(BaseModel):
    """Metadata block present in every generated document."""
    document_id: str = Field(..., description="Unique document identifier")
    document_type: str = Field(..., description="Type of document (rfp, project_history, etc.)")
    project_id: str = Field(..., description="Associated project ID")
    bank_id: str = Field(..., description="Associated bank ID")
    title: str = Field(..., description="Document title")
    author_ids: list[str] = Field(default_factory=list, description="Personnel IDs who authored this")
    creation_date: str = Field(..., description="Document creation date (ISO format)")
    version: str = Field(default="1.0", description="Document version")


class SectionSkeleton(BaseModel):
    """A single section within the document skeleton."""
    section_number: str = Field(..., description="Section number (e.g. '1', '2.1', '3.2.1')")
    heading: str = Field(..., description="Section heading")
    key_points: list[str] = Field(
        default_factory=list,
        description="Key points this section must cover",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Factual constraints from seed data that the prose must respect",
    )
    word_count_target: int = Field(
        default=300,
        description="Target word count for this section",
    )


# ---------------------------------------------------------------------------
# RFP Skeleton
# ---------------------------------------------------------------------------


class RFPSkeleton(BaseModel):
    """JSON skeleton for a Request for Proposals document."""
    metadata: DocumentMetadata
    executive_summary_points: list[str] = Field(
        ..., description="Key points for the executive summary"
    )
    scope_of_work: list[SectionSkeleton] = Field(
        ..., description="Sections defining the scope of work"
    )
    technical_requirements: list[SectionSkeleton] = Field(
        ..., description="Technical requirement sections"
    )
    compliance_requirements: list[str] = Field(
        default_factory=list,
        description="Regulation codes this RFP must reference",
    )
    budget_constraints: dict[str, float] = Field(
        default_factory=dict,
        description="Budget breakdown constraints from seed data",
    )
    timeline_milestones: list[dict[str, str]] = Field(
        default_factory=list,
        description="Key milestones with target dates",
    )
    evaluation_criteria: list[str] = Field(
        default_factory=list,
        description="Criteria for vendor evaluation",
    )


# ---------------------------------------------------------------------------
# Project History Skeleton
# ---------------------------------------------------------------------------


class ProjectHistorySkeleton(BaseModel):
    """JSON skeleton for a Project History / Status Report."""
    metadata: DocumentMetadata
    project_overview_points: list[str] = Field(
        ..., description="Key points about the project"
    )
    phase_sections: list[SectionSkeleton] = Field(
        ..., description="Sections covering each project phase"
    )
    stakeholder_contributions: list[dict[str, str]] = Field(
        default_factory=list,
        description="Personnel ID to contribution summary mapping",
    )
    risks_and_mitigations: list[SectionSkeleton] = Field(
        default_factory=list,
        description="Risk analysis sections",
    )
    lessons_learned: list[str] = Field(
        default_factory=list,
        description="Key takeaways from the project",
    )


# ---------------------------------------------------------------------------
# Meeting Minutes Skeleton
# ---------------------------------------------------------------------------


class MeetingMinutesSkeleton(BaseModel):
    """JSON skeleton for Meeting Minutes."""
    metadata: DocumentMetadata
    meeting_date: str = Field(..., description="Date of the meeting (ISO format)")
    attendee_ids: list[str] = Field(
        ..., description="Personnel IDs of attendees"
    )
    agenda_items: list[SectionSkeleton] = Field(
        ..., description="Agenda items discussed"
    )
    action_items: list[dict[str, str]] = Field(
        default_factory=list,
        description="Action items with assignee personnel IDs and deadlines",
    )
    decisions_made: list[str] = Field(
        default_factory=list,
        description="Key decisions reached during the meeting",
    )


# ---------------------------------------------------------------------------
# Mapping: document type -> skeleton class
# ---------------------------------------------------------------------------

SKELETON_MAP: dict[str, type[BaseModel]] = {
    "rfp": RFPSkeleton,
    "project_history": ProjectHistorySkeleton,
    "meeting_minutes": MeetingMinutesSkeleton,
}
