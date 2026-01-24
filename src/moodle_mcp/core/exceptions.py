"""
Custom exception hierarchy for Moodle MCP server.
"""

class MoodleException(Exception):
    """Base exception for all Moodle-related errors."""
    pass

class MoodleAPIError(MoodleException):
    """Moodle API returned an error response."""
    pass

class MoodleAuthError(MoodleAPIError):
    """Authentication/authorization failed."""
    pass

class MoodleConnectionError(MoodleException):
    """Network/connection error."""
    pass

class MoodleValidationError(MoodleException):
    """Input validation failed."""
    pass

class MoodleNotFoundError(MoodleAPIError):
    """Requested resource not found."""
    pass

class MoodlePermissionError(MoodleAPIError):
    """User lacks permission for operation."""
    pass
