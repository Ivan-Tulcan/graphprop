"""
Repository layer for seed entity CRUD operations.

Provides functions to insert and query seed entities from the SQLite
database, bridging between Pydantic domain models and SQLAlchemy rows.
"""

import json
from pathlib import Path

from sqlalchemy.orm import Session

from src.database.models import (
    BankProfileRow,
    BankRow,
    PersonnelRow,
    ProjectRow,
    RegulationRow,
    get_session,
)
from src.models.entities import (
    BankEntity,
    BankProfile,
    PersonnelEntity,
    ProjectEntity,
    RegulationEntity,
)


# ---------------------------------------------------------------------------
# INSERT helpers
# ---------------------------------------------------------------------------


def insert_bank(session: Session, bank: BankEntity) -> None:
    """Insert a BankEntity into the database."""
    session.merge(BankRow(
        bank_id=bank.bank_id,
        name=bank.name,
        country=bank.country,
        tier=bank.tier,
        total_assets_usd=bank.total_assets_usd,
        founded_year=bank.founded_year,
    ))


def insert_project(session: Session, project: ProjectEntity) -> None:
    """Insert a ProjectEntity into the database."""
    session.merge(ProjectRow(
        project_id=project.project_id,
        bank_id=project.bank_id,
        name=project.name,
        description=project.description,
        status=project.status.value,
        budget_usd=project.budget_usd,
        start_date=project.start_date,
        end_date=project.end_date,
        stakeholder_ids=json.dumps(project.stakeholder_ids),
    ))


def insert_personnel(session: Session, person: PersonnelEntity) -> None:
    """Insert a PersonnelEntity into the database."""
    session.merge(PersonnelRow(
        personnel_id=person.personnel_id,
        bank_id=person.bank_id,
        full_name=person.full_name,
        role=person.role.value,
        department=person.department,
        email=person.email,
        years_experience=person.years_experience,
    ))


def insert_regulation(session: Session, reg: RegulationEntity) -> None:
    """Insert a RegulationEntity into the database."""
    session.merge(RegulationRow(
        regulation_id=reg.regulation_id,
        code=reg.code,
        title=reg.title,
        issuing_body=reg.issuing_body,
        effective_date=reg.effective_date,
        summary=reg.summary,
        applicable_bank_ids=json.dumps(reg.applicable_bank_ids),
    ))


# ---------------------------------------------------------------------------
# QUERY helpers
# ---------------------------------------------------------------------------


def get_all_banks(session: Session) -> list[BankEntity]:
    """Return all banks as Pydantic models."""
    rows = session.query(BankRow).all()
    return [
        BankEntity(
            bank_id=r.bank_id,
            name=r.name,
            country=r.country,
            tier=r.tier,
            total_assets_usd=r.total_assets_usd,
            founded_year=r.founded_year,
        )
        for r in rows
    ]


def get_project_by_id(session: Session, project_id: str) -> ProjectEntity | None:
    """Return a single project by ID, or None if not found."""
    r = session.query(ProjectRow).filter_by(project_id=project_id).first()
    if r is None:
        return None
    return ProjectEntity(
        project_id=r.project_id,
        bank_id=r.bank_id,
        name=r.name,
        description=r.description,
        status=r.status,
        budget_usd=r.budget_usd,
        start_date=r.start_date,
        end_date=r.end_date,
        stakeholder_ids=json.loads(r.stakeholder_ids),
    )


def get_all_projects(session: Session) -> list[ProjectEntity]:
    """Return all projects as Pydantic models."""
    rows = session.query(ProjectRow).all()
    return [
        ProjectEntity(
            project_id=r.project_id,
            bank_id=r.bank_id,
            name=r.name,
            description=r.description,
            status=r.status,
            budget_usd=r.budget_usd,
            start_date=r.start_date,
            end_date=r.end_date,
            stakeholder_ids=json.loads(r.stakeholder_ids),
        )
        for r in rows
    ]


def get_personnel_by_ids(
    session: Session, personnel_ids: list[str]
) -> list[PersonnelEntity]:
    """Return personnel matching the given IDs."""
    rows = (
        session.query(PersonnelRow)
        .filter(PersonnelRow.personnel_id.in_(personnel_ids))
        .all()
    )
    return [
        PersonnelEntity(
            personnel_id=r.personnel_id,
            bank_id=r.bank_id,
            full_name=r.full_name,
            role=r.role,
            department=r.department,
            email=r.email,
            years_experience=r.years_experience,
        )
        for r in rows
    ]


def get_all_personnel(session: Session) -> list[PersonnelEntity]:
    """Return all personnel as Pydantic models."""
    rows = session.query(PersonnelRow).all()
    return [
        PersonnelEntity(
            personnel_id=r.personnel_id,
            bank_id=r.bank_id,
            full_name=r.full_name,
            role=r.role,
            department=r.department,
            email=r.email,
            years_experience=r.years_experience,
        )
        for r in rows
    ]


def get_bank_by_id(session: Session, bank_id: str) -> BankEntity | None:
    """Return a single bank by ID, or None if not found."""
    r = session.query(BankRow).filter_by(bank_id=bank_id).first()
    if r is None:
        return None
    return BankEntity(
        bank_id=r.bank_id,
        name=r.name,
        country=r.country,
        tier=r.tier,
        total_assets_usd=r.total_assets_usd,
        founded_year=r.founded_year,
    )


def get_regulations_for_bank(
    session: Session, bank_id: str
) -> list[RegulationEntity]:
    """Return all regulations applicable to a given bank."""
    rows = session.query(RegulationRow).all()
    results: list[RegulationEntity] = []
    for r in rows:
        applicable_ids = json.loads(r.applicable_bank_ids)
        if bank_id in applicable_ids:
            results.append(
                RegulationEntity(
                    regulation_id=r.regulation_id,
                    code=r.code,
                    title=r.title,
                    issuing_body=r.issuing_body,
                    effective_date=r.effective_date,
                    summary=r.summary,
                    applicable_bank_ids=applicable_ids,
                )
            )
    return results


def get_all_regulations(session: Session) -> list[RegulationEntity]:
    """Return all regulations as Pydantic models."""
    rows = session.query(RegulationRow).all()
    return [
        RegulationEntity(
            regulation_id=r.regulation_id,
            code=r.code,
            title=r.title,
            issuing_body=r.issuing_body,
            effective_date=r.effective_date,
            summary=r.summary,
            applicable_bank_ids=json.loads(r.applicable_bank_ids),
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Bank Profile (Source of Truth) helpers
# ---------------------------------------------------------------------------


def upsert_bank_profile(session: Session, profile: BankProfile) -> None:
    """Insert or update a BankProfile in the database."""
    session.merge(BankProfileRow(
        bank_id=profile.bank_id,
        profile_json=profile.model_dump_json(),
    ))


def get_bank_profile(session: Session, bank_id: str) -> BankProfile | None:
    """Return the BankProfile for a given bank, or None."""
    row = session.query(BankProfileRow).filter_by(bank_id=bank_id).first()
    if row is None:
        return None
    return BankProfile.model_validate_json(row.profile_json)


def delete_bank_profile(session: Session, bank_id: str) -> None:
    """Delete a bank profile by bank_id."""
    row = session.query(BankProfileRow).filter_by(bank_id=bank_id).first()
    if row:
        session.delete(row)
        session.commit()
