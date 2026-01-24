"""
Configuration management using Pydantic settings.
Loads configuration from environment variables.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class MoodleConfig(BaseSettings):
    """
    Configuration loaded from environment variables with MOODLE_ prefix.

    Supports DEV and PROD environments:
        MOODLE_DEV_URL / MOODLE_DEV_TOKEN - Development instance (default)
        MOODLE_PROD_URL / MOODLE_PROD_TOKEN - Production instance
        MOODLE_ENV - Set to 'prod' to use production, defaults to 'dev'

    Example .env file:
        MOODLE_DEV_URL=https://moodle-projects.wolfware.ncsu.edu
        MOODLE_DEV_TOKEN=your_dev_token
        MOODLE_PROD_URL=https://moodle-courses.wolfware.ncsu.edu
        MOODLE_PROD_TOKEN=your_prod_token
    """
    model_config = SettingsConfigDict(
        env_prefix='MOODLE_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

    # Environment selection (dev or prod)
    env: str = 'dev'

    # Development instance (default)
    dev_url: str
    dev_token: str

    # Production instance
    prod_url: str
    prod_token: str

    # Optional settings with defaults
    api_timeout: int = 30
    max_connections: int = 100
    max_keepalive_connections: int = 20
    max_response_chars: int = 50000

    # WRITE OPERATION SAFETY: Course ID whitelist for development
    # Write operations are ONLY allowed on these courses when in DEV mode
    # Can be overridden via MOODLE_DEV_COURSE_WHITELIST env var (comma-separated)
    dev_course_whitelist: str = "7299"  # Elizabeth's Moodle Playground

    # In PROD, write operations are DISABLED by default
    prod_allow_writes: bool = False

    @property
    def _parsed_dev_whitelist(self) -> list[int]:
        """Parse the dev_course_whitelist string into list of integers."""
        try:
            return [int(id.strip()) for id in self.dev_course_whitelist.split(',') if id.strip()]
        except (ValueError, AttributeError):
            # Fallback to default if parsing fails
            return [7299]

    @property
    def url(self) -> str:
        """Get URL based on environment (defaults to dev).

        SAFETY: Only the EXACT string 'prod' (lowercase, no whitespace) triggers production.
        Any other value (including 'PROD', 'Prod', 'production', etc.) uses development.
        """
        if self.env.lower().strip() == 'prod':
            return self.prod_url
        return self.dev_url

    @property
    def token(self) -> str:
        """Get token based on environment (defaults to dev).

        SAFETY: Only the EXACT string 'prod' (lowercase, no whitespace) triggers production.
        Any other value (including 'PROD', 'Prod', 'production', etc.) uses development.
        """
        if self.env.lower().strip() == 'prod':
            return self.prod_token
        return self.dev_token

    @property
    def environment_name(self) -> str:
        """Get human-readable environment name."""
        return "PRODUCTION" if self.env.lower().strip() == 'prod' else "DEVELOPMENT"

    @property
    def is_production(self) -> bool:
        """Returns True only if using production environment.

        SAFETY: Only the EXACT string 'prod' (after lowercase+strip) returns True.
        """
        return self.env.lower().strip() == 'prod'

    @property
    def is_development(self) -> bool:
        """Returns True if using development environment (default)."""
        return not self.is_production

    def can_write_to_course(self, course_id: int) -> bool:
        """Check if write operations are allowed for a specific course.

        SAFETY RULES:
        - DEV mode: Only courses in dev_course_whitelist (default: [7299])
        - PROD mode: Disabled unless prod_allow_writes=True (default: False)

        Args:
            course_id: The course ID to check

        Returns:
            True if writes are allowed, False otherwise
        """
        if self.is_production:
            # PROD: Writes disabled by default for safety
            return self.prod_allow_writes
        else:
            # DEV: Only whitelisted courses
            return course_id in self._parsed_dev_whitelist

    def get_write_restriction_message(self, course_id: int) -> str:
        """Get human-readable message explaining why write is blocked.

        Args:
            course_id: The course ID that was attempted

        Returns:
            Error message explaining the restriction
        """
        if self.is_production:
            return (
                f"Write operations are DISABLED in PRODUCTION mode.\n"
                f"Attempted: Course {course_id}\n"
                f"Safety: prod_allow_writes={self.prod_allow_writes}"
            )
        else:
            return (
                f"Write operations are only allowed on whitelisted courses in DEV mode.\n"
                f"Attempted: Course {course_id}\n"
                f"Allowed: {self._parsed_dev_whitelist}\n"
                f"To allow writes to this course, add it to MOODLE_DEV_COURSE_WHITELIST"
            )

# Singleton instance
_config: MoodleConfig | None = None

def get_config() -> MoodleConfig:
    """Get or create config singleton."""
    global _config
    if _config is None:
        _config = MoodleConfig()
    return _config
