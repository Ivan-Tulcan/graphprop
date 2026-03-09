"""
Unit tests for the seed database repository layer.

Tests insert and query operations against an in-memory SQLite database.
"""

import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.database.models import init_db, get_session
from src.database.repository import (
    get_all_banks,
    get_bank_by_id,
    get_project_by_id,
    get_all_personnel,
    get_regulations_for_bank,
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


@pytest.fixture
def db_session(tmp_path: Path):
    """Create a temporary SQLite database and return a session."""
    db_path = tmp_path / "test_seed.db"
    init_db(db_path)
    session = get_session(db_path)
    yield session
    session.close()


class TestDatabaseOperations:
    """Tests for seed database CRUD operations."""

    def test_insert_and_retrieve_bank(self, db_session) -> None:
        """Should insert a bank and retrieve it by ID."""
        bank = BankEntity(
            bank_id="BNK-T01",
            name="Test Bank",
            country="Canada",
            tier="Tier 1",
            total_assets_usd=200.0,
            founded_year=2000,
        )
        insert_bank(db_session, bank)
        db_session.commit()

        result = get_bank_by_id(db_session, "BNK-T01")
        assert result is not None
        assert result.name == "Test Bank"
        assert result.country == "Canada"

    def test_get_all_banks(self, db_session) -> None:
        """Should return all inserted banks."""
        for i in range(3):
            insert_bank(db_session, BankEntity(
                bank_id=f"BNK-M{i}",
                name=f"Multi Bank {i}",
                country="US",
                tier="Tier 2",
                total_assets_usd=50.0,
                founded_year=2020,
            ))
        db_session.commit()

        banks = get_all_banks(db_session)
        assert len(banks) == 3

    def test_insert_and_retrieve_project(self, db_session) -> None:
        """Should insert a project and retrieve it with stakeholder IDs."""
        project = ProjectEntity(
            project_id="PRJ-T01",
            bank_id="BNK-001",
            name="Test Project",
            description="Testing database operations",
            status=ProjectStatus.PLANNING,
            budget_usd=1_000_000.0,
            start_date=date(2025, 1, 1),
            stakeholder_ids=["PER-001", "PER-002"],
        )
        insert_project(db_session, project)
        db_session.commit()

        result = get_project_by_id(db_session, "PRJ-T01")
        assert result is not None
        assert result.name == "Test Project"
        assert result.stakeholder_ids == ["PER-001", "PER-002"]

    def test_get_nonexistent_project_returns_none(self, db_session) -> None:
        """Querying a non-existent project should return None."""
        result = get_project_by_id(db_session, "PRJ-NOPE")
        assert result is None

    def test_regulations_filtered_by_bank(self, db_session) -> None:
        """Should only return regulations applicable to the queried bank."""
        reg1 = RegulationEntity(
            regulation_id="REG-T01",
            code="Test-A",
            title="Reg A",
            issuing_body="Auth A",
            effective_date=date(2020, 1, 1),
            summary="Test A",
            applicable_bank_ids=["BNK-001"],
        )
        reg2 = RegulationEntity(
            regulation_id="REG-T02",
            code="Test-B",
            title="Reg B",
            issuing_body="Auth B",
            effective_date=date(2021, 1, 1),
            summary="Test B",
            applicable_bank_ids=["BNK-002"],
        )
        insert_regulation(db_session, reg1)
        insert_regulation(db_session, reg2)
        db_session.commit()

        regs_for_bnk1 = get_regulations_for_bank(db_session, "BNK-001")
        assert len(regs_for_bnk1) == 1
        assert regs_for_bnk1[0].code == "Test-A"

        regs_for_bnk3 = get_regulations_for_bank(db_session, "BNK-003")
        assert len(regs_for_bnk3) == 0
