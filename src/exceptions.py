"""
Custom exception classes for the Synthetic Document Factory.

Provides a hierarchy of domain-specific exceptions for clear error
reporting across the generation pipeline.
"""


class SDFError(Exception):
    """Base exception for all Synthetic Document Factory errors."""


class DatabaseError(SDFError):
    """Raised when a database operation fails."""


class SeedDataError(SDFError):
    """Raised when seed data is missing or malformed."""


class LLMClientError(SDFError):
    """Raised when an LLM API call fails after retries."""


class SchemaValidationError(SDFError):
    """Raised when a generated document skeleton fails Pydantic validation."""


class AuditFailureError(SDFError):
    """Raised when a document draft fails compliance auditing."""


class RenderingError(SDFError):
    """Raised when the PDF rendering pipeline fails."""
