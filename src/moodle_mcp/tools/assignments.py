"""
Assignment tools - READ and WRITE operations for assignments and submissions.
"""

from dataclasses import dataclass, field
from typing import Any, Annotated

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors, require_write_permission
from ..utils.api_helpers import get_moodle_client, get_resolver
from ..utils.assignment_helpers import (
    find_assignment_by_id,
    get_assignments_for_user,
    get_assignments_for_course,
)


# --------------------------------------------------------------------------- #
# Local structured-output models (FastMCP 3.x).
# Kept here (not in models/results.py) since they're specific to assignment tools.
# --------------------------------------------------------------------------- #
@dataclass
class Assignment:
    id: int
    name: str | None = None
    course_id: int | None = None
    course_name: str | None = None
    duedate: int | None = None
    allowsubmissionsfromdate: int | None = None
    cutoffdate: int | None = None
    intro: str | None = None


@dataclass
class AssignmentList:
    assignments: list[Assignment] = field(default_factory=list)
    count: int = 0


@dataclass
class Submission:
    id: int
    userid: int | None = None
    status: str | None = None
    timemodified: int | None = None
    attemptnumber: int | None = None


@dataclass
class SubmissionList:
    assignment_id: int
    submissions: list[Submission] = field(default_factory=list)
    count: int = 0


@dataclass
class SubmissionStatus:
    assignment_id: int
    user_id: int
    status: dict[str, Any] = field(default_factory=dict)


@dataclass
class SavedSubmission:
    assignment_id: int
    course_id: int
    saved: bool
    status: str


@dataclass
class SubmittedAssignment:
    assignment_id: int
    course_id: int
    status: str


def _assignment(data: dict) -> Assignment:
    """Build an Assignment from a raw Moodle assignment dict."""
    return Assignment(
        id=data.get("id", 0),
        name=data.get("name"),
        course_id=data.get("course_id") or data.get("course"),
        course_name=data.get("course_name") or data.get("coursename"),
        duedate=data.get("duedate"),
        allowsubmissionsfromdate=data.get("allowsubmissionsfromdate"),
        cutoffdate=data.get("cutoffdate"),
        intro=data.get("intro"),
    )


# ============================================================================
# READ OPERATIONS
# ============================================================================

@mcp.tool(
    name="moodle_list_assignments",
    description=(
        "Get all assignments in a course. Accepts a numeric course id, "
        "shortname, or idnumber. Example: course=2292. Returns assignment ids."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_list_assignments(
    course: Annotated[
        int | str, Field(description="Course id, shortname, or idnumber")
    ],
    ctx: Context = None,
) -> AssignmentList:
    """
    Get list of all assignments in a course.

    Example use cases:
        - "What assignments are in course 42?"
        - "List all assignments for course 15"
    """
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    cid = await resolver.course_id(course)

    assignments = await get_assignments_for_course(moodle, cid)
    items = [_assignment(a) for a in assignments]
    return AssignmentList(assignments=items, count=len(items))


@mcp.tool(
    name="moodle_get_assignment_details",
    description=(
        "Get detailed information about an assignment including description, "
        "due date, and submission settings. REQUIRED: assignment_id (integer). "
        "Example: assignment_id=123. Use moodle_list_assignments to get "
        "assignment_id."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_assignment_details(
    assignment_id: Annotated[int, Field(description="Assignment ID", gt=0)],
    ctx: Context = None,
) -> Assignment:
    """
    Get comprehensive details for a specific assignment.

    Example use cases:
        - "Show details for assignment 123"
        - "Get due date for assignment 67"
    """
    moodle = get_moodle_client(ctx)

    assignment = await find_assignment_by_id(moodle, assignment_id)
    if not assignment:
        from ..core.exceptions import MoodleNotFoundError
        raise MoodleNotFoundError(
            f"Assignment {assignment_id} not found in your enrolled courses."
        )

    return _assignment(assignment)


@mcp.tool(
    name="moodle_get_assignment_submissions",
    description=(
        "Get all submissions for an assignment (requires teacher/grader "
        "permissions). REQUIRED: assignment_id (integer). Example: "
        "assignment_id=123. Use moodle_list_assignments to get assignment_id."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_assignment_submissions(
    assignment_id: Annotated[int, Field(description="Assignment ID", gt=0)],
    ctx: Context = None,
) -> SubmissionList:
    """
    Get list of submissions for an assignment.

    Shows submission status for all students (requires teacher/admin
    permissions).

    Example use cases:
        - "Show submissions for assignment 123"
        - "Who submitted assignment 45?"
    """
    moodle = get_moodle_client(ctx)

    submissions_data = await moodle.call(
        "mod_assign_get_submissions", {"assignmentids": [assignment_id]}
    )

    assignments = (submissions_data or {}).get("assignments", [])
    raw = assignments[0].get("submissions", []) if assignments else []

    submissions = [
        Submission(
            id=s.get("id", 0),
            userid=s.get("userid"),
            status=s.get("status"),
            timemodified=s.get("timemodified"),
            attemptnumber=s.get("attemptnumber"),
        )
        for s in raw
    ]
    return SubmissionList(
        assignment_id=assignment_id, submissions=submissions, count=len(submissions)
    )


@mcp.tool(
    name="moodle_get_user_assignments",
    description=(
        "Get all assignments for a user across all enrolled courses. Accepts a "
        "numeric user id, username, or email (omit for the current user). "
        "Example: user=624. Returns assignment ids and due dates."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_user_assignments(
    user: Annotated[
        int | str | None,
        Field(description="User id, username, or email; omit for current user"),
    ] = None,
    ctx: Context = None,
) -> AssignmentList:
    """
    Get all assignments for a user across all enrolled courses.

    Example use cases:
        - "What assignments do I have?"
        - "List assignments for user 123"
    """
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    uid = await resolver.user_id(user)

    all_assignments = await get_assignments_for_user(
        moodle, uid, include_course_name=True
    )
    items = [_assignment(a) for a in all_assignments]
    return AssignmentList(assignments=items, count=len(items))


@mcp.tool(
    name="moodle_get_submission_status",
    description=(
        "Get submission status for an assignment. REQUIRED: assignment_id "
        "(integer). Optional: user (id, username, or email; omit for current "
        "user). Example: assignment_id=123. Returns submission status, due "
        "dates, and whether the user can submit."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_submission_status(
    assignment_id: Annotated[int, Field(description="Assignment ID", gt=0)],
    user: Annotated[
        int | str | None,
        Field(description="User id, username, or email; omit for current user"),
    ] = None,
    ctx: Context = None,
) -> SubmissionStatus:
    """
    Get detailed submission status for an assignment.

    Example use cases:
        - "Can I still submit assignment 123?"
        - "Check submission status for assignment 456"
    """
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    uid = await resolver.user_id(user)

    status_data = await moodle.call(
        "mod_assign_get_submission_status",
        {"assignid": assignment_id, "userid": uid},
    )

    return SubmissionStatus(
        assignment_id=assignment_id, user_id=uid, status=status_data or {}
    )


# ============================================================================
# WRITE OPERATIONS - Require write permission for assignment submissions
# ============================================================================

@mcp.tool(
    name="moodle_save_assignment_submission",
    description=(
        "Save assignment submission text (draft). REQUIRED: course_id "
        "(integer), assignment_id (integer), submission_text (string). WRITE "
        "OPERATION - only works on whitelisted courses (default: course 7299). "
        "Example: course_id=7299, assignment_id=123, submission_text='My "
        "answer'. This saves a draft; use moodle_submit_assignment to finalize."
    ),
    tags={"write", "assignment"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False,
        idempotentHint=True, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_save_assignment_submission(
    course_id: Annotated[
        int, Field(description="Course ID (must be whitelisted)", gt=0)
    ],
    assignment_id: Annotated[int, Field(description="Assignment ID", gt=0)],
    submission_text: Annotated[
        str, Field(description="Assignment submission text content", min_length=1)
    ],
    ctx: Context = None,
) -> SavedSubmission:
    """
    Save assignment submission text as draft.

    SAFETY: This write operation is only allowed on whitelisted courses.
    Default whitelist: [7299] (Elizabeth's Moodle Playground)

    This saves the submission as a DRAFT. To finalize submission, use
    moodle_submit_assignment after saving.

    Example use cases:
        - "Save my assignment answer"
        - "Submit draft for assignment 123"
    """
    moodle = get_moodle_client(ctx)

    await moodle.call(
        "mod_assign_save_submission",
        {
            "assignmentid": assignment_id,
            "plugindata": {
                "onlinetext_editor": {
                    "text": submission_text,
                    "format": 1,  # HTML format
                    "itemid": 0,
                }
            },
        },
    )

    return SavedSubmission(
        assignment_id=assignment_id,
        course_id=course_id,
        saved=True,
        status="draft",
    )


@mcp.tool(
    name="moodle_submit_assignment",
    description=(
        "Submit assignment for grading (final submit). REQUIRED: course_id "
        "(integer), assignment_id (integer). WRITE OPERATION - DESTRUCTIVE - "
        "only works on whitelisted courses (default: course 7299). Example: "
        "course_id=7299, assignment_id=123. This finalizes the submission and "
        "cannot be undone (unless a teacher reopens)."
    ),
    tags={"write", "assignment"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=True,
        idempotentHint=True, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_submit_assignment(
    course_id: Annotated[
        int, Field(description="Course ID (must be whitelisted)", gt=0)
    ],
    assignment_id: Annotated[
        int, Field(description="Assignment ID to submit", gt=0)
    ],
    ctx: Context = None,
) -> SubmittedAssignment:
    """
    Submit assignment for final grading.

    SAFETY: This write operation is only allowed on whitelisted courses.
    Default whitelist: [7299] (Elizabeth's Moodle Playground)

    WARNING: This is a FINAL action. Once submitted, you cannot edit the
    submission unless the teacher reopens it.

    Example use cases:
        - "Submit assignment 123 for grading"
        - "Turn in assignment"
    """
    moodle = get_moodle_client(ctx)

    await moodle.call(
        "mod_assign_submit_for_grading", {"assignmentid": assignment_id}
    )

    return SubmittedAssignment(
        assignment_id=assignment_id, course_id=course_id, status="submitted"
    )
