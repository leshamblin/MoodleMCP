"""
Course management tools - READ operations for courses and categories.
"""

from pydantic import Field
from fastmcp import Context

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors
from ..utils.api_helpers import get_moodle_client, resolve_user_id
from ..utils.formatting import format_response
from ..models.base import ResponseFormat
from ..models.courses import Course, CourseCategory, CourseSection

@mcp.tool(
    name="moodle_list_user_courses",
    description="List all courses where a user is enrolled. REQUIRED: user_id (integer). Optional: include_hidden (boolean, default=False), format (default='markdown'). Example: user_id=624. Use moodle_get_current_user or moodle_get_site_info to get user_id. Returns course IDs needed for other course tools.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_list_user_courses(
    user_id: int | None = Field(None, description="User ID (omit for current user)"),
    include_hidden: bool = Field(False, description="Include hidden courses"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get list of courses where a user is enrolled.

    Returns all courses for the authenticated user (or specified user), including:
    - Course ID, name, and category
    - Start and end dates
    - Visibility status
    - Course format

    Args:
        user_id: Optional user ID (defaults to current authenticated user)
        include_hidden: Whether to include hidden courses
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Formatted list of enrolled courses

    Example use cases:
        - "What courses am I enrolled in?"
        - "List all my active courses"
        - "Show courses for user ID 123"
    """
    moodle = get_moodle_client(ctx)

    # Resolve user_id (defaults to current user if None)
    user_id = await resolve_user_id(moodle, user_id)

    # Get user's courses
    courses_data = await moodle._make_request(
        'core_enrol_get_users_courses',
        {'userid': user_id}
    )

    # Parse courses
    courses = [Course(**course) for course in courses_data]

    # Filter hidden courses if requested
    if not include_hidden:
        courses = [c for c in courses if c.visible]

    if len(courses) == 0:
        return f"No courses found for user {user_id}."

    response_data = {"courses": [c.model_dump() for c in courses], "count": len(courses)}
    return format_response(response_data, f"Enrolled Courses (User {user_id})", format)

@mcp.tool(
    name="moodle_get_course_details",
    description="Get detailed course information including name, description, dates, format, and settings. REQUIRED: course_id (integer). Example: course_id=2292. Use moodle_list_user_courses to discover course IDs.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_course_details(
    course_id: int = Field(description="Course ID to retrieve", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get comprehensive details for a specific course.

    Retrieves full course information including description, dates, settings, and enrollment info.

    Args:
        course_id: Course ID
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Detailed course information

    Example use cases:
        - "Get details for course 42"
        - "Show me information about course ID 15"
        - "What is the description of course 8?"
    """
    moodle = get_moodle_client(ctx)

    # Get course by ID
    courses_data = await moodle._make_request(
        'core_course_get_courses',
        {'options[ids][0]': course_id}
    )

    if not courses_data:
        return f"Course {course_id} not found."

    course = Course(**courses_data[0])

    return format_response(course.model_dump(), f"Course Details: {course.fullname}", format)

@mcp.tool(
    name="moodle_search_courses",
    description="Search for courses by name or description. REQUIRED: search_query (string, min 1 char). Optional: limit (integer, 1-100, default=20). Example: search_query='Python'. Returns course IDs that can be used with other course tools.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_search_courses(
    search_query: str = Field(description="Search term for course name/description", min_length=1),
    limit: int = Field(default=20, description="Maximum results", ge=1, le=100),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Search for courses by name or description.

    Searches across course names, short names, and descriptions.

    Args:
        search_query: Search term
        limit: Maximum number of results
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of matching courses

    Example use cases:
        - "Search for courses about Python"
        - "Find courses with 'calculus' in the name"
        - "Search for computer science courses"
    """
    moodle = get_moodle_client(ctx)

    # Search courses
    search_data = await moodle._make_request(
        'core_course_search_courses',
        {
            'criterianame': 'search',
            'criteriavalue': search_query
        }
    )

    courses_data = search_data.get('courses', [])
    total = search_data.get('total', len(courses_data))

    # Parse and limit results
    courses = [Course(**course) for course in courses_data[:limit]]

    if len(courses) == 0:
        return f"No courses found matching '{search_query}'."

    response_data = {"courses": [c.model_dump() for c in courses], "total": total, "showing": len(courses)}
    return format_response(response_data, f"Search Results: '{search_query}' ({len(courses)} of {total})", format)

@mcp.tool(
    name="moodle_get_course_contents",
    description="Get full course content structure including sections, modules, activities, and resources. REQUIRED: course_id (integer). Example: course_id=2292. Use moodle_list_user_courses to get course_id.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_course_contents(
    course_id: int = Field(description="Course ID", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get complete course structure with sections, modules, and activities.

    Retrieves the course outline including:
    - All sections/topics
    - Modules and activities in each section
    - Module names and types (assignments, quizzes, forums, etc.)
    - Visibility and availability

    Args:
        course_id: Course ID
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Course structure and contents

    Example use cases:
        - "Show me the structure of course 42"
        - "What activities are in course 15?"
        - "List all sections in course 8"
    """
    moodle = get_moodle_client(ctx)

    # Get course contents
    contents_data = await moodle._make_request(
        'core_course_get_contents',
        {'courseid': course_id}
    )

    if not contents_data:
        return f"No content found for course {course_id}."

    # Parse sections
    sections = [CourseSection(**section) for section in contents_data]

    return format_response([s.model_dump() for s in sections], f"Course Contents (Course {course_id})", format)

@mcp.tool(
    name="moodle_get_enrolled_users",
    description="Get list of all users enrolled in a course. REQUIRED: course_id (integer). Optional: limit (1-100, default=20), offset (default=0). Example: course_id=2292. Returns user IDs.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_enrolled_users(
    course_id: int = Field(description="Course ID", gt=0),
    limit: int = Field(default=20, description="Maximum results", ge=1, le=100),
    offset: int = Field(default=0, description="Offset for pagination", ge=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get list of users enrolled in a course.

    Returns enrolled students, teachers, and other participants.

    Args:
        course_id: Course ID
        limit: Maximum number of users to return
        offset: Offset for pagination
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of enrolled users

    Example use cases:
        - "Who is enrolled in course 42?"
        - "List students in course 15"
        - "Show participants in course 8"
    """
    moodle = get_moodle_client(ctx)

    # Get enrolled users
    users_data = await moodle._make_request(
        'core_enrol_get_enrolled_users',
        {'courseid': course_id}
    )

    if not users_data:
        return f"No users found in course {course_id}."

    # Apply pagination
    total = len(users_data)
    users_page = users_data[offset:offset+limit]

    response_data = {
        "users": users_page,
        "total": total,
        "showing": len(users_page),
        "offset": offset
    }
    return format_response(response_data, f"Enrolled Users (Course {course_id})", format)

@mcp.tool(
    name="moodle_get_course_categories",
    description="Get all course categories from the Moodle site. NO PARAMETERS REQUIRED. Optional: format (default='markdown'). Useful for browsing course organization and discovering category IDs.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_course_categories(
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get list of all course categories.

    Returns category information including name, description, parent category, and course count.

    Args:
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of course categories

    Example use cases:
        - "What course categories exist?"
        - "List all course categories"
        - "Show me the category structure"
    """
    moodle = get_moodle_client(ctx)

    # Get categories
    categories_data = await moodle._make_request('core_course_get_categories')

    if not categories_data:
        return "No categories found."

    categories = [CourseCategory(**cat) for cat in categories_data]

    return format_response([c.model_dump() for c in categories], "Course Categories", format)

@mcp.tool(
    name="moodle_get_recent_courses",
    description="Get recently accessed courses for a user, sorted by most recent access. REQUIRED: user_id (integer). Optional: limit (1-50, default=10). Example: user_id=624. Use moodle_get_current_user to get user_id.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_recent_courses(
    user_id: int | None = Field(None, description="User ID (omit for current user)"),
    limit: int = Field(default=10, description="Maximum results", ge=1, le=50),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get recently accessed courses for a user.

    Returns courses sorted by most recent access.

    Args:
        user_id: Optional user ID (defaults to current user)
        limit: Maximum number of courses to return
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of recently accessed courses

    Example use cases:
        - "What courses did I recently access?"
        - "Show my recent courses"
        - "List recently viewed courses"
    """
    moodle = get_moodle_client(ctx)

    # Resolve user_id (defaults to current user if None)
    user_id = await resolve_user_id(moodle, user_id)

    # Get recent courses
    try:
        recent_data = await moodle._make_request(
            'core_course_get_recent_courses',
            {'userid': user_id, 'limit': limit}
        )
        courses = [Course(**course) for course in recent_data]
    except Exception:
        # Fallback to all user courses if recent courses function not available
        courses_data = await moodle._make_request(
            'core_enrol_get_users_courses',
            {'userid': user_id}
        )
        courses = [Course(**course) for course in courses_data[:limit]]

    if len(courses) == 0:
        return f"No recent courses found for user {user_id}."

    return format_response([c.model_dump() for c in courses], f"Recent Courses (User {user_id})", format)

