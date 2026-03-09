"""
Logging configuration for the Synthetic Document Factory.

Provides a structured logger with console output and optional file output.
"""

import logging
import sys
from pathlib import Path


def setup_logger(
    name: str = "sdf",
    level: str | None = None,
    log_file: Path | None = None,
) -> logging.Logger:
    """
    Configure and return a named logger.

    Args:
        name: Logger name (default: 'sdf' for Synthetic Document Factory).
        level: Logging level string. Falls back to settings if None.
        log_file: Optional path to write log output to a file.

    Returns:
        Configured logging.Logger instance.
    """
    # Import here to avoid circular dependency at module load time
    from config.settings import settings

    log_level = level or settings.LOG_LEVEL

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Avoid adding duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Optional file handler
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Convenience: module-level default logger
logger = setup_logger()
