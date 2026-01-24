"""
Completion tracking tools for Moodle MCP server.

This module provides both READ and WRITE operations for managing course and activity
completion status in Moodle. Completion tracking is essential for monitoring student
progress and managing course workflows.

Tools:
- moodle_get_activities_completion_status: Get completion status of activities (READ)
- moodle_get_course_completion_status: Get overall course completion status (READ)
- moodle_mark_course_self_completed: Student marks course as self-completed (WRITE)
- moodle_update_activity_completion_status_manually: Manually mark activity complete (WRITE)
"""

from pydantic import Field
from fastmcp import Context

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors, require_write_permission
from ..utils.api_helpers import get_moodle_client
from ..utils.formatting import format_response
from ..models.base import ResponseFormat


# ============================================================================
# READ OPERATIONS
# ============================================================================


@mcp.tool(
    name="moodle_get_activities_completion_status",
    description="Get completion status for all activities in a course for a specific user. REQUIRED: course_id (integer), user_id (integer). Example: course_id=7299, user_id=123. Returns list of activities with their completion status.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_activities_completion_status(
    course_id: int = Field(description="Course ID", gt=0),
    user_id: int = Field(description="User ID (0 = current user)", ge=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format (markdown or json)"),
    ctx: Context = None
) -> str:
    """
    Get completion status of all activities in a course for a specific user.

    Returns detailed completion information including:
    - Activity ID, name, and type
    - Completion state (0=incomplete, 1=complete, 2=complete with pass, 3=complete with fail)
    - Tracking method (0=none, 1=manual, 2=automatic)
    - Timestamps for completion

    Args:
        course_id: The course ID to check
        user_id: The user ID (0 for current user)
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Formatted completion status information
    """
    moodle = get_moodle_client(ctx)

    # Prepare parameters
    params = {
        'courseid': course_id,
        'userid': user_id
    }

    # Make request
    result = await moodle._make_request(
        'core_completion_get_activities_completion_status',
        params
    )

    return format_response(result, "Activity Completion Status", format)


@mcp.tool(
    name="moodle_get_course_completion_status",
    description="Get overall course completion status for a specific user. REQUIRED: course_id (integer), user_id (integer). Example: course_id=7299, user_id=123. Returns course completion criteria and overall status.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_course_completion_status(
    course_id: int = Field(description="Course ID", gt=0),
    user_id: int = Field(description="User ID (0 = current user)", ge=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format (markdown or json)"),
    ctx: Context = None
) -> str:
    """
    Get overall course completion status for a specific user.

    Returns completion information including:
    - Completion criteria and their status
    - Overall completion state
    - Time completed (if applicable)

    Args:
        course_id: The course ID to check
        user_id: The user ID (0 for current user)
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Formatted course completion status
    """
    moodle = get_moodle_client(ctx)

    # Prepare parameters
    params = {
        'courseid': course_id,
        'userid': user_id
    }

    # Make request
    result = await moodle._make_request(
        'core_completion_get_course_completion_status',
        params
    )

    return format_response(result, "Course Completion Status", format)


# ============================================================================
# WRITE OPERATIONS
# ============================================================================


@mcp.tool(
    name="moodle_mark_course_self_completed",
    description="Mark a course as self-completed by the current user. REQUIRED: course_id (integer). Example: course_id=7299. WRITE OPERATION - only works on whitelisted courses (default: course 7299). Used when students want to mark the course as completed on their own.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,  # Safe to call multiple times
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_mark_course_self_completed(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format (markdown or json)"),
    ctx: Context = None
) -> str:
    """
    Mark a course as self-completed.

    This allows students to mark a course as completed when the course allows
    self-completion. This is typically used for courses that don't have automatic
    completion criteria but allow students to manually mark completion.

    SAFETY:
    - Only works on whitelisted courses (default: 7299)
    - Non-destructive operation (can be reversed by resetting completion)
    - Idempotent (safe to call multiple times)

    Args:
        course_id: The course ID (must be whitelisted)
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Success confirmation message
    """
    moodle = get_moodle_client(ctx)

    # Prepare parameters
    params = {
        'courseid': course_id
    }

    # Make request
    result = await moodle._make_request(
        'core_completion_mark_course_self_completed',
        params
    )

    return format_response(result, "Course Marked as Self-Completed", format)


@mcp.tool(
    name="moodle_update_activity_completion_status_manually",
    description="Manually update completion status for an activity. REQUIRED: course_id (integer), cm_id (integer, course module ID), completed (boolean). Example: course_id=7299, cm_id=456, completed=true. WRITE OPERATION - only works on whitelisted courses. Used by teachers to manually override activity completion.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,  # Safe to call multiple times with same status
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_update_activity_completion_status_manually(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    cm_id: int = Field(description="Course module ID (activity ID)", gt=0),
    completed: bool = Field(description="Completion status: true = complete, false = incomplete"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format (markdown or json)"),
    ctx: Context = None
) -> str:
    """
    Manually update the completion status of an activity.

    This allows teachers (or users with appropriate permissions) to manually
    mark an activity as complete or incomplete. This is useful for activities
    with manual completion tracking or when overriding automatic completion.

    SAFETY:
    - Only works on whitelisted courses (default: 7299)
    - Non-destructive operation (completion status can be toggled)
    - Idempotent (safe to call multiple times with same status)
    - Only works for activities with manual completion tracking enabled

    Args:
        course_id: The course ID (must be whitelisted)
        cm_id: The course module ID (activity ID)
        completed: True to mark as complete, False to mark as incomplete
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Success confirmation message
    """
    moodle = get_moodle_client(ctx)

    # Prepare parameters
    params = {
        'cmid': cm_id,
        'completed': 1 if completed else 0
    }

    # Make request
    result = await moodle._make_request(
        'core_completion_update_activity_completion_status_manually',
        params
    )

    return format_response(result, "Activity Completion Status Updated", format)
