"""
Course management tools - READ and WRITE operations for courses and categories.
"""

from pydantic import Field
from fastmcp import Context

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors, require_write_permission
from ..utils.api_helpers import get_moodle_client, resolve_user_id
from ..utils.formatting import format_response
from ..models.base import ResponseFormat
from ..models.courses import Course, CourseCategory, CourseSection, CourseModule

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

# ============================================================================
# WRITE OPERATIONS - Course and Category Administration
# ============================================================================
# These functions require ADMIN permissions in Moodle and are restricted by
# whitelist in development mode. Use with extreme caution.

@mcp.tool(
    name="moodle_create_course",
    description="Create a new course (requires admin permissions). REQUIRED: fullname (string), shortname (string), category_id (integer). Optional: summary, format, visible. ADMIN ONLY - requires admin permissions in Moodle. Returns the new course ID.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
@handle_moodle_errors
async def moodle_create_course(
    fullname: str = Field(description="Full name of the course", min_length=1),
    shortname: str = Field(description="Short name/code for the course", min_length=1),
    category_id: int = Field(description="Category ID where course will be created", gt=0),
    summary: str | None = Field(None, description="Course summary/description"),
    course_format: str = Field(default="topics", description="Course format (topics, weeks, social)"),
    visible: bool = Field(default=True, description="Whether course is visible to students"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Create a new course in Moodle.

    WARNING: Requires ADMIN permissions in Moodle.
    This is a write operation that creates new data.

    Args:
        fullname: Full course name
        shortname: Short course code
        category_id: Category to place course in
        summary: Optional course description
        course_format: Course format (topics, weeks, etc.)
        visible: Whether course is visible
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation with new course ID

    Example use cases:
        - "Create a new course called 'Introduction to Python'"
        - "Add a course with shortname 'CS101' in category 5"
    """
    moodle = get_moodle_client(ctx)

    try:
        course_data = {
            'courses[0][fullname]': fullname,
            'courses[0][shortname]': shortname,
            'courses[0][categoryid]': category_id,
            'courses[0][format]': course_format,
            'courses[0][visible]': 1 if visible else 0
        }

        if summary:
            course_data['courses[0][summary]'] = summary

        result = await moodle._make_request(
            'core_course_create_courses',
            course_data
        )

        if result and len(result) > 0:
            new_course = result[0]
            response_data = {
                'course_id': new_course.get('id'),
                'fullname': fullname,
                'shortname': shortname,
                'category_id': category_id,
                'visible': visible
            }
            return format_response(response_data, "Course Created Successfully", format)
        else:
            raise Exception("Failed to create course - no result returned")

    except Exception as e:
        raise Exception(f"Failed to create course: {str(e)}")

@mcp.tool(
    name="moodle_update_course",
    description="Update an existing course (requires admin/teacher permissions). REQUIRED: course_id (integer). Optional: fullname, shortname, summary, visible. ADMIN FUNCTION - requires appropriate permissions. Can only update whitelisted courses in dev mode.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_update_course(
    course_id: int = Field(description="Course ID to update", gt=0),
    fullname: str | None = Field(None, description="New full name"),
    shortname: str | None = Field(None, description="New short name"),
    summary: str | None = Field(None, description="New summary/description"),
    visible: bool | None = Field(None, description="New visibility status"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Update an existing course's properties.

    SAFETY: Only allowed on whitelisted courses in development mode.
    WARNING: Requires ADMIN or TEACHER permissions in Moodle.

    Args:
        course_id: Course ID to update (must be whitelisted!)
        fullname: New full course name
        shortname: New short course code
        summary: New course description
        visible: New visibility status
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation of update

    Raises:
        WriteOperationError: If course_id is not whitelisted

    Example use cases:
        - "Update course 7299 fullname to 'Advanced Python'"
        - "Hide course 7299"
        - "Change course 7299 summary"
    """
    moodle = get_moodle_client(ctx)

    try:
        course_data = {
            'courses[0][id]': course_id
        }

        if fullname is not None:
            course_data['courses[0][fullname]'] = fullname
        if shortname is not None:
            course_data['courses[0][shortname]'] = shortname
        if summary is not None:
            course_data['courses[0][summary]'] = summary
        if visible is not None:
            course_data['courses[0][visible]'] = 1 if visible else 0

        # Check if we have any updates
        if len(course_data) == 1:
            return "No updates specified. Please provide at least one field to update."

        await moodle._make_request(
            'core_course_update_courses',
            course_data
        )

        response_data = {
            'course_id': course_id,
            'updated': True
        }

        return format_response(response_data, f"Course {course_id} Updated", format)

    except Exception as e:
        raise Exception(f"Failed to update course: {str(e)}")

@mcp.tool(
    name="moodle_delete_course",
    description="Delete a course permanently (requires admin permissions). REQUIRED: course_id (integer). DESTRUCTIVE OPERATION - Cannot be undone! ADMIN ONLY - requires admin permissions. Only works on whitelisted courses in dev mode.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,  # DESTRUCTIVE!
        "idempotentHint": True,
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_delete_course(
    course_id: int = Field(description="Course ID to delete (must be whitelisted!)", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    PERMANENTLY delete a course from Moodle.

    DANGER: This is a DESTRUCTIVE operation that CANNOT BE UNDONE!
    All course content, enrollments, grades, and activities will be deleted.

    SAFETY: Only allowed on whitelisted courses in development mode.
    WARNING: Requires ADMIN permissions in Moodle.

    Args:
        course_id: Course ID to delete (must be whitelisted!)
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation of deletion

    Raises:
        WriteOperationError: If course_id is not whitelisted

    Example use cases:
        - "Delete course 7299" (only if whitelisted)
        - "Remove course 7299 permanently"
    """
    moodle = get_moodle_client(ctx)

    try:
        await moodle._make_request(
            'core_course_delete_courses',
            {'courseids[0]': course_id}
        )

        response_data = {
            'course_id': course_id,
            'deleted': True,
            'warning': 'Course has been permanently deleted'
        }

        return format_response(response_data, f"Course {course_id} Deleted", format)

    except Exception as e:
        raise Exception(f"Failed to delete course: {str(e)}")

@mcp.tool(
    name="moodle_duplicate_course",
    description="Duplicate an existing course (requires admin/teacher permissions). REQUIRED: course_id (integer), fullname (string), shortname (string), category_id (integer). Optional: visible. ADMIN FUNCTION - requires appropriate permissions. Source course must be whitelisted in dev mode.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_duplicate_course(
    course_id: int = Field(description="Source course ID to duplicate (must be whitelisted!)", gt=0),
    fullname: str = Field(description="Full name for new course", min_length=1),
    shortname: str = Field(description="Short name for new course", min_length=1),
    category_id: int = Field(description="Category ID for new course", gt=0),
    visible: bool = Field(default=True, description="Whether new course is visible"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Duplicate an existing course with all its activities and settings.

    SAFETY: Source course must be whitelisted in development mode.
    WARNING: Requires ADMIN or TEACHER permissions in Moodle.

    Args:
        course_id: Source course to duplicate (must be whitelisted!)
        fullname: Full name for new course
        shortname: Short name for new course
        category_id: Category to place new course in
        visible: Whether new course is visible
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation with new course ID

    Raises:
        WriteOperationError: If source course_id is not whitelisted

    Example use cases:
        - "Duplicate course 7299 as 'Test Course Copy'"
        - "Copy course 7299 to category 5"
    """
    moodle = get_moodle_client(ctx)

    try:
        params = {
            'courseid': course_id,
            'fullname': fullname,
            'shortname': shortname,
            'categoryid': category_id,
            'visible': 1 if visible else 0
        }

        result = await moodle._make_request(
            'core_course_duplicate_course',
            params
        )

        response_data = {
            'source_course_id': course_id,
            'new_course_id': result.get('id') if result else None,
            'fullname': fullname,
            'shortname': shortname
        }

        return format_response(response_data, "Course Duplicated Successfully", format)

    except Exception as e:
        raise Exception(f"Failed to duplicate course: {str(e)}")

@mcp.tool(
    name="moodle_import_course_content",
    description="Import content from one course to another (requires admin/teacher permissions). REQUIRED: source_course_id (integer), dest_course_id (integer). Both courses must be whitelisted in dev mode. ADMIN FUNCTION - requires appropriate permissions.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('source_course_id')
@require_write_permission('dest_course_id')
async def moodle_import_course_content(
    source_course_id: int = Field(description="Source course ID to import from (must be whitelisted!)", gt=0),
    dest_course_id: int = Field(description="Destination course ID to import to (must be whitelisted!)", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Import activities and content from one course to another.

    SAFETY: Both courses must be whitelisted in development mode.
    WARNING: Requires ADMIN or TEACHER permissions in Moodle.

    This copies course content but not enrollments or grades.

    Args:
        source_course_id: Source course to copy from (must be whitelisted!)
        dest_course_id: Destination course to copy to (must be whitelisted!)
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation of import

    Raises:
        WriteOperationError: If either course is not whitelisted

    Example use cases:
        - "Import content from course 7299 to course 7300"
        - "Copy activities from course 7299"
    """
    moodle = get_moodle_client(ctx)

    try:
        params = {
            'importfrom': source_course_id,
            'importto': dest_course_id,
            'deletecontent': 0  # Don't delete existing content
        }

        await moodle._make_request(
            'core_course_import_course',
            params
        )

        response_data = {
            'source_course_id': source_course_id,
            'dest_course_id': dest_course_id,
            'imported': True
        }

        return format_response(response_data, "Course Content Imported", format)

    except Exception as e:
        raise Exception(f"Failed to import course content: {str(e)}")

@mcp.tool(
    name="moodle_create_course_category",
    description="Create a new course category (requires admin permissions). REQUIRED: name (string). Optional: parent_id, description, visible. ADMIN ONLY - requires admin permissions in Moodle. Returns the new category ID.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
@handle_moodle_errors
async def moodle_create_course_category(
    name: str = Field(description="Category name", min_length=1),
    parent_id: int = Field(default=0, description="Parent category ID (0 for top level)", ge=0),
    description: str | None = Field(None, description="Category description"),
    visible: bool = Field(default=True, description="Whether category is visible"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Create a new course category in Moodle.

    WARNING: Requires ADMIN permissions in Moodle.
    This is a write operation that creates new data.

    Args:
        name: Category name
        parent_id: Parent category ID (0 for root level)
        description: Optional category description
        visible: Whether category is visible
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation with new category ID

    Example use cases:
        - "Create a category called 'Computer Science'"
        - "Add a subcategory under category 5"
    """
    moodle = get_moodle_client(ctx)

    try:
        category_data = {
            'categories[0][name]': name,
            'categories[0][parent]': parent_id,
            'categories[0][visible]': 1 if visible else 0
        }

        if description:
            category_data['categories[0][description]'] = description

        result = await moodle._make_request(
            'core_course_create_categories',
            category_data
        )

        if result and len(result) > 0:
            new_category = result[0]
            response_data = {
                'category_id': new_category.get('id'),
                'name': name,
                'parent_id': parent_id,
                'visible': visible
            }
            return format_response(response_data, "Category Created Successfully", format)
        else:
            raise Exception("Failed to create category - no result returned")

    except Exception as e:
        raise Exception(f"Failed to create category: {str(e)}")

@mcp.tool(
    name="moodle_delete_course_category",
    description="Delete a course category permanently (requires admin permissions). REQUIRED: category_id (integer). Optional: recursive (boolean, default=False). DESTRUCTIVE OPERATION - Cannot be undone! ADMIN ONLY. If recursive=True, deletes all courses in category!",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,  # DESTRUCTIVE!
        "idempotentHint": True,
        "openWorldHint": False
    }
)
@handle_moodle_errors
async def moodle_delete_course_category(
    category_id: int = Field(description="Category ID to delete", gt=0),
    recursive: bool = Field(default=False, description="Also delete all courses in category (DANGEROUS!)"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    PERMANENTLY delete a course category from Moodle.

    DANGER: This is a DESTRUCTIVE operation that CANNOT BE UNDONE!
    If recursive=True, ALL COURSES in this category will also be deleted!

    WARNING: Requires ADMIN permissions in Moodle.

    Args:
        category_id: Category ID to delete
        recursive: If True, delete all courses in category (DANGEROUS!)
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation of deletion

    Example use cases:
        - "Delete empty category 15"
        - "Remove category 20 and all its courses" (recursive)
    """
    moodle = get_moodle_client(ctx)

    try:
        params = {
            'categories[0][id]': category_id,
            'categories[0][recursive]': 1 if recursive else 0
        }

        await moodle._make_request(
            'core_course_delete_categories',
            params
        )

        response_data = {
            'category_id': category_id,
            'deleted': True,
            'recursive': recursive,
            'warning': 'Category has been permanently deleted' +
                      (' along with all its courses' if recursive else '')
        }

        return format_response(response_data, f"Category {category_id} Deleted", format)

    except Exception as e:
        raise Exception(f"Failed to delete category: {str(e)}")
