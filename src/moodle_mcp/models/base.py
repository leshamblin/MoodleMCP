"""
Base Pydantic models for Moodle entities.
"""

from pydantic import BaseModel, ConfigDict
from enum import Enum

class MoodleBaseModel(BaseModel):
    """
    Base model for all Moodle entities with common configuration.

    Configuration:
    - Allow extra fields from Moodle API (API may return more than we model)
    - Use field aliases for Moodle's naming conventions
    - Validate on assignment
    """
    model_config = ConfigDict(
        extra='allow',  # Allow extra fields from API
        populate_by_name=True,  # Accept both field name and alias
        validate_assignment=True,  # Validate when setting attributes
        str_strip_whitespace=True  # Auto-strip string whitespace
    )

class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"
