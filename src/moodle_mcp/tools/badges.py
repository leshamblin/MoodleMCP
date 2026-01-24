"""
Badge tools for Moodle MCP server.

This module provides READ-only operations for viewing and managing badges in Moodle.
Badges are digital credentials that can be awarded to users for achievements and
completion of learning objectives.

Tools:
- moodle_get_user_badges: Get badges earned by a user (READ)
- moodle_get_user_badge_by_hash: Get specific badge details by unique hash (READ)
"""

from pydantic import Field
from fastmcp import Context

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors
from ..utils.api_helpers import get_moodle_client
from ..utils.formatting import format_response
from ..models.base import ResponseFormat


# ============================================================================
# READ OPERATIONS
# ============================================================================


@mcp.tool(
    name="moodle_get_user_badges",
    description="Get all badges earned by a user. REQUIRED: user_id (integer, 0=current user). Optional: course_id (integer, filter by course). Example: user_id=123, course_id=7299. Returns list of earned badges with details.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_user_badges(
    user_id: int = Field(default=0, description="User ID (0 = current user)", ge=0),
    course_id: int = Field(default=0, description="Course ID to filter badges (0 = all)", ge=0),
    page: int = Field(default=0, description="Page number for pagination", ge=0),
    per_page: int = Field(default=0, description="Badges per page (0 = all)", ge=0),
    search: str = Field(default="", description="Search string to filter badges"),
    only_public: bool = Field(default=False, description="Only return badges visible to others"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format (markdown or json)"),
    ctx: Context = None
) -> str:
    """
    Get all badges earned by a specific user.

    Returns detailed information about badges including:
    - Badge ID, name, and description
    - Issue date and expiry date (if applicable)
    - Badge criteria and issuer information
    - Badge image URL
    - Whether badge is visible to others

    Args:
        user_id: The user ID (0 for current user)
        course_id: Filter by course ID (0 for all courses)
        page: Page number for pagination (0-based)
        per_page: Number of badges per page (0 for all)
        search: Search string to filter badges by name
        only_public: Only return badges visible to others
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Formatted badge information
    """
    moodle = get_moodle_client(ctx)

    # Prepare parameters
    params = {
        'userid': user_id
    }

    if course_id > 0:
        params['courseid'] = course_id

    if page > 0:
        params['page'] = page

    if per_page > 0:
        params['perpage'] = per_page

    if search:
        params['search'] = search

    if only_public:
        params['onlypublic'] = 1

    # Make request
    result = await moodle._make_request(
        'core_badges_get_user_badges',
        params
    )

    return format_response(result, "User Badges", format)


@mcp.tool(
    name="moodle_get_user_badge_by_hash",
    description="Get detailed information about a specific badge using its unique hash. REQUIRED: hash (string, unique badge identifier). Example: hash='abc123def456'. Returns detailed badge information including criteria and issuer.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_user_badge_by_hash(
    hash: str = Field(description="Unique badge hash identifier", min_length=1),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format (markdown or json)"),
    ctx: Context = None
) -> str:
    """
    Get detailed information about a specific badge by its unique hash.

    Each badge has a unique hash identifier that can be used to retrieve its
    detailed information. This is useful for verifying badge authenticity or
    viewing badge details from a badge URL.

    Returns information including:
    - Badge ID, name, and description
    - Badge criteria and requirements
    - Issuer information
    - Badge image and URL
    - Issue and expiry dates
    - Endorsement information (if applicable)
    - Related badges (if any)

    Args:
        hash: The unique badge hash identifier
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Formatted badge information
    """
    moodle = get_moodle_client(ctx)

    # Prepare parameters
    params = {
        'hash': hash
    }

    # Make request
    result = await moodle._make_request(
        'core_badges_get_user_badge_by_hash',
        params
    )

    return format_response(result, "Badge Details", format)
