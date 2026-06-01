"""
Completion tracking tools for Moodle MCP server.

Provides READ and WRITE operations for managing course and activity completion
status. Completion tracking is essential for monitoring student progress and
managing course workflows.

Tools:
- moodle_get_activities_completion_status: Get completion status of activities (READ)
- moodle_get_course_completion_status: Get overall course completion status (READ)
- moodle_mark_course_self_completed: Student marks course as self-completed (WRITE)
- moodle_update_activity_completion_status_manually: Manually mark activity complete (WRITE)
"""

from dataclasses import dataclass, field
from typing import Annotated

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors, require_write_permission
from ..utils.api_helpers import get_moodle_client, get_resolver


# --------------------------------------------------------------------------- #
# Local structured-output models (FastMCP 3.x).
# Kept here (not in models/results.py) since they're specific to completion tools.
# --------------------------------------------------------------------------- #
@dataclass
class ActivityCompletion:
    cmid: int | None = None
    modname: str | None = None
    instance: int | None = None
    state: int | None = None
    timecompleted: int | None = None
    tracking: int | None = None


@dataclass
class ActivitiesCompletionStatus:
    course_id: int
    user_id: int
    statuses: list[ActivityCompletion] = field(default_factory=list)
    count: int = 0


@dataclass
class CompletionCriteria:
    type: str | None = None
    title: str | None = None
    status: str | None = None
    complete: bool | None = None


@dataclass
class CourseCompletionStatus:
    course_id: int
    user_id: int
    completed: bool | None = None
    aggregation: int | None = None
    criteria: list[CompletionCriteria] = field(default_factory=list)


@dataclass
class WriteResult:
    success: bool
    message: str


# ============================================================================
# READ OPERATIONS
# ============================================================================


@mcp.tool(
    name="moodle_get_activities_completion_status",
    description=(
        "Get completion status for all activities in a course for a user. "
        "Accepts a numeric course id, shortname, or idnumber; and a numeric "
        "user id, username, or email (omit for the current user). "
        "Example: course=7299, user=123."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_activities_completion_status(
    course: Annotated[
        int | str, Field(description="Course id, shortname, or idnumber")
    ],
    user: Annotated[
        int | str | None,
        Field(description="User id, username, or email; omit for current user"),
    ] = None,
    ctx: Context = None,
) -> ActivitiesCompletionStatus:
    """Get a user's activity completion status in a course.

    State values: 0=incomplete, 1=complete, 2=complete with pass,
    3=complete with fail. Tracking: 0=none, 1=manual, 2=automatic.
    """
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    cid = await resolver.course_id(course)
    uid = await resolver.user_id(user)

    result = await moodle.call(
        "core_completion_get_activities_completion_status",
        {"courseid": cid, "userid": uid},
    )

    raw = (result or {}).get("statuses", []) if isinstance(result, dict) else []
    statuses = [
        ActivityCompletion(
            cmid=s.get("cmid"),
            modname=s.get("modname"),
            instance=s.get("instance"),
            state=s.get("state"),
            timecompleted=s.get("timecompleted"),
            tracking=s.get("tracking"),
        )
        for s in raw
    ]
    return ActivitiesCompletionStatus(
        course_id=cid, user_id=uid, statuses=statuses, count=len(statuses)
    )


@mcp.tool(
    name="moodle_get_course_completion_status",
    description=(
        "Get overall course completion status for a user. Accepts a numeric "
        "course id, shortname, or idnumber; and a numeric user id, username, "
        "or email (omit for the current user). Example: course=7299, user=123."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_course_completion_status(
    course: Annotated[
        int | str, Field(description="Course id, shortname, or idnumber")
    ],
    user: Annotated[
        int | str | None,
        Field(description="User id, username, or email; omit for current user"),
    ] = None,
    ctx: Context = None,
) -> CourseCompletionStatus:
    """Get a user's overall course completion status."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    cid = await resolver.course_id(course)
    uid = await resolver.user_id(user)

    result = await moodle.call(
        "core_completion_get_course_completion_status",
        {"courseid": cid, "userid": uid},
    )

    status = (result or {}).get("completionstatus", {}) if isinstance(result, dict) else {}
    criteria = [
        CompletionCriteria(
            type=c.get("type"),
            title=c.get("title"),
            status=c.get("status"),
            complete=c.get("complete"),
        )
        for c in (status.get("completions", []) or [])
    ]
    return CourseCompletionStatus(
        course_id=cid,
        user_id=uid,
        completed=status.get("completed"),
        aggregation=status.get("aggregation"),
        criteria=criteria,
    )


# ============================================================================
# WRITE OPERATIONS
# ============================================================================


@mcp.tool(
    name="moodle_mark_course_self_completed",
    description=(
        "Mark a course as self-completed by the current user. REQUIRED: "
        "course (id/shortname/name). Example: course=7299. WRITE OPERATION - only "
        "works on whitelisted courses (default: 7299). Used when students want "
        "to mark the course as completed on their own."
    ),
    tags={"write", "completion"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False,
        idempotentHint=True, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission('course')
async def moodle_mark_course_self_completed(
    course: Annotated[
        int | str,
        Field(description="Course id, shortname, or name (must be whitelisted)"),
    ],
    ctx: Context = None,
) -> WriteResult:
    """Mark a course as self-completed by the current user.

    Requires the course to allow self-completion. Idempotent.
    """
    moodle = get_moodle_client(ctx)
    cid = await get_resolver(ctx).course_id(course)

    await moodle.call(
        "core_completion_mark_course_self_completed",
        {"courseid": cid},
    )

    return WriteResult(
        success=True,
        message=f"Course {cid} marked as self-completed.",
    )


@mcp.tool(
    name="moodle_update_activity_completion_status_manually",
    description=(
        "Manually update completion status for an activity. REQUIRED: course "
        "(id/shortname/name), activity (name or course-module id), completed "
        "(boolean). Example: course=7299, activity='Cat Health Quiz', "
        "completed=true. WRITE OPERATION - only works on whitelisted courses. "
        "Used by teachers to manually override activity completion."
    ),
    tags={"write", "completion"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False,
        idempotentHint=True, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission('course')
async def moodle_update_activity_completion_status_manually(
    course: Annotated[
        int | str,
        Field(description="Course id, shortname, or name (must be whitelisted)"),
    ],
    activity: Annotated[
        int | str,
        Field(description="Activity name or course-module id (cmid)"),
    ],
    completed: Annotated[
        bool, Field(description="Completion status: true = complete, false = incomplete")
    ],
    ctx: Context = None,
) -> WriteResult:
    """Manually mark an activity complete/incomplete.

    Only works for activities with manual completion tracking enabled.
    Idempotent.
    """
    moodle = get_moodle_client(ctx)
    cm_id = (await get_resolver(ctx).activity(course, activity)).cmid

    await moodle.call(
        "core_completion_update_activity_completion_status_manually",
        {"cmid": cm_id, "completed": 1 if completed else 0},
    )

    state = "complete" if completed else "incomplete"
    return WriteResult(
        success=True,
        message=f"Activity {cm_id} marked as {state}.",
    )
