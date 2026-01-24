"""
Group management tools - READ and WRITE operations for managing course groups.
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
    name="moodle_get_course_groups",
    description="Get all groups in a course. REQUIRED: course_id (integer). Example: course_id=2292. Use moodle_list_user_courses to get course_id. Returns group IDs, names, and descriptions.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_course_groups(
    course_id: int = Field(description="Course ID", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get list of all groups in a course.

    Returns group information including ID, name, description, and member count.

    Args:
        course_id: Course ID
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of groups in the course

    Example use cases:
        - "What groups exist in course 42?"
        - "List all groups in course 15"
        - "Show me the groups for course 2292"
    """
    moodle = get_moodle_client(ctx)

    # Get groups for course
    groups_data = await moodle._make_request(
        'core_group_get_course_groups',
        {'courseid': course_id}
    )

    if not groups_data:
        return f"No groups found in course {course_id}."

    return format_response(groups_data, f"Groups in Course {course_id}", format)

@mcp.tool(
    name="moodle_get_course_groupings",
    description="Get all groupings in a course. REQUIRED: course_id (integer). Example: course_id=2292. Groupings are collections of groups. Returns grouping IDs, names, and descriptions.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_course_groupings(
    course_id: int = Field(description="Course ID", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get list of all groupings in a course.

    Groupings are collections of groups that can be used together.
    Returns grouping information including ID, name, and description.

    Args:
        course_id: Course ID
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of groupings in the course

    Example use cases:
        - "What groupings exist in course 42?"
        - "List all groupings in course 15"
        - "Show me the groupings for course 2292"
    """
    moodle = get_moodle_client(ctx)

    # Get groupings for course
    groupings_data = await moodle._make_request(
        'core_group_get_course_groupings',
        {'courseid': course_id}
    )

    if not groupings_data:
        return f"No groupings found in course {course_id}."

    return format_response(groupings_data, f"Groupings in Course {course_id}", format)

@mcp.tool(
    name="moodle_get_activity_allowed_groups",
    description="Get groups that can access a specific course module/activity. REQUIRED: cmid (course module ID, integer). Returns groups with access to the activity.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_activity_allowed_groups(
    cmid: int = Field(description="Course module ID (activity ID)", gt=0),
    user_id: int | None = Field(None, description="User ID (omit for current user)"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get groups allowed to access a specific activity.

    Returns groups that have access to a course module (activity) based on
    the activity's group mode and group restrictions.

    Args:
        cmid: Course module ID
        user_id: Optional user ID (defaults to current user)
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of groups with access to the activity

    Example use cases:
        - "What groups can access activity 123?"
        - "Show groups for course module 456"
        - "Which groups are allowed in this assignment?"
    """
    moodle = get_moodle_client(ctx)

    params = {'cmid': cmid}
    if user_id is not None:
        params['userid'] = user_id

    # Get allowed groups for activity
    groups_data = await moodle._make_request(
        'core_group_get_activity_allowed_groups',
        params
    )

    if not groups_data or not groups_data.get('groups'):
        return f"No groups found for activity {cmid}."

    groups = groups_data.get('groups', [])
    return format_response(groups, f"Groups for Activity {cmid}", format)

@mcp.tool(
    name="moodle_get_activity_groupmode",
    description="Get the group mode for a specific course module/activity. REQUIRED: cmid (course module ID, integer). Returns: 0 (no groups), 1 (separate groups), or 2 (visible groups).",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_activity_groupmode(
    cmid: int = Field(description="Course module ID (activity ID)", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get group mode for a specific activity.

    Group modes:
    - 0: No groups
    - 1: Separate groups (students can only see their own group)
    - 2: Visible groups (students can see all groups but work in their own)

    Args:
        cmid: Course module ID
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Group mode information for the activity

    Example use cases:
        - "What is the group mode for activity 123?"
        - "Does activity 456 use groups?"
        - "Show group settings for this assignment"
    """
    moodle = get_moodle_client(ctx)

    # Get group mode for activity
    result = await moodle._make_request(
        'core_group_get_activity_groupmode',
        {'cmid': cmid}
    )

    if format == ResponseFormat.JSON:
        return format_response(result, None, format)

    # Format markdown with interpretation
    groupmode = result.get('groupmode', 0)
    groupmode_str = {
        0: "No groups",
        1: "Separate groups (students see only their group)",
        2: "Visible groups (students see all groups)"
    }.get(groupmode, f"Unknown ({groupmode})")

    lines = [
        f"# Group Mode for Activity {cmid}\n",
        f"**Group Mode:** {groupmode_str}",
        f"**Group Mode Value:** {groupmode}"
    ]

    if result.get('forced'):
        lines.append(f"**Forced:** Yes (cannot be changed at activity level)")

    return "\n".join(lines)

@mcp.tool(
    name="moodle_get_course_user_groups",
    description="Get all groups a specific user belongs to in a course. REQUIRED: course_id (integer), user_id (integer). Example: course_id=2292, user_id=624. Returns the user's group memberships.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_course_user_groups(
    course_id: int = Field(description="Course ID", gt=0),
    user_id: int | None = Field(None, description="User ID (omit for current user)"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get all groups a user belongs to in a specific course.

    Returns information about which groups the user is a member of,
    including group IDs, names, and descriptions.

    Args:
        course_id: Course ID
        user_id: User ID (defaults to current user if not specified)
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of groups the user belongs to in the course

    Example use cases:
        - "What groups am I in for course 2292?"
        - "Show user 624's groups in course 42"
        - "Which groups is this student member of?"
    """
    moodle = get_moodle_client(ctx)

    # Resolve user_id if not provided
    from ..utils.api_helpers import resolve_user_id
    user_id = await resolve_user_id(moodle, user_id)

    # Get user's groups in the course
    groups_data = await moodle._make_request(
        'core_group_get_course_user_groups',
        {
            'courseid': course_id,
            'userid': user_id
        }
    )

    if not groups_data or not groups_data.get('groups'):
        return f"User {user_id} is not in any groups in course {course_id}."

    groups = groups_data.get('groups', [])
    return format_response(groups, f"User {user_id}'s Groups in Course {course_id}", format)

@mcp.tool(
    name="moodle_get_groups_for_selector",
    description="Get groups for use in a selector/dropdown. REQUIRED: course_id (integer). Optional: group_id (integer). Returns groups formatted for selection interfaces.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_groups_for_selector(
    course_id: int = Field(description="Course ID", gt=0),
    group_id: int | None = Field(None, description="Optional group ID to highlight"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get groups formatted for use in a selector interface.

    This is useful for getting a clean list of groups suitable for
    dropdown menus, selectors, or other UI elements.

    Args:
        course_id: Course ID
        group_id: Optional group ID to highlight in the results
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Groups formatted for selector use

    Example use cases:
        - "Get groups for selector in course 2292"
        - "Show selectable groups in course 42"
        - "List groups for dropdown menu"
    """
    moodle = get_moodle_client(ctx)

    params = {'courseid': course_id}
    if group_id is not None:
        params['groupid'] = group_id

    # Get groups for selector
    groups_data = await moodle._make_request(
        'core_group_get_groups_for_selector',
        params
    )

    if not groups_data or not groups_data.get('groups'):
        return f"No groups available for selector in course {course_id}."

    groups = groups_data.get('groups', [])
    return format_response(groups, f"Groups for Selector (Course {course_id})", format)

@mcp.tool(
    name="moodle_get_group_members",
    description="Get members of a group. REQUIRED: group_id (integer). Example: group_id=456. Returns list of user IDs and names in the group.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_group_members(
    group_id: int = Field(description="Group ID", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get list of members in a group.

    Returns all users who are members of the specified group.

    Args:
        group_id: Group ID
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of group members

    Example use cases:
        - "Who is in group 456?"
        - "List members of group 123"
        - "Show group members"
    """
    moodle = get_moodle_client(ctx)

    try:
        members_data = await moodle._make_request(
            'core_group_get_group_members',
            {'groupids[0]': group_id}
        )

        members = members_data[0].get('userids', []) if members_data else []

        response_data = {
            'group_id': group_id,
            'member_count': len(members),
            'members': members
        }
        return format_response(response_data, f"Group Members (Group {group_id})", format)
    except Exception as e:
        return f"Unable to retrieve group members. Error: {str(e)}"

# ============================================================================
# WRITE OPERATIONS - Require write permission for group management
# ============================================================================

@mcp.tool(
    name="moodle_create_groups",
    description="Create one or more groups in a course. REQUIRED: course_id (integer), groups (array of objects with name and optional description). WRITE OPERATION - only works on whitelisted courses (default: course 7299). Example: course_id=7299, groups=[{'name':'Team A','description':'Project team A'}].",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,  # Creates new groups each time
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_create_groups(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    groups: list[dict] = Field(description="List of {name: str, description?: str} objects", min_length=1),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Create one or more groups in a course.

    SAFETY: This write operation is only allowed on whitelisted courses.
    Default whitelist: [7299] (Elizabeth's Moodle Playground)

    Creates new groups with specified names and optional descriptions.

    Args:
        course_id: Course ID (must be in whitelist!)
        groups: List of dictionaries with 'name' and optional 'description'
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation with created group IDs

    Raises:
        WriteOperationError: If course_id is not whitelisted

    Example use cases:
        - "Create a group called Team A"
        - "Create groups for my project teams"
        - "Make new groups Team 1, Team 2, Team 3"
    """
    moodle = get_moodle_client(ctx)

    try:
        # Prepare group data
        params = {}
        for idx, group_data in enumerate(groups):
            params[f'groups[{idx}][courseid]'] = course_id
            params[f'groups[{idx}][name]'] = group_data.get('name')
            if group_data.get('description'):
                params[f'groups[{idx}][description]'] = group_data.get('description')

        result = await moodle._make_request(
            'core_group_create_groups',
            params
        )

        created_groups = result if isinstance(result, list) else []

        response_data = {
            'course_id': course_id,
            'groups_created': len(created_groups),
            'groups': created_groups
        }

        return format_response(response_data, "Groups Created", format)
    except Exception as e:
        raise Exception(f"Failed to create groups: {str(e)}")

@mcp.tool(
    name="moodle_add_group_members",
    description="Add users to a group. REQUIRED: course_id (integer), group_id (integer), user_ids (array of integers). WRITE OPERATION - only works on whitelisted courses (default: course 7299). Example: course_id=7299, group_id=456, user_ids=[123,789].",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,  # Safe to add same user multiple times
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_add_group_members(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    group_id: int = Field(description="Group ID", gt=0),
    user_ids: list[int] = Field(description="List of user IDs to add", min_length=1),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Add users to a group.

    SAFETY: This write operation is only allowed on whitelisted courses.
    Default whitelist: [7299] (Elizabeth's Moodle Playground)

    Adds the specified users to the group. Users must be enrolled in the course.

    Args:
        course_id: Course ID (must be in whitelist!)
        group_id: Group ID to add members to
        user_ids: List of user IDs to add
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation of added members

    Raises:
        WriteOperationError: If course_id is not whitelisted

    Example use cases:
        - "Add user 123 to group 456"
        - "Add students to Team A"
        - "Put users 123, 456, 789 in group 12"
    """
    moodle = get_moodle_client(ctx)

    try:
        # Prepare member data
        params = {}
        for idx, user_id in enumerate(user_ids):
            params[f'members[{idx}][groupid]'] = group_id
            params[f'members[{idx}][userid]'] = user_id

        result = await moodle._make_request(
            'core_group_add_group_members',
            params
        )

        response_data = {
            'course_id': course_id,
            'group_id': group_id,
            'members_added': len(user_ids),
            'user_ids': user_ids
        }

        return format_response(response_data, "Group Members Added", format)
    except Exception as e:
        raise Exception(f"Failed to add group members: {str(e)}")

@mcp.tool(
    name="moodle_delete_group_members",
    description="Remove users from a group. REQUIRED: course_id (integer), group_id (integer), user_ids (array of integers). WRITE OPERATION - DESTRUCTIVE - only works on whitelisted courses (default: course 7299). Example: course_id=7299, group_id=456, user_ids=[123].",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,  # Removes members
        "idempotentHint": True,   # Safe to call multiple times
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_delete_group_members(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    group_id: int = Field(description="Group ID", gt=0),
    user_ids: list[int] = Field(description="List of user IDs to remove", min_length=1),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Remove users from a group.

    SAFETY: This write operation is only allowed on whitelisted courses.
    Default whitelist: [7299] (Elizabeth's Moodle Playground)

    WARNING: This removes users from the group. They will no longer have
    access to group-specific activities.

    Args:
        course_id: Course ID (must be in whitelist!)
        group_id: Group ID to remove members from
        user_ids: List of user IDs to remove
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation of removed members

    Raises:
        WriteOperationError: If course_id is not whitelisted

    Example use cases:
        - "Remove user 123 from group 456"
        - "Delete student from Team A"
        - "Remove users from group"
    """
    moodle = get_moodle_client(ctx)

    try:
        # Prepare member removal data
        params = {}
        for idx, user_id in enumerate(user_ids):
            params[f'members[{idx}][groupid]'] = group_id
            params[f'members[{idx}][userid]'] = user_id

        result = await moodle._make_request(
            'core_group_delete_group_members',
            params
        )

        response_data = {
            'course_id': course_id,
            'group_id': group_id,
            'members_removed': len(user_ids),
            'user_ids': user_ids
        }

        return format_response(response_data, "Group Members Removed", format)
    except Exception as e:
        raise Exception(f"Failed to remove group members: {str(e)}")

@mcp.tool(
    name="moodle_delete_groups",
    description="Delete one or more groups from a course. REQUIRED: course_id (integer), group_ids (array of integers). WRITE OPERATION - DESTRUCTIVE - only works on whitelisted courses (default: course 7299). WARNING: Permanently deletes groups and all their data. Example: course_id=7299, group_ids=[456,789].",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,  # Permanently deletes groups
        "idempotentHint": True,   # Safe to call multiple times (already deleted groups are ignored)
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_delete_groups(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    group_ids: list[int] = Field(description="List of group IDs to delete", min_length=1),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Delete one or more groups from a course.

    SAFETY: This write operation is only allowed on whitelisted courses.
    Default whitelist: [7299] (Elizabeth's Moodle Playground)

    WARNING: This permanently deletes groups and all their associated data.
    All group members will be removed from the group. Group-specific settings,
    submissions, and activities will be affected.

    Args:
        course_id: Course ID (must be in whitelist!)
        group_ids: List of group IDs to delete
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation of deleted groups

    Raises:
        WriteOperationError: If course_id is not whitelisted

    Example use cases:
        - "Delete group 456"
        - "Remove groups 123 and 456 from the course"
        - "Delete the old project groups"
    """
    moodle = get_moodle_client(ctx)

    try:
        # Prepare group deletion data
        params = {}
        for idx, group_id in enumerate(group_ids):
            params[f'groupids[{idx}]'] = group_id

        result = await moodle._make_request(
            'core_group_delete_groups',
            params
        )

        response_data = {
            'course_id': course_id,
            'groups_deleted': len(group_ids),
            'group_ids': group_ids
        }

        return format_response(response_data, "Groups Deleted", format)
    except Exception as e:
        raise Exception(f"Failed to delete groups: {str(e)}")
