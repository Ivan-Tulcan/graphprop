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


class RFPParticipationEvent(BaseModel):
    event_name: str = Field(..., description="Name of the event (e.g., 'Entrega de propuestas', 'Defensas técnicas')")
    target_date: str = Field(..., description="Estimated date for the event")
    description: str = Field(..., description="Details about what is expected in this event")

class RFPSkeleton(BaseModel):
    """JSON skeleton for a Request for Proposals document."""
    metadata: DocumentMetadata
    executive_summary_points: list[str] = Field(
        ..., description="Key points for the executive summary"
    )
    objectives_and_constraints: list[str] = Field(
        ..., description="Clear business need, primary objectives, and constraints. Keep it high-level."
    )
    compliance_requirements: list[str] = Field(
        default_factory=list,
        description="Regulation codes this RFP must reference",
    )
    budget_range: str = Field(
        default="",
        description="Estimated budget range (e.g., 'USD 1.5M - 2.0M')",
    )
    participation_process: list[RFPParticipationEvent] = Field(
        ..., description="Detailed timeline of the RFP participation process (Q&A, submissions, defenses, selection, negotiations)"
    )
    evaluation_criteria: list[str] = Field(
        default_factory=list,
        description="Criteria for vendor evaluation",
    )


# ---------------------------------------------------------------------------
# Project History Skeleton
# ---------------------------------------------------------------------------

class ProjectMilestone(BaseModel):
    milestone_name: str = Field(..., description="Name of the milestone")
    main_tasks: list[str] = Field(..., description="Key tasks performed during this milestone")
    status: str = Field(..., description="Current status: 'Realizado', 'Atrasado', or 'A tiempo'")
    comment: str = Field(..., description="Complementary comment regarding the status and outcomes")

class ProjectHistorySkeleton(BaseModel):
    """JSON skeleton for a Project History / Status Report."""
    metadata: DocumentMetadata
    project_overview_points: list[str] = Field(
        ..., description="Key points about the project summary"
    )
    timeline_milestones: list[ProjectMilestone] = Field(
        ..., description="Chronological list of project milestones with status tracking"
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
# Technical Annex Skeleton
# ---------------------------------------------------------------------------


class ArchitectureDiagram(BaseModel):
    title: str = Field(..., description="Title of the architecture diagram")
    description: str = Field(..., description="Brief description of the AS-IS or TO-BE architecture")
    c4_plantuml_code: str = Field(..., description="C4-PlantUML code for the diagram. Must start with @startuml, include the appropriate C4 standard Library, define elements and relationships, and end with @enduml")


class TechnicalSubDocument(BaseModel):
    """A distinct technical document that will be generated as a separate PDF."""
    title: str = Field(..., description="Title of this specific annex document (e.g., 'Arquitectura AS-IS', 'Requisitos Funcionales', 'Dimensionamiento').")
    purpose: str = Field(..., description="Specific purpose of this document.")
    content_sections: list[SectionSkeleton] = Field(..., description="Detailed content sections for this specific document.")
    diagrams: list[ArchitectureDiagram] = Field(default_factory=list, description="Diagrams relevant to this specific document.")


class TechnicalAnnexSkeleton(BaseModel):
    """JSON skeleton for a collection of Technical Annexes."""
    metadata: DocumentMetadata
    sub_documents: list[TechnicalSubDocument] = Field(
        ...,
        description="List of separate technical documents (PDFs) to be generated. Examples: Architecture AS-IS, Architecture TO-BE, Requirements, Sizing, Security, etc."
    )
    references: list[str] = Field(
        default_factory=list,
        description="Standards, regulations, and internal documents referenced across all annexes.",
    )


# ---------------------------------------------------------------------------
# RFP Q&A Skeleton
# ---------------------------------------------------------------------------


class RFPQAItem(BaseModel):
    """A single question-and-answer entry in the RFP Q&A table."""
    question_number: str = Field(..., description="Sequential number, e.g. '1', '2'")
    category: str = Field(
        ...,
        description=(
            "Category of the question: Técnico, Legal, Financiero, Funcional, "
            "Proceso, Arquitectura, Seguridad, or Otro"
        ),
    )
    vendor_question: str = Field(
        ...,
        description="Question submitted by a competing vendor to clarify the RFP",
    )
    bank_answer: str = Field(
        ...,
        description="Official answer provided by the issuing bank",
    )
    answered_by: str = Field(
        default="",
        description="Full name or role of the bank representative who answered",
    )


class RFPQASkeleton(BaseModel):
    """JSON skeleton for an RFP Questions and Answers document."""
    metadata: DocumentMetadata
    rfp_reference: str = Field(
        ...,
        description="Title or ID of the RFP this Q&A document refers to",
    )
    submission_context: str = Field(
        ...,
        description=(
            "Brief context: purpose of the Q&A round, number of competing vendors, "
            "scope of the technology project, and timeline context"
        ),
    )
    qa_items: list[RFPQAItem] = Field(
        default_factory=list,
        description=(
            "List of 15-25 Q&A pairs covering technical, legal, financial, functional, "
            "and process aspects. Questions should reflect real vendor concerns about a "
            "banking technology procurement project."
        ),
    )
    clarification_notes: list[str] = Field(
        default_factory=list,
        description="General clarification notes that apply to the entire Q&A document",
    )
    response_deadline: str = Field(
        default="",
        description="Deadline for final proposal submission after Q&A is published (ISO date)",
    )


# ---------------------------------------------------------------------------
# Mapping: document type -> skeleton class
# ---------------------------------------------------------------------------

SKELETON_MAP: dict[str, type[BaseModel]] = {
    "rfp": RFPSkeleton,
    "project_history": ProjectHistorySkeleton,
    "meeting_minutes": MeetingMinutesSkeleton,
    "technical_annex": TechnicalAnnexSkeleton,
    "rfp_qa": RFPQASkeleton,
}
