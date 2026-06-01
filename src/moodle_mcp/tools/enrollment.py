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
from ..utils.api_helpers import get_moodle_client, get_resolver


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
        "Enrol users into a course. REQUIRED: course (id/shortname/name), users "
        "(array of user ids, usernames, or emails). Optional: role_id (default "
        "5=Student; 4=Teacher, 3=Non-editing teacher, 1=Manager). WRITE OPERATION "
        "- only works on whitelisted courses (default: course 7299). "
        "Example: course=7299, users=['stu@example.com', 624]."
    ),
    tags={"write", "enrolment"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False,
        idempotentHint=True, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission("course")
async def moodle_enrol_users(
    course: Annotated[
        int | str,
        Field(description="Course id, shortname, or name (must be whitelisted)"),
    ],
    users: Annotated[
        list[int | str],
        Field(description="User ids, usernames, or emails to enrol", min_length=1),
    ],
    role_id: Annotated[int, Field(description="Role id (5=Student, 4=Teacher, 3=Non-editing, 1=Manager)", gt=0)] = 5,
    ctx: Context = None,
) -> EnrolmentResult:
    """Enrol users into a course with a role.

    Calls enrol_manual_enrol_users, which returns null on success.
    """
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    cid = await resolver.course_id(course)
    uids = [await resolver.user_id(u) for u in users]

    await moodle.call(
        "enrol_manual_enrol_users",
        {
            "enrolments": [
                {"roleid": role_id, "userid": uid, "courseid": cid}
                for uid in uids
            ]
        },
    )
    return EnrolmentResult(
        course_id=cid,
        user_ids=uids,
        users_enrolled=len(uids),
        role_id=role_id,
        role=_ROLE_NAMES.get(role_id, f"Role {role_id}"),
    )


@mcp.tool(
    name="moodle_unenrol_users",
    description=(
        "Unenrol (remove) users from a course. REQUIRED: course (id/shortname/"
        "name), users (array of user ids, usernames, or emails). WRITE OPERATION "
        "- DESTRUCTIVE - only works on whitelisted courses (default: course 7299). "
        "Example: course=7299, users=['stu@example.com']."
    ),
    tags={"write", "enrolment", "destructive"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=True,
        idempotentHint=True, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission("course")
async def moodle_unenrol_users(
    course: Annotated[
        int | str,
        Field(description="Course id, shortname, or name (must be whitelisted)"),
    ],
    users: Annotated[
        list[int | str],
        Field(description="User ids, usernames, or emails to unenrol", min_length=1),
    ],
    ctx: Context = None,
) -> UnenrolmentResult:
    """Unenrol users from a course.

    Users lose course access; their progress/grades are hidden, not deleted.
    Calls enrol_manual_unenrol_users, which returns null on success.
    """
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    cid = await resolver.course_id(course)
    uids = [await resolver.user_id(u) for u in users]

    await moodle.call(
        "enrol_manual_unenrol_users",
        {
            "enrolments": [
                {"userid": uid, "courseid": cid} for uid in uids
            ]
        },
    )
    return UnenrolmentResult(
        course_id=cid,
        user_ids=uids,
        users_unenrolled=len(uids),
    )
