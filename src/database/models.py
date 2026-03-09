"""
SQLAlchemy ORM models and database engine setup.

Maps the Pydantic seed entities to relational tables in a local
SQLite database that acts as the single source of truth.
"""

import json
from datetime import date
from pathlib import Path

from sqlalchemy import (
    Column,
    Date,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.settings import settings


# ---------------------------------------------------------------------------
# SQLAlchemy Base & Engine
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_engine(db_path: Path | None = None):
    """Create a SQLAlchemy engine pointing to the seed SQLite database."""
    path = db_path or settings.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}", echo=False)


def get_session(db_path: Path | None = None) -> Session:
    """Return a new SQLAlchemy session."""
    engine = get_engine(db_path)
    return sessionmaker(bind=engine)()


# ---------------------------------------------------------------------------
# ORM Table Definitions
# ---------------------------------------------------------------------------


class BankRow(Base):
    __tablename__ = "banks"

    bank_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    country = Column(String, nullable=False)
    tier = Column(String, nullable=False)
    total_assets_usd = Column(Float, nullable=False)
    founded_year = Column(Integer, nullable=False)


class ProjectRow(Base):
    __tablename__ = "projects"

    project_id = Column(String, primary_key=True)
    bank_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, nullable=False)
    budget_usd = Column(Float, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    # Store stakeholder IDs as JSON array string
    stakeholder_ids = Column(Text, nullable=False, default="[]")


class PersonnelRow(Base):
    __tablename__ = "personnel"

    personnel_id = Column(String, primary_key=True)
    bank_id = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    department = Column(String, nullable=False)
    email = Column(String, nullable=False)
    years_experience = Column(Integer, nullable=False)


class RegulationRow(Base):
    __tablename__ = "regulations"

    regulation_id = Column(String, primary_key=True)
    code = Column(String, nullable=False)
    title = Column(String, nullable=False)
    issuing_body = Column(String, nullable=False)
    effective_date = Column(Date, nullable=False)
    summary = Column(Text, nullable=False)
    # Store applicable bank IDs as JSON array string
    applicable_bank_ids = Column(Text, nullable=False, default="[]")


# ---------------------------------------------------------------------------
# Helper: create all tables
# ---------------------------------------------------------------------------


def init_db(db_path: Path | None = None) -> None:
    """Create all tables in the database (idempotent)."""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
