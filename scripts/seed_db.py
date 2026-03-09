"""
Seed Database Population Script.

Populates the SQLite seed database with fictional banking entities:
  - 2 banks
  - 5 projects
  - 10 personnel
  - 3 regulations

Usage:
    python -m scripts.seed_db
"""

import sys
from datetime import date
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.database.models import init_db, get_session
from src.database.repository import (
    insert_bank,
    insert_personnel,
    insert_project,
    insert_regulation,
)
from src.models.entities import (
    BankEntity,
    PersonnelEntity,
    PersonnelRole,
    ProjectEntity,
    ProjectStatus,
    RegulationEntity,
)
from src.logger import setup_logger

logger = setup_logger("seeder")


# ---------------------------------------------------------------------------
# Fictional Seed Data
# ---------------------------------------------------------------------------

BANKS = [
    BankEntity(
        bank_id="BNK-001",
        name="Meridian Continental Bank",
        country="United States",
        tier="Tier 1",
        total_assets_usd=425.0,
        founded_year=1987,
    ),
    BankEntity(
        bank_id="BNK-002",
        name="Austral Pacific Financial Group",
        country="Australia",
        tier="Tier 2",
        total_assets_usd=98.5,
        founded_year=2003,
    ),
]

PERSONNEL = [
    # --- Meridian Continental Bank (BNK-001) ---
    PersonnelEntity(
        personnel_id="PER-001",
        bank_id="BNK-001",
        full_name="Dr. Elena Vasquez",
        role=PersonnelRole.CTO,
        department="Technology Division",
        email="e.vasquez@meridianbank.com",
        years_experience=22,
    ),
    PersonnelEntity(
        personnel_id="PER-002",
        bank_id="BNK-001",
        full_name="Marcus Chen",
        role=PersonnelRole.PROJECT_MANAGER,
        department="Digital Transformation Office",
        email="m.chen@meridianbank.com",
        years_experience=14,
    ),
    PersonnelEntity(
        personnel_id="PER-003",
        bank_id="BNK-001",
        full_name="Samira Patel",
        role=PersonnelRole.ARCHITECT,
        department="Enterprise Architecture",
        email="s.patel@meridianbank.com",
        years_experience=18,
    ),
    PersonnelEntity(
        personnel_id="PER-004",
        bank_id="BNK-001",
        full_name="James O'Brien",
        role=PersonnelRole.COMPLIANCE_OFFICER,
        department="Risk & Compliance",
        email="j.obrien@meridianbank.com",
        years_experience=16,
    ),
    PersonnelEntity(
        personnel_id="PER-005",
        bank_id="BNK-001",
        full_name="Aisha Rahman",
        role=PersonnelRole.DEVELOPER,
        department="Core Banking Platform",
        email="a.rahman@meridianbank.com",
        years_experience=8,
    ),
    PersonnelEntity(
        personnel_id="PER-006",
        bank_id="BNK-001",
        full_name="Viktor Novak",
        role=PersonnelRole.BUSINESS_ANALYST,
        department="Digital Transformation Office",
        email="v.novak@meridianbank.com",
        years_experience=11,
    ),
    # --- Austral Pacific Financial Group (BNK-002) ---
    PersonnelEntity(
        personnel_id="PER-007",
        bank_id="BNK-002",
        full_name="Catherine Whitfield",
        role=PersonnelRole.VP_TECHNOLOGY,
        department="IT Governance",
        email="c.whitfield@australpacific.com.au",
        years_experience=20,
    ),
    PersonnelEntity(
        personnel_id="PER-008",
        bank_id="BNK-002",
        full_name="Liam Torres",
        role=PersonnelRole.PROJECT_MANAGER,
        department="Strategic Initiatives",
        email="l.torres@australpacific.com.au",
        years_experience=9,
    ),
    PersonnelEntity(
        personnel_id="PER-009",
        bank_id="BNK-002",
        full_name="Mei-Lin Zhou",
        role=PersonnelRole.ARCHITECT,
        department="Cloud Infrastructure",
        email="m.zhou@australpacific.com.au",
        years_experience=15,
    ),
    PersonnelEntity(
        personnel_id="PER-010",
        bank_id="BNK-002",
        full_name="David Okonkwo",
        role=PersonnelRole.DIRECTOR,
        department="Regulatory Affairs",
        email="d.okonkwo@australpacific.com.au",
        years_experience=24,
    ),
]

PROJECTS = [
    ProjectEntity(
        project_id="PRJ-001",
        bank_id="BNK-001",
        name="Core Banking Platform Modernization",
        description=(
            "Migration of the legacy COBOL-based core banking system to a "
            "cloud-native microservices architecture on AWS, including real-time "
            "transaction processing capabilities and open-banking API layer."
        ),
        status=ProjectStatus.IN_PROGRESS,
        budget_usd=12_500_000.00,
        start_date=date(2025, 3, 1),
        end_date=date(2027, 6, 30),
        stakeholder_ids=["PER-001", "PER-002", "PER-003", "PER-005"],
    ),
    ProjectEntity(
        project_id="PRJ-002",
        bank_id="BNK-001",
        name="Anti-Money Laundering (AML) AI Engine",
        description=(
            "Development of a machine-learning-based AML detection engine "
            "integrated with the existing transaction monitoring platform. "
            "Must meet FinCEN and EU AMLD6 requirements."
        ),
        status=ProjectStatus.PLANNING,
        budget_usd=4_800_000.00,
        start_date=date(2025, 9, 1),
        end_date=date(2026, 12, 31),
        stakeholder_ids=["PER-001", "PER-004", "PER-006"],
    ),
    ProjectEntity(
        project_id="PRJ-003",
        bank_id="BNK-001",
        name="Customer Data Platform (CDP) Rollout",
        description=(
            "Enterprise-wide deployment of a unified customer data platform "
            "consolidating data from retail, commercial, and wealth management "
            "divisions for a 360-degree customer view."
        ),
        status=ProjectStatus.IN_PROGRESS,
        budget_usd=7_200_000.00,
        start_date=date(2025, 1, 15),
        end_date=date(2026, 7, 31),
        stakeholder_ids=["PER-002", "PER-003", "PER-006"],
    ),
    ProjectEntity(
        project_id="PRJ-004",
        bank_id="BNK-002",
        name="Cloud Migration & Hybrid Infrastructure",
        description=(
            "Phased migration of on-premises data-center workloads to a "
            "hybrid cloud model (Azure + on-prem), including disaster recovery "
            "site setup and network security re-architecture."
        ),
        status=ProjectStatus.IN_PROGRESS,
        budget_usd=9_100_000.00,
        start_date=date(2025, 6, 1),
        end_date=date(2027, 3, 31),
        stakeholder_ids=["PER-007", "PER-008", "PER-009"],
    ),
    ProjectEntity(
        project_id="PRJ-005",
        bank_id="BNK-002",
        name="Regulatory Reporting Automation",
        description=(
            "Automation of quarterly and annual regulatory reporting processes "
            "using RPA and NLP, targeting APRA prudential standards and "
            "Basel III capital adequacy calculations."
        ),
        status=ProjectStatus.PLANNING,
        budget_usd=3_400_000.00,
        start_date=date(2026, 1, 1),
        end_date=date(2027, 6, 30),
        stakeholder_ids=["PER-007", "PER-010", "PER-008"],
    ),
]

REGULATIONS = [
    RegulationEntity(
        regulation_id="REG-001",
        code="Basel III",
        title="Basel III: International Regulatory Framework for Banks",
        issuing_body="Basel Committee on Banking Supervision (BCBS)",
        effective_date=date(2023, 1, 1),
        summary=(
            "Comprehensive set of reform measures to strengthen the regulation, "
            "supervision, and risk management of the banking sector. Covers "
            "capital adequacy, stress testing, and market liquidity risk."
        ),
        applicable_bank_ids=["BNK-001", "BNK-002"],
    ),
    RegulationEntity(
        regulation_id="REG-002",
        code="AMLD6",
        title="6th Anti-Money Laundering Directive",
        issuing_body="European Union",
        effective_date=date(2021, 6, 3),
        summary=(
            "Directive harmonizing the definition of money laundering offences "
            "and sanctions across EU member states. Extends criminal liability "
            "to legal persons and establishes minimum penalties."
        ),
        applicable_bank_ids=["BNK-001"],
    ),
    RegulationEntity(
        regulation_id="REG-003",
        code="CPS 234",
        title="APRA Prudential Standard CPS 234 - Information Security",
        issuing_body="Australian Prudential Regulation Authority (APRA)",
        effective_date=date(2019, 7, 1),
        summary=(
            "Requires APRA-regulated entities to maintain an information "
            "security capability commensurate with the size and extent of "
            "threats to their information assets, including mandatory incident "
            "notification within 72 hours."
        ),
        applicable_bank_ids=["BNK-002"],
    ),
]


# ---------------------------------------------------------------------------
# Main seeder function
# ---------------------------------------------------------------------------


def seed_database() -> None:
    """Populate the seed database with all fictional entities."""
    logger.info("Initializing seed database...")
    init_db()

    session = get_session()
    try:
        # Banks
        for bank in BANKS:
            insert_bank(session, bank)
            logger.info("  Inserted bank: %s (%s)", bank.bank_id, bank.name)

        # Personnel
        for person in PERSONNEL:
            insert_personnel(session, person)
            logger.info(
                "  Inserted personnel: %s (%s)", person.personnel_id, person.full_name
            )

        # Projects
        for project in PROJECTS:
            insert_project(session, project)
            logger.info(
                "  Inserted project: %s (%s)", project.project_id, project.name
            )

        # Regulations
        for reg in REGULATIONS:
            insert_regulation(session, reg)
            logger.info(
                "  Inserted regulation: %s (%s)", reg.regulation_id, reg.code
            )

        session.commit()
        logger.info(
            "Seed database populated: %d banks, %d personnel, %d projects, %d regulations",
            len(BANKS),
            len(PERSONNEL),
            len(PROJECTS),
            len(REGULATIONS),
        )
    except Exception:
        session.rollback()
        logger.exception("Failed to seed database")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
