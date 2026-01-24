"""
Assignment tools - READ and WRITE operations for assignments and submissions.
"""

from pydantic import Field
from fastmcp import Context

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors, require_write_permission
from ..utils.api_helpers import get_moodle_client, resolve_user_id
from ..utils.formatting import format_response
from ..utils.assignment_helpers import (
    find_assignment_by_id,
    get_assignments_for_user,
    get_assignments_for_course
)
from ..models.base import ResponseFormat

# ============================================================================
# READ OPERATIONS
# ============================================================================

@mcp.tool(
    name="moodle_list_assignments",
    description="Get all assignments in a course. REQUIRED: course_id (integer). Example: course_id=2292. Returns assignment IDs. Use moodle_list_user_courses to get course_id.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_list_assignments(
    course_id: int = Field(description="Course ID", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get list of all assignments in a course.

    Returns assignment details including name, due dates, and settings.

    Args:
        course_id: Course ID
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of assignments in the course

    Example use cases:
        - "What assignments are in course 42?"
        - "List all assignments for course 15"
        - "Show homework in course 8"
    """
    moodle = get_moodle_client(ctx)

    # Get assignments for course using helper
    assignments = await get_assignments_for_course(moodle, course_id)

    if not assignments:
        return f"No assignments found in course {course_id}."

    return format_response(assignments, f"Assignments in Course {course_id}", format)

@mcp.tool(
    name="moodle_get_assignment_details",
    description="Get detailed information about an assignment including description, due date, and submission settings. REQUIRED: assignment_id (integer). Example: assignment_id=123. Use moodle_list_assignments to get assignment_id.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_assignment_details(
    assignment_id: int = Field(description="Assignment ID", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get comprehensive details for a specific assignment.

    Returns assignment description, due dates, submission settings, and grading information.

    Args:
        assignment_id: Assignment ID
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Detailed assignment information

    Example use cases:
        - "Show details for assignment 123"
        - "What is assignment 45 about?"
        - "Get due date for assignment 67"
    """
    moodle = get_moodle_client(ctx)

    # Search for the assignment using helper
    assignment = await find_assignment_by_id(moodle, assignment_id)

    if assignment:
        return format_response(assignment, f"Assignment: {assignment.get('name')}", format)

    return f"Assignment {assignment_id} not found in your enrolled courses."

@mcp.tool(
    name="moodle_get_assignment_submissions",
    description="Get all submissions for an assignment (requires teacher/grader permissions). REQUIRED: assignment_id (integer). Example: assignment_id=123. Use moodle_list_assignments to get assignment_id.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_assignment_submissions(
    assignment_id: int = Field(description="Assignment ID", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get list of submissions for an assignment.

    Shows submission status for all students (requires teacher/admin permissions).

    Args:
        assignment_id: Assignment ID
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of assignment submissions

    Example use cases:
        - "Show submissions for assignment 123"
        - "Who submitted assignment 45?"
        - "Get submission status for assignment 67"
    """
    moodle = get_moodle_client(ctx)

    # Get submissions
    try:
        submissions_data = await moodle._make_request(
            'mod_assign_get_submissions',
            {'assignmentids[0]': assignment_id}
        )

        assignments = submissions_data.get('assignments', [])
        if not assignments:
            return f"No submission information found for assignment {assignment_id}."

        submissions = assignments[0].get('submissions', [])

        return format_response(submissions, f"Submissions for Assignment {assignment_id}", format)
    except Exception as e:
        return f"Unable to retrieve submissions for assignment {assignment_id}. You may not have permission. Error: {str(e)}"

@mcp.tool(
    name="moodle_get_user_assignments",
    description="Get all assignments for a user across all enrolled courses. REQUIRED: user_id (integer). Example: user_id=624. Use moodle_get_current_user to get user_id. Returns assignment IDs and due dates.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_user_assignments(
    user_id: int | None = Field(None, description="User ID (omit for current user)"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get all assignments for a user across all enrolled courses.

    Shows all assignments from all courses where the user is enrolled.

    Args:
        user_id: Optional user ID (defaults to current user)
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of all user's assignments

    Example use cases:
        - "What assignments do I have?"
        - "Show all my assignments"
        - "List assignments for user 123"
    """
    moodle = get_moodle_client(ctx)

    # Resolve user_id to current user if not provided
    user_id = await resolve_user_id(moodle, user_id)

    # Get all assignments using helper
    all_assignments = await get_assignments_for_user(moodle, user_id, include_course_name=True)

    if not all_assignments:
        return f"No assignments found for user {user_id}."

    return format_response(all_assignments, f"All Assignments for User {user_id}", format)

# ============================================================================
# WRITE OPERATIONS - Require write permission for assignment submissions
# ============================================================================

@mcp.tool(
    name="moodle_get_submission_status",
    description="Get submission status for an assignment. REQUIRED: course_id (integer), assignment_id (integer). Optional: user_id (integer, omit for current user). Example: course_id=7299, assignment_id=123. Returns submission status, due dates, and whether user can submit.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_submission_status(
    course_id: int = Field(description="Course ID", gt=0),
    assignment_id: int = Field(description="Assignment ID", gt=0),
    user_id: int | None = Field(None, description="User ID (omit for current user)"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get detailed submission status for an assignment.

    Shows whether the assignment is submitted, draft status, due dates,
    and submission capabilities.

    Args:
        course_id: Course ID
        assignment_id: Assignment ID
        user_id: User ID (None for current user)
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Detailed submission status

    Example use cases:
        - "Can I still submit assignment 123?"
        - "What's the status of my assignment?"
        - "Check submission status for assignment 456"
    """
    moodle = get_moodle_client(ctx)

    # Resolve user_id
    user_id = await resolve_user_id(moodle, user_id)

    try:
        status_data = await moodle._make_request(
            'mod_assign_get_submission_status',
            {'assignid': assignment_id, 'userid': user_id}
        )

        return format_response(status_data, f"Submission Status (Assignment {assignment_id})", format)
    except Exception as e:
        return f"Unable to get submission status. Error: {str(e)}"

@mcp.tool(
    name="moodle_save_assignment_submission",
    description="Save assignment submission text (draft). REQUIRED: course_id (integer), assignment_id (integer), submission_text (string). WRITE OPERATION - only works on whitelisted courses (default: course 7299). Example: course_id=7299, assignment_id=123, submission_text='My answer'. This saves a draft, use moodle_submit_assignment to finalize.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,  # Safe to save multiple times
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_save_assignment_submission(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    assignment_id: int = Field(description="Assignment ID", gt=0),
    submission_text: str = Field(description="Assignment submission text content", min_length=1),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Save assignment submission text as draft.

    SAFETY: This write operation is only allowed on whitelisted courses.
    Default whitelist: [7299] (Elizabeth's Moodle Playground)

    This saves the submission as a DRAFT. To finalize submission,
    use moodle_submit_assignment after saving.

    Args:
        course_id: Course ID (must be in whitelist!)
        assignment_id: Assignment ID
        submission_text: Text content of submission
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation of saved submission

    Raises:
        WriteOperationError: If course_id is not whitelisted

    Example use cases:
        - "Save my assignment answer"
        - "Submit draft for assignment 123"
        - "Save assignment text"
    """
    moodle = get_moodle_client(ctx)

    try:
        # Prepare submission data
        params = {
            'assignmentid': assignment_id,
            'plugindata[onlinetext_editor][text]': submission_text,
            'plugindata[onlinetext_editor][format]': 1,  # HTML format
            'plugindata[onlinetext_editor][itemid]': 0
        }

        result = await moodle._make_request(
            'mod_assign_save_submission',
            params
        )

        response_data = {
            'assignment_id': assignment_id,
            'course_id': course_id,
            'saved': True,
            'status': 'draft'
        }

        return format_response(response_data, "Assignment Submission Saved (Draft)", format)
    except Exception as e:
        raise Exception(f"Failed to save assignment submission: {str(e)}")

@mcp.tool(
    name="moodle_submit_assignment",
    description="Submit assignment for grading (final submit). REQUIRED: course_id (integer), assignment_id (integer). WRITE OPERATION - DESTRUCTIVE - only works on whitelisted courses (default: course 7299). Example: course_id=7299, assignment_id=123. This finalizes the submission and cannot be undone (unless teacher reopens).",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,  # Final submission
        "idempotentHint": True,   # Safe to call multiple times
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_submit_assignment(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    assignment_id: int = Field(description="Assignment ID to submit", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Submit assignment for final grading.

    SAFETY: This write operation is only allowed on whitelisted courses.
    Default whitelist: [7299] (Elizabeth's Moodle Playground)

    WARNING: This is a FINAL action. Once submitted, you cannot edit
    the submission unless the teacher reopens it.

    Args:
        course_id: Course ID (must be in whitelist!)
        assignment_id: Assignment ID to submit
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation of submission

    Raises:
        WriteOperationError: If course_id is not whitelisted

    Example use cases:
        - "Submit assignment 123 for grading"
        - "Finalize my assignment submission"
        - "Turn in assignment"
    """
    moodle = get_moodle_client(ctx)

    try:
        params = {
            'assignmentid': assignment_id
        }

        result = await moodle._make_request(
            'mod_assign_submit_for_grading',
            params
        )

        response_data = {
            'assignment_id': assignment_id,
            'course_id': course_id,
            'status': 'submitted'
        }

        return format_response(response_data, "Assignment Submitted for Grading", format)
    except Exception as e:
        raise Exception(f"Failed to submit assignment: {str(e)}")
