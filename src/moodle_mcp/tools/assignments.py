"""
Assignment tools - READ and WRITE operations for assignments and submissions.
"""

from dataclasses import dataclass, field
from typing import Annotated

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors, require_write_permission
from ..utils.api_helpers import get_moodle_client, get_resolver
from ..utils.assignment_helpers import (
    find_assignment_by_id,
    find_assignment_in_course,
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
    # Flat summary extracted from mod_assign_get_submission_status.lastattempt
    # (the full nested API blob is teacher-view metadata that bloats output).
    grading_status: str | None = None   # e.g. 'graded' | 'notgraded'
    graded: bool | None = None
    can_submit: bool | None = None
    can_edit: bool | None = None
    locked: bool | None = None
    submission_status: str | None = None  # the current submission's status string


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
    """List a course's assignments."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    cid = await resolver.course_id(course)

    assignments = await get_assignments_for_course(moodle, cid)
    items = [_assignment(a) for a in assignments]
    return AssignmentList(assignments=items, count=len(items))


@mcp.tool(
    name="moodle_get_assignment_details",
    description=(
        "Get details (description, due date, submission settings) for one "
        "assignment. Best: pass course plus the assignment name or instance id "
        "-- a single lookup. If you pass only an assignment instance id without "
        "course, it falls back to scanning your enrolled courses. "
        "Example: course='Biology 101', assignment='Lab Report 1'."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_assignment_details(
    assignment: Annotated[
        int | str, Field(description="Assignment name (with course) or instance id")
    ],
    course: Annotated[
        int | str | None,
        Field(description="Course id, shortname, or name (recommended)"),
    ] = None,
    ctx: Context = None,
) -> Assignment:
    """Get an assignment's details (single lookup when course is given)."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    from ..core.exceptions import MoodleNotFoundError

    if course is not None:
        act = await resolver.activity(course, assignment, modname="assign")
        cid = await resolver.course_id(course)
        found = await find_assignment_in_course(moodle, cid, act.instance)
    elif isinstance(assignment, int):
        found = await find_assignment_by_id(moodle, assignment)
    else:
        raise MoodleNotFoundError(
            "Pass 'course' when identifying an assignment by name."
        )

    if not found:
        raise MoodleNotFoundError(f"Assignment {assignment!r} not found.")

    return _assignment(found)


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
    """Get an assignment's submissions."""
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
    """Get a user's assignments across all enrolled courses."""
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
        "Get submission status for an assignment. Pass course plus the "
        "assignment name (recommended), or an assignment instance id directly. "
        "Optional: user (id, username, or email; omit for current user). "
        "Returns submission status, due dates, and whether the user can submit. "
        "Example: course='Biology 101', assignment='Lab Report 1'."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_submission_status(
    assignment: Annotated[
        int | str, Field(description="Assignment name (with course) or instance id")
    ],
    course: Annotated[
        int | str | None,
        Field(description="Course id, shortname, or name (required if assignment is a name)"),
    ] = None,
    user: Annotated[
        int | str | None,
        Field(description="User id, username, or email; omit for current user"),
    ] = None,
    ctx: Context = None,
) -> SubmissionStatus:
    """Get a user's submission status for an assignment."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    uid = await resolver.user_id(user)

    if course is not None:
        aid = (await resolver.activity(course, assignment, modname="assign")).instance
    elif isinstance(assignment, int):
        aid = assignment
    else:
        from ..core.exceptions import MoodleNotFoundError
        raise MoodleNotFoundError(
            "Pass 'course' when identifying an assignment by name."
        )

    status_data = await moodle.call(
        "mod_assign_get_submission_status",
        {"assignid": aid, "userid": uid},
    )

    last = (status_data or {}).get("lastattempt", {}) or {}
    submission = last.get("submission") or {}
    return SubmissionStatus(
        assignment_id=aid,
        user_id=uid,
        grading_status=last.get("gradingstatus"),
        graded=last.get("graded"),
        can_submit=last.get("cansubmit"),
        can_edit=last.get("canedit"),
        locked=last.get("locked"),
        submission_status=submission.get("status"),
    )


# ============================================================================
# WRITE OPERATIONS - Require write permission for assignment submissions
# ============================================================================

@mcp.tool(
    name="moodle_save_assignment_submission",
    description=(
        "WRITE: save online-text content as a draft submission for an "
        "assignment (does not finalize -- use moodle_submit_assignment for "
        "that). Only works on write-whitelisted courses (course 7299 in DEV). "
        "'assignment' accepts the activity name or its instance id. "
        "Example: course=7299, assignment='Lab Report 1', "
        "submission_text='My answer'."
    ),
    tags={"write", "assignment"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False,
        idempotentHint=True, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission('course')
async def moodle_save_assignment_submission(
    course: Annotated[
        int | str,
        Field(description="Course id, shortname, or name (must be whitelisted)"),
    ],
    assignment: Annotated[
        int | str, Field(description="Assignment name or instance id")
    ],
    submission_text: Annotated[
        str, Field(description="Assignment submission text content", min_length=1)
    ],
    ctx: Context = None,
) -> SavedSubmission:
    """Save assignment submission text as a draft (whitelisted courses only)."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)

    cid = await resolver.course_id(course)
    act = await resolver.activity(course, assignment, modname="assign")

    await moodle.call(
        "mod_assign_save_submission",
        {
            "assignmentid": act.instance,
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
        assignment_id=act.instance,
        course_id=cid,
        saved=True,
        status="draft",
    )


@mcp.tool(
    name="moodle_submit_assignment",
    description=(
        "WRITE (destructive): finalize (submit for grading) an assignment's "
        "draft. Only works on write-whitelisted courses (course 7299 in DEV). "
        "'assignment' accepts the activity name or its instance id. Save draft "
        "content first with moodle_save_assignment_submission. Cannot be undone "
        "unless a teacher reopens. Example: course=7299, "
        "assignment='Lab Report 1'."
    ),
    tags={"write", "assignment"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=True,
        idempotentHint=True, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission('course')
async def moodle_submit_assignment(
    course: Annotated[
        int | str,
        Field(description="Course id, shortname, or name (must be whitelisted)"),
    ],
    assignment: Annotated[
        int | str, Field(description="Assignment name or instance id")
    ],
    ctx: Context = None,
) -> SubmittedAssignment:
    """Submit an assignment for final grading (whitelisted courses only)."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)

    cid = await resolver.course_id(course)
    act = await resolver.activity(course, assignment, modname="assign")

    await moodle.call(
        "mod_assign_submit_for_grading", {"assignmentid": act.instance}
    )

    return SubmittedAssignment(
        assignment_id=act.instance, course_id=cid, status="submitted"
    )
