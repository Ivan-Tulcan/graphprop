"""
Unit tests for Pydantic domain models.

Validates that seed entity models enforce correct types, required
fields, and enum constraints.
"""

from datetime import date

import pytest

from src.models.entities import (
    BankEntity,
    PersonnelEntity,
    PersonnelRole,
    ProjectEntity,
    ProjectStatus,
    RegulationEntity,
)


class TestBankEntity:
    """Tests for the BankEntity Pydantic model."""

    def test_valid_bank_creation(self) -> None:
        """A bank with all required fields should be created successfully."""
        bank = BankEntity(
            bank_id="BNK-TEST",
            name="Test Bank International",
            country="Germany",
            tier="Tier 1",
            total_assets_usd=150.0,
            founded_year=1995,
        )
        assert bank.bank_id == "BNK-TEST"
        assert bank.total_assets_usd == 150.0

    def test_bank_missing_required_field_raises(self) -> None:
        """Missing a required field should raise ValidationError."""
        with pytest.raises(Exception):
            BankEntity(
                bank_id="BNK-BAD",
                name="Incomplete Bank",
                # Missing: country, tier, total_assets_usd, founded_year
            )

    def test_bank_serialization_roundtrip(self) -> None:
        """Model should serialize to dict and back without data loss."""
        bank = BankEntity(
            bank_id="BNK-RT",
            name="Roundtrip Bank",
            country="Japan",
            tier="Tier 2",
            total_assets_usd=42.5,
            founded_year=2010,
        )
        data = bank.model_dump()
        restored = BankEntity.model_validate(data)
        assert restored == bank


class TestProjectEntity:
    """Tests for the ProjectEntity Pydantic model."""

    def test_valid_project_creation(self) -> None:
        """A project with all fields should be created and enums resolved."""
        project = ProjectEntity(
            project_id="PRJ-TEST",
            bank_id="BNK-001",
            name="Test Project",
            description="A test banking project.",
            status=ProjectStatus.IN_PROGRESS,
            budget_usd=5_000_000.0,
            start_date=date(2025, 1, 1),
            end_date=date(2026, 12, 31),
            stakeholder_ids=["PER-001", "PER-002"],
        )
        assert project.status == ProjectStatus.IN_PROGRESS
        assert len(project.stakeholder_ids) == 2

    def test_project_status_from_string(self) -> None:
        """ProjectStatus enum should accept valid string values."""
        project = ProjectEntity(
            project_id="PRJ-STR",
            bank_id="BNK-001",
            name="String Status",
            description="Test",
            status="planning",
            budget_usd=100.0,
            start_date=date(2025, 6, 1),
        )
        assert project.status == ProjectStatus.PLANNING

    def test_project_optional_end_date(self) -> None:
        """end_date should default to None when not provided."""
        project = ProjectEntity(
            project_id="PRJ-OPT",
            bank_id="BNK-002",
            name="No End Date",
            description="Open-ended project",
            status=ProjectStatus.IN_PROGRESS,
            budget_usd=200.0,
            start_date=date(2025, 3, 1),
        )
        assert project.end_date is None

    def test_project_default_stakeholders(self) -> None:
        """stakeholder_ids should default to empty list."""
        project = ProjectEntity(
            project_id="PRJ-DEF",
            bank_id="BNK-001",
            name="No Stakeholders",
            description="Test",
            status=ProjectStatus.PLANNING,
            budget_usd=100.0,
            start_date=date(2025, 1, 1),
        )
        assert project.stakeholder_ids == []


class TestPersonnelEntity:
    """Tests for the PersonnelEntity Pydantic model."""

    def test_valid_personnel_creation(self) -> None:
        """Personnel with all fields and valid role enum should work."""
        person = PersonnelEntity(
            personnel_id="PER-TEST",
            bank_id="BNK-001",
            full_name="Jane Doe",
            role=PersonnelRole.ARCHITECT,
            department="Engineering",
            email="jane.doe@test.com",
            years_experience=12,
        )
        assert person.role == PersonnelRole.ARCHITECT

    def test_invalid_role_raises(self) -> None:
        """An invalid role string should raise a validation error."""
        with pytest.raises(Exception):
            PersonnelEntity(
                personnel_id="PER-BAD",
                bank_id="BNK-001",
                full_name="Bad Role",
                role="janitor",  # Not a valid PersonnelRole
                department="Facilities",
                email="bad@test.com",
                years_experience=5,
            )


class TestRegulationEntity:
    """Tests for the RegulationEntity Pydantic model."""

    def test_valid_regulation_creation(self) -> None:
        """Regulation with all fields should be created properly."""
        reg = RegulationEntity(
            regulation_id="REG-TEST",
            code="Test-001",
            title="Test Regulation",
            issuing_body="Test Authority",
            effective_date=date(2020, 1, 1),
            summary="A test regulation for validation.",
            applicable_bank_ids=["BNK-001", "BNK-002"],
        )
        assert len(reg.applicable_bank_ids) == 2

    def test_regulation_default_applicable_banks(self) -> None:
        """applicable_bank_ids should default to empty list."""
        reg = RegulationEntity(
            regulation_id="REG-EMPTY",
            code="Empty",
            title="No Banks",
            issuing_body="None",
            effective_date=date(2023, 6, 1),
            summary="No banks",
        )
        assert reg.applicable_bank_ids == []
