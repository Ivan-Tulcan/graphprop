"""
Application configuration module.

Loads environment variables and provides centralized settings
for the Synthetic Document Factory.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class Settings:
    """Centralized application settings loaded from environment variables."""

    # --- API Keys (never hardcoded) ---
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # --- Model identifiers ---
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5-20250929"
    OPENAI_MODEL: str = "gpt-4o"

    # --- Paths ---
    PROJECT_ROOT: Path = _PROJECT_ROOT
    DATA_DIR: Path = _PROJECT_ROOT / "data"
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", str(_PROJECT_ROOT / "output")))
    DB_PATH: Path = DATA_DIR / "seed.db"

    # --- Logging ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # --- Generation defaults ---
    MAX_AUDIT_RETRIES: int = 3
    DEFAULT_DOC_COUNT: int = 1


settings = Settings()
