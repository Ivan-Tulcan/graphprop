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
