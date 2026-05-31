"""
Enrollment tools - WRITE operations for managing course enrollment.
"""

from dataclasses import dataclass
from typing import Annotated

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors, require_write_permission
from ..utils.api_helpers import get_moodle_client


_ROLE_NAMES = {5: "Student", 4: "Teacher", 3: "Non-editing teacher", 1: "Manager"}


@dataclass
class EnrolmentResult:
    course_id: int
    user_ids: list[int]
    users_enrolled: int
    role_id: int
    role: str


@dataclass
class UnenrolmentResult:
    course_id: int
    user_ids: list[int]
    users_unenrolled: int


@mcp.tool(
    name="moodle_enrol_users",
    description=(
        "Enrol users into a course. REQUIRED: course_id (integer), user_ids "
        "(array of integers). Optional: role_id (default 5=Student; 4=Teacher, "
        "3=Non-editing teacher, 1=Manager). WRITE OPERATION - only works on "
        "whitelisted courses (default: course 7299)."
    ),
    tags={"write", "enrolment"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False,
        idempotentHint=True, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission("course_id")
async def moodle_enrol_users(
    course_id: Annotated[int, Field(description="Course ID (must be whitelisted)", gt=0)],
    user_ids: Annotated[list[int], Field(description="User IDs to enrol", min_length=1)],
    role_id: Annotated[int, Field(description="Role id (5=Student, 4=Teacher, 3=Non-editing, 1=Manager)", gt=0)] = 5,
    ctx: Context = None,
) -> EnrolmentResult:
    """
    Enrol one or more users into a course with a role.

    SAFETY: only allowed on whitelisted courses (default [7299]).
    enrol_manual_enrol_users returns null on success.
    """
    moodle = get_moodle_client(ctx)
    await moodle.call(
        "enrol_manual_enrol_users",
        {
            "enrolments": [
                {"roleid": role_id, "userid": uid, "courseid": course_id}
                for uid in user_ids
            ]
        },
    )
    return EnrolmentResult(
        course_id=course_id,
        user_ids=user_ids,
        users_enrolled=len(user_ids),
        role_id=role_id,
        role=_ROLE_NAMES.get(role_id, f"Role {role_id}"),
    )


@mcp.tool(
    name="moodle_unenrol_users",
    description=(
        "Unenrol (remove) users from a course. REQUIRED: course_id (integer), "
        "user_ids (array of integers). WRITE OPERATION - DESTRUCTIVE - only "
        "works on whitelisted courses (default: course 7299)."
    ),
    tags={"write", "enrolment", "destructive"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=True,
        idempotentHint=True, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission("course_id")
async def moodle_unenrol_users(
    course_id: Annotated[int, Field(description="Course ID (must be whitelisted)", gt=0)],
    user_ids: Annotated[list[int], Field(description="User IDs to unenrol", min_length=1)],
    ctx: Context = None,
) -> UnenrolmentResult:
    """
    Remove one or more users from a course.

    SAFETY: only allowed on whitelisted courses (default [7299]).
    WARNING: users lose course access; progress/grades are hidden (not deleted).
    enrol_manual_unenrol_users returns null on success.
    """
    moodle = get_moodle_client(ctx)
    await moodle.call(
        "enrol_manual_unenrol_users",
        {
            "enrolments": [
                {"userid": uid, "courseid": course_id} for uid in user_ids
            ]
        },
    )
    return UnenrolmentResult(
        course_id=course_id,
        user_ids=user_ids,
        users_unenrolled=len(user_ids),
    )
