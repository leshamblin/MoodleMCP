"""
User management tools - READ ONLY.
"""

from pydantic import Field
from fastmcp import Context

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors
from ..utils.api_helpers import get_moodle_client, resolve_user_id
from ..utils.formatting import format_response
from ..models.base import ResponseFormat
from ..models.users import User

@mcp.tool(
    name="moodle_get_current_user",
    description="Get profile for currently authenticated user including user ID. NO PARAMETERS REQUIRED. Returns userid field (e.g., 624) needed for many other tools. Use this FIRST to discover your user_id. Optional: format (default='markdown').",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_current_user(
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get detailed profile information for the currently authenticated user.

    Returns comprehensive user profile including ID, name, email, institution, and preferences.

    Args:
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Current user profile information

    Example use cases:
        - "Who am I logged in as?"
        - "Show my user profile"
        - "What is my user ID?"
    """
    moodle = get_moodle_client(ctx)

    # Get site info which includes current user details
    site_info = await moodle.get_site_info()

    return format_response(site_info, "Current User Profile", format)

@mcp.tool(
    name="moodle_get_user_profile",
    description="Get detailed user profile information. REQUIRED: user_id (integer). Example: user_id=624. Use moodle_get_current_user or moodle_search_users to get user_id.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_user_profile(
    user_id: int = Field(description="User ID to retrieve", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get detailed profile for a specific user.

    Retrieves user information including name, email, profile image, department, institution, and more.

    Args:
        user_id: User ID
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        User profile information

    Example use cases:
        - "Get profile for user 123"
        - "Show details for user ID 45"
        - "Who is user 67?"
    """
    moodle = get_moodle_client(ctx)

    # Get user by ID
    users_data = await moodle._make_request(
        'core_user_get_users_by_field',
        {'field': 'id', 'values[0]': user_id}
    )

    if not users_data:
        return f"User {user_id} not found."

    user = User(**users_data[0])

    return format_response(user.model_dump(), f"User Profile: {user.fullname or user.username}", format)

@mcp.tool(
    name="moodle_search_users",
    description="Search for users by name or email. REQUIRED: search_query (string, min 2 chars). Optional: limit (1-100, default=20). Example: search_query='Smith'. Returns user IDs.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_search_users(
    search_query: str = Field(description="Search term (name or email)", min_length=2),
    limit: int = Field(default=20, description="Maximum results", ge=1, le=100),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Search for users by name or email.

    Searches across user names (first, last, full) and email addresses.

    Args:
        search_query: Search term
        limit: Maximum number of results
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of matching users

    Example use cases:
        - "Search for users named John"
        - "Find users with email containing '@example.com'"
        - "Search for Smith"
    """
    moodle = get_moodle_client(ctx)

    # Search using fullname criterion
    users_data = await moodle._make_request(
        'core_user_get_users',
        {
            'criteria[0][key]': 'fullname',
            'criteria[0][value]': search_query
        }
    )

    users_list = users_data.get('users', [])[:limit]

    if len(users_list) == 0:
        return f"No users found matching '{search_query}'."

    users = [User(**user) for user in users_list]

    return format_response([u.model_dump() for u in users], f"User Search Results: '{search_query}'", format)

@mcp.tool(
    name="moodle_get_user_preferences",
    description="Get user preferences and settings. REQUIRED: user_id (integer). Example: user_id=624. Use moodle_get_current_user to get user_id.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_user_preferences(
    user_id: int | None = Field(None, description="User ID (omit for current user)"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get user preferences and settings.

    Returns user-specific settings like language, theme, email format, etc.

    Args:
        user_id: Optional user ID (defaults to current user)
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        User preferences

    Example use cases:
        - "Show my preferences"
        - "What are user 123's preferences?"
        - "Get language settings for current user"
    """
    moodle = get_moodle_client(ctx)

    # Resolve user_id (defaults to current user if None)
    user_id = await resolve_user_id(moodle, user_id)

    # Get user preferences
    try:
        prefs_data = await moodle._make_request(
            'core_user_get_user_preferences',
            {'userid': user_id}
        )
        preferences = prefs_data.get('preferences', [])
    except Exception:
        # Fallback to basic user info if preferences not available
        users_data = await moodle._make_request(
            'core_user_get_users_by_field',
            {'field': 'id', 'values[0]': user_id}
        )
        if users_data:
            user = users_data[0]
            preferences = {
                'lang': user.get('lang'),
                'theme': user.get('theme'),
                'timezone': user.get('timezone'),
                'mailformat': user.get('mailformat')
            }
        else:
            return f"Could not retrieve preferences for user {user_id}."

    return format_response(preferences, f"User Preferences (User {user_id})", format)

@mcp.tool(
    name="moodle_get_course_participants",
    description="Get all participants (students, teachers, etc.) in a course with their roles. REQUIRED: course_id (integer). Optional: limit (1-100, default=20). Example: course_id=2292. Returns user IDs and role information.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_course_participants(
    course_id: int = Field(description="Course ID", gt=0),
    limit: int = Field(default=20, description="Maximum results", ge=1, le=100),
    offset: int = Field(default=0, description="Offset for pagination", ge=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get list of participants in a course with their roles.

    Returns all enrolled users including students, teachers, and other roles.

    Args:
        course_id: Course ID
        limit: Maximum number of participants to return
        offset: Offset for pagination
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of course participants with roles

    Example use cases:
        - "Who are the participants in course 42?"
        - "List teachers in course 15"
        - "Show all users in course 8"
    """
    moodle = get_moodle_client(ctx)

    # Get enrolled users (participants)
    users_data = await moodle._make_request(
        'core_enrol_get_enrolled_users',
        {'courseid': course_id}
    )

    if not users_data:
        return f"No participants found in course {course_id}."

    # Apply pagination
    total = len(users_data)
    users_page = users_data[offset:offset+limit]

    response_data = {
        "participants": users_page,
        "total": total,
        "showing": len(users_page)
    }
    return format_response(response_data, f"Course Participants (Course {course_id})", format)
