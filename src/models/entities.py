"""
Pydantic domain models for seed entities.

These models represent the core banking-domain entities that form the
'source of truth' for all document generation. No LLM can invent an
entity that does not exist in the seed database.
"""

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ProjectStatus(str, Enum):
    """Lifecycle status of a banking project."""
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class DocumentType(str, Enum):
    """Types of documents the factory can generate."""
    RFP = "rfp"
    PROJECT_HISTORY = "project_history"
    MEETING_MINUTES = "meeting_minutes"
    TECHNICAL_ANNEX = "technical_annex"
    REGULATION_SUMMARY = "regulation_summary"


class PersonnelRole(str, Enum):
    """Job roles within banking entities."""
    CTO = "cto"
    PROJECT_MANAGER = "project_manager"
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    COMPLIANCE_OFFICER = "compliance_officer"
    BUSINESS_ANALYST = "business_analyst"
    VP_TECHNOLOGY = "vp_technology"
    DIRECTOR = "director"


# ---------------------------------------------------------------------------
# Seed Entity Models
# ---------------------------------------------------------------------------


class BankEntity(BaseModel):
    """
    A fictional banking institution.

    Serves as the top-level organizational entity to which projects,
    personnel, and regulatory requirements are attached.
    """
    bank_id: str = Field(..., description="Unique bank identifier, e.g. BNK-001")
    name: str = Field(..., description="Full legal name of the bank")
    country: str = Field(..., description="Country of incorporation")
    tier: str = Field(..., description="Bank tier classification (Tier 1, Tier 2, etc.)")
    total_assets_usd: float = Field(..., description="Total assets in USD (billions)")
    founded_year: int = Field(..., description="Year the bank was founded")


class ProjectEntity(BaseModel):
    """
    A banking technology or infrastructure project.

    Each project belongs to a bank and references personnel as stakeholders.
    """
    project_id: str = Field(..., description="Unique project identifier, e.g. PRJ-001")
    bank_id: str = Field(..., description="Foreign key to the parent bank")
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Brief project description")
    status: ProjectStatus = Field(..., description="Current project status")
    budget_usd: float = Field(..., description="Approved budget in USD")
    start_date: date = Field(..., description="Project start date")
    end_date: Optional[date] = Field(None, description="Target or actual end date")
    stakeholder_ids: list[str] = Field(
        default_factory=list,
        description="List of PersonnelEntity IDs involved in the project",
    )


class PersonnelEntity(BaseModel):
    """
    A fictional employee or contractor within a banking organization.

    Personnel are referenced as stakeholders across projects and documents.
    """
    personnel_id: str = Field(..., description="Unique personnel identifier, e.g. PER-001")
    bank_id: str = Field(..., description="Foreign key to the employing bank")
    full_name: str = Field(..., description="Full legal name")
    role: PersonnelRole = Field(..., description="Job role/title")
    department: str = Field(..., description="Department or division")
    email: str = Field(..., description="Corporate email address")
    years_experience: int = Field(..., description="Years of professional experience")


class RegulationEntity(BaseModel):
    """
    A banking regulation or compliance standard.

    These regulations constrain project requirements and appear as
    references in generated documents (RFPs, compliance reports).
    """
    regulation_id: str = Field(..., description="Unique regulation identifier, e.g. REG-001")
    code: str = Field(..., description="Official regulation code (e.g. Basel III)")
    title: str = Field(..., description="Full title of the regulation")
    issuing_body: str = Field(..., description="Regulatory body that issued it")
    effective_date: date = Field(..., description="Date the regulation took effect")
    summary: str = Field(..., description="Brief summary of the regulation's scope")
    applicable_bank_ids: list[str] = Field(
        default_factory=list,
        description="List of BankEntity IDs this regulation applies to",
    )


# ---------------------------------------------------------------------------
# Bank Profile — Source of Truth
# ---------------------------------------------------------------------------

class EvolutionEvent(BaseModel):
    """A single event in the bank's evolution history."""
    event_date: date = Field(..., description="Date of the event")
    category: str = Field(..., description="Category: canal, modernización, migración, servicio, adquisición, otro")
    title: str = Field(..., description="Short title of the event")
    description: str = Field(..., description="Detailed description of the event")


class BankProfile(BaseModel):
    """
    Comprehensive 'Source of Truth' for a bank.

    Stores structured knowledge about the bank that is used as context
    during document generation.  Every bank follows this same schema.
    """
    bank_id: str = Field(..., description="FK to BankEntity")

    # --- Strategy & Vision ---
    mission: str = Field(default="", description="Mission statement")
    vision: str = Field(default="", description="Vision statement")
    strategic_objectives: list[str] = Field(default_factory=list, description="Key strategic objectives")
    competitive_advantages: list[str] = Field(default_factory=list, description="Core competitive advantages")

    # --- Business Processes ---
    core_processes: list[str] = Field(default_factory=list, description="Core banking processes (e.g. lending, deposits, payments)")
    support_processes: list[str] = Field(default_factory=list, description="Support processes (HR, legal, compliance, etc.)")

    # --- Technology Stack ---
    core_banking_system: str = Field(default="", description="Core banking platform (e.g. Temenos T24, Finacle)")
    programming_languages: list[str] = Field(default_factory=list, description="Primary programming languages")
    databases: list[str] = Field(default_factory=list, description="Database technologies")
    cloud_providers: list[str] = Field(default_factory=list, description="Cloud providers (AWS, Azure, GCP...)")
    devops_tools: list[str] = Field(default_factory=list, description="CI/CD and DevOps tooling")
    integration_middleware: list[str] = Field(default_factory=list, description="ESB, API gateways, messaging")
    security_stack: list[str] = Field(default_factory=list, description="Security tools and frameworks")

    # --- Enterprise Architecture ---
    architecture_style: str = Field(default="", description="Dominant architecture style (monolithic, SOA, microservices, hybrid)")
    architecture_layers: list[str] = Field(default_factory=list, description="Architecture layers description")
    key_systems: list[str] = Field(default_factory=list, description="Key internal systems and platforms")
    external_integrations: list[str] = Field(default_factory=list, description="External systems and partners")

    # --- Technology Ecosystem ---
    data_platform: str = Field(default="", description="Data platform / data lake description")
    analytics_tools: list[str] = Field(default_factory=list, description="BI and analytics tools")
    ai_ml_capabilities: list[str] = Field(default_factory=list, description="AI/ML capabilities in use")

    # --- Channels ---
    digital_channels: list[str] = Field(default_factory=list, description="Digital channels (mobile app, web, chatbot...)")
    physical_channels: list[str] = Field(default_factory=list, description="Physical channels (branches, ATMs, kiosks...)")
    partner_channels: list[str] = Field(default_factory=list, description="Partner/third-party channels")

    # --- Organizational ---
    org_structure_notes: str = Field(default="", description="Notes on organizational structure")
    key_departments: list[str] = Field(default_factory=list, description="Key departments/divisions")

    # --- Evolution History ---
    evolution_history: list[EvolutionEvent] = Field(
        default_factory=list,
        description="Chronological history of major changes, migrations, new channels, modernization projects",
    )

    # --- Free-form additional context ---
    additional_context: str = Field(default="", description="Any additional unstructured notes")
