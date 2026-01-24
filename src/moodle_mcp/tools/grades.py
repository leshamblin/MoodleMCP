"""
Grade and gradebook tools - READ and WRITE operations.
"""

from pydantic import Field
from fastmcp import Context

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors, require_write_permission
from ..utils.api_helpers import get_moodle_client, resolve_user_id
from ..utils.formatting import format_response
from ..models.base import ResponseFormat

# ============================================================================
# READ OPERATIONS
# ============================================================================

@mcp.tool(
    name="moodle_get_user_grades",
    description="Get user's grades for all items in a specific course. REQUIRED: course_id (integer), user_id (integer). Example: course_id=2292, user_id=624.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_user_grades(
    user_id: int | None = Field(None, description="User ID (omit for current user)"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get comprehensive grade information for a user across all enrolled courses.

    Returns grades for all graded activities in all courses where the user is enrolled.

    Args:
        user_id: Optional user ID (defaults to current user)
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Complete grade information for the user

    Example use cases:
        - "What are my grades?"
        - "Show all grades for user 123"
        - "Get my course grades"
    """
    moodle = get_moodle_client(ctx)

    # Resolve user_id to current user if not provided


    user_id = await resolve_user_id(moodle, user_id)

    # Get user's courses first
    courses_data = await moodle._make_request(
        'core_enrol_get_users_courses',
        {'userid': user_id}
    )

    if not courses_data:
        return f"No courses found for user {user_id}."

    # Get grades for each course
    all_grades = []
    for course in courses_data:
        try:
            grades_data = await moodle._make_request(
                'gradereport_user_get_grade_items',
                {'courseid': course['id'], 'userid': user_id}
            )
            if grades_data and 'usergrades' in grades_data:
                all_grades.append({
                    'course': course['fullname'],
                    'courseid': course['id'],
                    'grades': grades_data['usergrades']
                })
        except Exception:
            continue  # Skip courses where grades can't be retrieved

    if not all_grades:
        return f"No grade information available for user {user_id}."

    return format_response(all_grades, f"Grades for User {user_id}", format)

@mcp.tool(
    name="moodle_get_course_grades",
    description="Get all grade items and grades for a course. REQUIRED: course_id (integer), user_id (integer). Example: course_id=2292, user_id=624. Use moodle_list_user_courses to get course_id.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_course_grades(
    course_id: int = Field(description="Course ID", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get gradebook for a course (instructor/admin view).

    Returns all grade items and categories for a course. Requires appropriate permissions.

    Args:
        course_id: Course ID
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Course gradebook information

    Example use cases:
        - "Show gradebook for course 42"
        - "What are the grade items in course 15?"
    """
    moodle = get_moodle_client(ctx)

    # Get grade items for course
    try:
        grades_data = await moodle._make_request(
            'core_grades_get_gradeitems',
            {'courseid': course_id}
        )
    except Exception as e:
        return f"Unable to retrieve grades for course {course_id}. You may not have permission. Error: {str(e)}"

    if not grades_data:
        return f"No grade items found for course {course_id}."

    return format_response(grades_data, f"Gradebook for Course {course_id}", format)

@mcp.tool(
    name="moodle_get_grade_items",
    description="Get all gradable items (assignments, quizzes, etc.) in a course. REQUIRED: course_id (integer). Optional: user_id (integer) for specific user's grades. Example: course_id=2292.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_grade_items(
    course_id: int = Field(description="Course ID", gt=0),
    user_id: int | None = Field(None, description="Optional user ID to get specific user's grades"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get list of grade items (graded activities) for a course.

    Shows all graded activities, assignments, quizzes, etc. in a course.
    Optionally includes grades for a specific user.

    Args:
        course_id: Course ID
        user_id: Optional user ID to include grades
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of grade items

    Example use cases:
        - "What are the graded items in course 42?"
        - "List all assignments and quizzes in course 15"
        - "Show grade items for course 8 with my grades"
    """
    moodle = get_moodle_client(ctx)

    # If user_id specified, get their grade items
    if user_id:
        grades_data = await moodle._make_request(
            'gradereport_user_get_grade_items',
            {'courseid': course_id, 'userid': user_id}
        )
    else:
        # Get grade items only
        grades_data = await moodle._make_request(
            'core_grades_get_gradeitems',
            {'courseid': course_id}
        )

    if not grades_data:
        return f"No grade items found for course {course_id}."

    return format_response(grades_data, f"Grade Items for Course {course_id}", format)

@mcp.tool(
    name="moodle_get_student_grade_summary",
    description="Get grade summary with statistics for a student in a course. REQUIRED: course_id (integer), user_id (integer). Example: course_id=2292, user_id=624.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_student_grade_summary(
    course_id: int = Field(description="Course ID", gt=0),
    user_id: int | None = Field(None, description="User ID (omit for current user)"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get grade summary for a student in a specific course.

    Returns overall course grade and individual activity grades.

    Args:
        course_id: Course ID
        user_id: Optional user ID (defaults to current user)
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Grade summary for the course

    Example use cases:
        - "What's my grade in course 42?"
        - "Show grade summary for course 15"
        - "Get student 123's grades in course 8"
    """
    moodle = get_moodle_client(ctx)

    # Resolve user_id to current user if not provided


    user_id = await resolve_user_id(moodle, user_id)

    # Get grade items for user in course
    grades_data = await moodle._make_request(
        'gradereport_user_get_grade_items',
        {'courseid': course_id, 'userid': user_id}
    )

    if not grades_data or 'usergrades' not in grades_data:
        return f"No grades found for user {user_id} in course {course_id}."

    return format_response(grades_data, f"Grade Summary: Course {course_id}, User {user_id}", format)

@mcp.tool(
    name="moodle_get_gradebook_overview",
    description="Get overview of all grades for a user across all enrolled courses. REQUIRED: user_id (integer). Example: user_id=624. Use moodle_get_current_user to get user_id.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_gradebook_overview(
    user_id: int | None = Field(None, description="User ID (omit for current user)"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get overview of grades across all courses for a user.

    Shows course-level grade summary for all enrolled courses.

    Args:
        user_id: Optional user ID (defaults to current user)
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Grade overview across all courses

    Example use cases:
        - "Show my grade overview"
        - "What are my course grades?"
        - "Get gradebook overview for user 123"
    """
    moodle = get_moodle_client(ctx)

    # Resolve user_id to current user if not provided


    user_id = await resolve_user_id(moodle, user_id)

    try:
        overview_data = await moodle._make_request(
            'gradereport_overview_get_course_grades',
            {'userid': user_id}
        )
    except Exception:
        # Fallback: get courses and try to get grades for each
        courses_data = await moodle._make_request(
            'core_enrol_get_users_courses',
            {'userid': user_id}
        )
        overview_data = {'grades': [{'courseid': c['id'], 'coursename': c['fullname']} for c in courses_data]}

    if not overview_data:
        return f"No grade overview available for user {user_id}."

    return format_response(overview_data, f"Grade Overview for User {user_id}", format)

@mcp.tool(
    name="moodle_get_grade_report",
    description="Get complete grade report for a user in a course. REQUIRED: course_id (integer), user_id (integer). Example: course_id=2292, user_id=624.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_grade_report(
    course_id: int = Field(description="Course ID", gt=0),
    user_id: int | None = Field(None, description="User ID (omit for current user)"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get comprehensive grade report for a user in a course.

    Provides detailed grading information including all activities, weights, and calculations.

    Args:
        course_id: Course ID
        user_id: Optional user ID (defaults to current user)
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Detailed grade report

    Example use cases:
        - "Show detailed grade report for course 42"
        - "Get my complete grades in course 15"
        - "Detailed grade breakdown for user 123 in course 8"
    """
    moodle = get_moodle_client(ctx)

    # Resolve user_id to current user if not provided


    user_id = await resolve_user_id(moodle, user_id)

    # Get comprehensive grade report
    report_data = await moodle._make_request(
        'gradereport_user_get_grade_items',
        {'courseid': course_id, 'userid': user_id}
    )

    if not report_data:
        return f"No grade report available for user {user_id} in course {course_id}."

    return format_response(report_data, "Grade Report", format)

# ============================================================================
# WRITE OPERATIONS - Require write permission for grading
# ============================================================================

@mcp.tool(
    name="moodle_save_assignment_grade",
    description="Grade an assignment submission. REQUIRED: course_id (integer), assignment_id (integer), user_id (integer), grade (number). Optional: feedback_text (string). WRITE OPERATION - only works on whitelisted courses (default: course 7299). Example: course_id=7299, assignment_id=123, user_id=456, grade=85, feedback_text='Good work!'.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,  # Safe to update grade
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_save_assignment_grade(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    assignment_id: int = Field(description="Assignment ID", gt=0),
    user_id: int = Field(description="User ID to grade", gt=0),
    grade: float = Field(description="Grade value (must be within assignment's grading scale)", ge=0),
    feedback_text: str | None = Field(None, description="Optional feedback text for student"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Grade an assignment submission for a user.

    SAFETY: This write operation is only allowed on whitelisted courses.
    Default whitelist: [7299] (Elizabeth's Moodle Playground)

    Saves the grade and optional feedback for the student's submission.

    Args:
        course_id: Course ID (must be in whitelist!)
        assignment_id: Assignment ID
        user_id: User ID to grade
        grade: Grade value (must be within assignment's scale)
        feedback_text: Optional feedback text
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation of saved grade

    Raises:
        WriteOperationError: If course_id is not whitelisted

    Example use cases:
        - "Grade assignment 123 for user 456 with score 85"
        - "Save grade and feedback for submission"
        - "Grade student's assignment"
    """
    moodle = get_moodle_client(ctx)

    try:
        # Prepare grade data
        params = {
            'assignmentid': assignment_id,
            'userid': user_id,
            'grade': grade,
            'attemptnumber': -1,  # Grade most recent attempt
            'addattempt': 0,
            'workflowstate': 'released',  # Release grade to student
            'applytoall': 0
        }

        # Add feedback if provided
        if feedback_text:
            params['plugindata[assignfeedbackcomments_editor][text]'] = feedback_text
            params['plugindata[assignfeedbackcomments_editor][format]'] = 1  # HTML

        result = await moodle._make_request(
            'mod_assign_save_grade',
            params
        )

        response_data = {
            'assignment_id': assignment_id,
            'course_id': course_id,
            'user_id': user_id,
            'grade': grade,
            'saved': True
        }

        return format_response(response_data, "Assignment Grade Saved", format)
    except Exception as e:
        raise Exception(f"Failed to save assignment grade: {str(e)}")

@mcp.tool(
    name="moodle_update_grades",
    description="Update grades in the gradebook. REQUIRED: course_id (integer), item_name (string), grades (array of objects with userid and grade). WRITE OPERATION - only works on whitelisted courses (default: course 7299). Example: course_id=7299, item_name='Quiz 1', grades=[{'userid':123,'grade':85},{'userid':456,'grade':92}].",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,  # Safe to update grades
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_update_grades(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    item_name: str = Field(description="Grade item name", min_length=1),
    grades: list[dict] = Field(description="List of {userid: int, grade: float} objects", min_length=1),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Update grades in the gradebook for multiple users.

    SAFETY: This write operation is only allowed on whitelisted courses.
    Default whitelist: [7299] (Elizabeth's Moodle Playground)

    Updates grades for a specific grade item for multiple users.

    Args:
        course_id: Course ID (must be in whitelist!)
        item_name: Grade item name (e.g., "Quiz 1", "Assignment 2")
        grades: List of dictionaries with 'userid' and 'grade' keys
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation of updated grades

    Raises:
        WriteOperationError: If course_id is not whitelisted

    Example use cases:
        - "Update quiz grades for multiple students"
        - "Save grades for Quiz 1"
        - "Batch update assignment grades"
    """
    moodle = get_moodle_client(ctx)

    try:
        # Prepare grades data
        params = {
            'source': 'moodle_mcp',
            'courseid': course_id,
            'component': 'mod_assign',  # Component
            'activityname': item_name
        }

        # Add each grade
        for idx, grade_data in enumerate(grades):
            user_id = grade_data.get('userid')
            grade_value = grade_data.get('grade')
            params[f'grades[{idx}][userid]'] = user_id
            params[f'grades[{idx}][grade]'] = grade_value

        result = await moodle._make_request(
            'core_grades_update_grades',
            params
        )

        response_data = {
            'course_id': course_id,
            'item_name': item_name,
            'grades_updated': len(grades),
            'success': True
        }

        return format_response(response_data, "Grades Updated", format)
    except Exception as e:
        raise Exception(f"Failed to update grades: {str(e)}")
