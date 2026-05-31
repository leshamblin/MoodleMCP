"""Group management tools for the Moodle MCP server."""

from dataclasses import dataclass, field
from typing import Annotated

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from ..core.exceptions import MoodleNotFoundError
from ..server import mcp
from ..utils.api_helpers import get_moodle_client, get_resolver
from ..utils.error_handling import handle_moodle_errors, require_write_permission


# ---------------------------------------------------------------------------
# Result models (structured output)
# ---------------------------------------------------------------------------


@dataclass
class Group:
    """A single Moodle group."""

    id: int
    name: str
    courseid: int = 0
    description: str = ""
    idnumber: str = ""
    enrolmentkey: str = ""


@dataclass
class CourseGroups:
    """Groups belonging to a course."""

    course_id: int
    count: int
    groups: list[Group] = field(default_factory=list)


@dataclass
class Grouping:
    """A single Moodle grouping."""

    id: int
    name: str
    courseid: int = 0
    description: str = ""
    idnumber: str = ""


@dataclass
class CourseGroupings:
    """Groupings belonging to a course."""

    course_id: int
    count: int
    groupings: list[Grouping] = field(default_factory=list)


@dataclass
class ActivityAllowedGroups:
    """Groups a user is allowed to access for an activity."""

    cmid: int
    user_id: int
    count: int
    groups: list[Group] = field(default_factory=list)


@dataclass
class ActivityGroupMode:
    """Group mode setting for an activity."""

    cmid: int
    groupmode: int
    groupmode_name: str


@dataclass
class UserCourseGroups:
    """Groups a user belongs to within a course."""

    course_id: int
    user_id: int
    count: int
    group_ids: list[int] = field(default_factory=list)


@dataclass
class GroupMember:
    """A member of a group."""

    user_id: int
    fullname: str = ""
    email: str = ""


@dataclass
class GroupMembers:
    """Members of a single group."""

    group_id: int
    count: int
    members: list[GroupMember] = field(default_factory=list)


@dataclass
class CreatedGroup:
    """A group created by a write operation."""

    id: int
    name: str
    courseid: int


@dataclass
class CreateGroupsResult:
    """Result of creating one or more groups."""

    course_id: int
    count: int
    groups: list[CreatedGroup] = field(default_factory=list)


@dataclass
class GroupMembershipChange:
    """Result of adding or removing group members."""

    course_id: int
    group_id: int
    user_ids: list[int] = field(default_factory=list)
    success: bool = True
    message: str = ""


@dataclass
class DeleteGroupsResult:
    """Result of deleting one or more groups."""

    course_id: int
    group_ids: list[int] = field(default_factory=list)
    success: bool = True
    message: str = ""


_GROUPMODE_NAMES = {0: "No groups", 1: "Separate groups", 2: "Visible groups"}


# ---------------------------------------------------------------------------
# READ tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="moodle_get_course_groups",
    description="Get all groups in a course. Accepts a course ID or name.",
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_course_groups(
    course: Annotated[
        int | str, Field(description="Course ID or name to get groups for")
    ],
    ctx: Context = None,
) -> CourseGroups:
    """Return all groups belonging to a course."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)

    cid = await resolver.course_id(course)
    data = await moodle.call("core_group_get_course_groups", {"courseid": cid})

    groups = [
        Group(
            id=g.get("id"),
            name=g.get("name", ""),
            courseid=g.get("courseid", cid),
            description=g.get("description", ""),
            idnumber=g.get("idnumber", ""),
            enrolmentkey=g.get("enrolmentkey", ""),
        )
        for g in (data or [])
    ]
    return CourseGroups(course_id=cid, count=len(groups), groups=groups)


@mcp.tool(
    name="moodle_get_course_groupings",
    description="Get all groupings in a course. Accepts a course ID or name.",
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_course_groupings(
    course: Annotated[
        int | str, Field(description="Course ID or name to get groupings for")
    ],
    ctx: Context = None,
) -> CourseGroupings:
    """Return all groupings belonging to a course."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)

    cid = await resolver.course_id(course)
    data = await moodle.call("core_group_get_course_groupings", {"courseid": cid})

    groupings = [
        Grouping(
            id=g.get("id"),
            name=g.get("name", ""),
            courseid=g.get("courseid", cid),
            description=g.get("description", ""),
            idnumber=g.get("idnumber", ""),
        )
        for g in (data or [])
    ]
    return CourseGroupings(course_id=cid, count=len(groupings), groupings=groupings)


@mcp.tool(
    name="moodle_get_activity_allowed_groups",
    description=(
        "Get the groups a user is allowed to access in an activity. "
        "Provide the course module ID (cmid) and a user ID or name."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_activity_allowed_groups(
    cmid: Annotated[int, Field(description="Course module ID of the activity", gt=0)],
    user: Annotated[
        int | str,
        Field(description="User ID or name (defaults to current user if 0)"),
    ] = 0,
    ctx: Context = None,
) -> ActivityAllowedGroups:
    """Return the groups a user can access for an activity."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)

    uid = await resolver.user_id(user) if user else 0
    params = {"cmid": cmid, "userid": uid}
    data = await moodle.call("core_group_get_activity_allowed_groups", params)

    raw_groups = (data or {}).get("groups", [])
    groups = [
        Group(
            id=g.get("id"),
            name=g.get("name", ""),
            courseid=g.get("courseid", 0),
            description=g.get("description", ""),
            idnumber=g.get("idnumber", ""),
            enrolmentkey=g.get("enrolmentkey", ""),
        )
        for g in raw_groups
    ]
    return ActivityAllowedGroups(
        cmid=cmid, user_id=uid, count=len(groups), groups=groups
    )


@mcp.tool(
    name="moodle_get_activity_groupmode",
    description=(
        "Get the group mode for an activity (0=no groups, 1=separate, "
        "2=visible). Provide the course module ID (cmid)."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_activity_groupmode(
    cmid: Annotated[int, Field(description="Course module ID of the activity", gt=0)],
    ctx: Context = None,
) -> ActivityGroupMode:
    """Return the group mode setting for an activity."""
    moodle = get_moodle_client(ctx)

    data = await moodle.call("core_group_get_activity_groupmode", {"cmid": cmid})

    groupmode = (data or {}).get("groupmode", 0)
    return ActivityGroupMode(
        cmid=cmid,
        groupmode=groupmode,
        groupmode_name=_GROUPMODE_NAMES.get(groupmode, "Unknown"),
    )


@mcp.tool(
    name="moodle_get_course_user_groups",
    description=(
        "Get the groups a user belongs to within a course. Accepts a course "
        "ID or name and a user ID or name."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_course_user_groups(
    course: Annotated[int | str, Field(description="Course ID or name")],
    user: Annotated[
        int | str,
        Field(description="User ID or name (defaults to current user if 0)"),
    ] = 0,
    ctx: Context = None,
) -> UserCourseGroups:
    """Return the groups a user belongs to within a course."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)

    cid = await resolver.course_id(course)
    uid = await resolver.user_id(user) if user else 0
    params = {"courseid": cid, "userid": uid}
    data = await moodle.call("core_group_get_course_user_groups", params)

    raw_groups = (data or {}).get("groups", [])
    group_ids = [g.get("id") for g in raw_groups]
    return UserCourseGroups(
        course_id=cid, user_id=uid, count=len(group_ids), group_ids=group_ids
    )


@mcp.tool(
    name="moodle_get_groups_for_selector",
    description=(
        "Get the groups available in a course's group selector. Accepts a "
        "course ID or name."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_groups_for_selector(
    course: Annotated[int | str, Field(description="Course ID or name")],
    ctx: Context = None,
) -> CourseGroups:
    """Return the groups available in a course's group selector."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)

    cid = await resolver.course_id(course)
    data = await moodle.call("core_group_get_groups_for_selector", {"courseid": cid})

    raw_groups = (data or {}).get("groups", [])
    groups = [
        Group(
            id=g.get("id"),
            name=g.get("name", ""),
            courseid=g.get("courseid", cid),
            description=g.get("description", ""),
            idnumber=g.get("idnumber", ""),
            enrolmentkey=g.get("enrolmentkey", ""),
        )
        for g in raw_groups
    ]
    return CourseGroups(course_id=cid, count=len(groups), groups=groups)


@mcp.tool(
    name="moodle_get_group_members",
    description="Get the members of a group. Provide the group ID.",
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_group_members(
    group_id: Annotated[int, Field(description="Group ID to get members for", gt=0)],
    ctx: Context = None,
) -> GroupMembers:
    """Return the members of a group, enriched with user details."""
    moodle = get_moodle_client(ctx)

    data = await moodle.call("core_group_get_group_members", {"groupids": [group_id]})

    entry = None
    for item in data or []:
        if item.get("groupid") == group_id:
            entry = item
            break

    if entry is None:
        raise MoodleNotFoundError(f"Group {group_id} not found")

    user_ids = entry.get("userids", [])

    # Enrich with names/emails where possible.
    members: list[GroupMember] = []
    if user_ids:
        users = await moodle.call(
            "core_user_get_users_by_field",
            {"field": "id", "values": user_ids},
        )
        users_by_id = {u.get("id"): u for u in (users or [])}
        for uid in user_ids:
            u = users_by_id.get(uid, {})
            members.append(
                GroupMember(
                    user_id=uid,
                    fullname=u.get("fullname", ""),
                    email=u.get("email", ""),
                )
            )

    return GroupMembers(group_id=group_id, count=len(members), members=members)


# ---------------------------------------------------------------------------
# WRITE tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="moodle_create_groups",
    description=(
        "WRITE OPERATION - only works on whitelisted courses. Create a new "
        "group in a course."
    ),
    tags={"write", "group"},
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission("course_id")
async def moodle_create_groups(
    course_id: Annotated[
        int, Field(description="Course ID (must be whitelisted)", gt=0)
    ],
    name: Annotated[str, Field(description="Name of the group", min_length=1)],
    description: Annotated[str, Field(description="Group description")] = "",
    ctx: Context = None,
) -> CreateGroupsResult:
    """Create a group in a course (whitelisted courses only)."""
    moodle = get_moodle_client(ctx)

    params = {
        "groups": [
            {
                "courseid": course_id,
                "name": name,
                "description": description,
            }
        ]
    }
    data = await moodle.call("core_group_create_groups", params)

    created = [
        CreatedGroup(
            id=g.get("id"),
            name=g.get("name", name),
            courseid=g.get("courseid", course_id),
        )
        for g in (data or [])
    ]
    return CreateGroupsResult(
        course_id=course_id, count=len(created), groups=created
    )


@mcp.tool(
    name="moodle_add_group_members",
    description=(
        "WRITE OPERATION - only works on whitelisted courses. Add a user to "
        "a group."
    ),
    tags={"write", "group"},
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission("course_id")
async def moodle_add_group_members(
    course_id: Annotated[
        int, Field(description="Course ID (must be whitelisted)", gt=0)
    ],
    group_id: Annotated[int, Field(description="Group ID to add the user to", gt=0)],
    user_id: Annotated[int, Field(description="User ID to add to the group", gt=0)],
    ctx: Context = None,
) -> GroupMembershipChange:
    """Add a user to a group (whitelisted courses only)."""
    moodle = get_moodle_client(ctx)

    params = {"members": [{"groupid": group_id, "userid": user_id}]}
    await moodle.call("core_group_add_group_members", params)

    return GroupMembershipChange(
        course_id=course_id,
        group_id=group_id,
        user_ids=[user_id],
        success=True,
        message=f"User {user_id} added to group {group_id}",
    )


@mcp.tool(
    name="moodle_delete_group_members",
    description=(
        "WRITE OPERATION - only works on whitelisted courses. Remove a user "
        "from a group."
    ),
    tags={"write", "group", "destructive"},
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission("course_id")
async def moodle_delete_group_members(
    course_id: Annotated[
        int, Field(description="Course ID (must be whitelisted)", gt=0)
    ],
    group_id: Annotated[
        int, Field(description="Group ID to remove the user from", gt=0)
    ],
    user_id: Annotated[
        int, Field(description="User ID to remove from the group", gt=0)
    ],
    ctx: Context = None,
) -> GroupMembershipChange:
    """Remove a user from a group (whitelisted courses only)."""
    moodle = get_moodle_client(ctx)

    params = {"members": [{"groupid": group_id, "userid": user_id}]}
    await moodle.call("core_group_delete_group_members", params)

    return GroupMembershipChange(
        course_id=course_id,
        group_id=group_id,
        user_ids=[user_id],
        success=True,
        message=f"User {user_id} removed from group {group_id}",
    )


@mcp.tool(
    name="moodle_delete_groups",
    description=(
        "WRITE OPERATION - only works on whitelisted courses. Delete a group "
        "from a course."
    ),
    tags={"write", "group", "destructive"},
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission("course_id")
async def moodle_delete_groups(
    course_id: Annotated[
        int, Field(description="Course ID (must be whitelisted)", gt=0)
    ],
    group_id: Annotated[int, Field(description="Group ID to delete", gt=0)],
    ctx: Context = None,
) -> DeleteGroupsResult:
    """Delete a group from a course (whitelisted courses only)."""
    moodle = get_moodle_client(ctx)

    params = {"groupids": [group_id]}
    await moodle.call("core_group_delete_groups", params)

    return DeleteGroupsResult(
        course_id=course_id,
        group_ids=[group_id],
        success=True,
        message=f"Group {group_id} deleted",
    )
