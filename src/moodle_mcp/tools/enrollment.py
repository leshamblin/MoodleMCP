"""
Enrollment tools - WRITE operations for managing course enrollment.
"""

from pydantic import Field
from fastmcp import Context

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors, require_write_permission
from ..utils.api_helpers import get_moodle_client
from ..utils.formatting import format_response
from ..models.base import ResponseFormat

# ============================================================================
# WRITE OPERATIONS - Critical for course management
# ============================================================================

@mcp.tool(
    name="moodle_enrol_users",
    description="Enrol users into a course. REQUIRED: course_id (integer), user_ids (array of integers), role_id (integer, default=5 for student). WRITE OPERATION - only works on whitelisted courses (default: course 7299). Example: course_id=7299, user_ids=[123,456], role_id=5. Common roles: 5=Student, 4=Teacher, 3=Non-editing teacher.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,  # Re-enrolling same user is safe
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_enrol_users(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    user_ids: list[int] = Field(description="List of user IDs to enrol", min_length=1),
    role_id: int = Field(default=5, description="Role ID (5=Student, 4=Teacher, 3=Non-editing teacher)", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Enrol one or more users into a course with specified role.

    SAFETY: This write operation is only allowed on whitelisted courses.
    Default whitelist: [7299] (Elizabeth's Moodle Playground)

    Common role IDs:
    - 5: Student
    - 4: Teacher (editing)
    - 3: Non-editing teacher
    - 1: Manager

    Args:
        course_id: Course ID (must be in whitelist!)
        user_ids: List of user IDs to enrol
        role_id: Role to assign (default: 5 for Student)
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation message with enrollment details

    Raises:
        WriteOperationError: If course_id is not whitelisted

    Example use cases:
        - "Enrol user 123 as a student in course 7299"
        - "Add users [456, 789] as students to course 7299"
        - "Enrol user 234 as a teacher in course 7299"
    """
    moodle = get_moodle_client(ctx)

    # Prepare enrollment data
    enrolments = []
    for idx, user_id in enumerate(user_ids):
        enrolments.append({
            f'enrolments[{idx}][roleid]': role_id,
            f'enrolments[{idx}][userid]': user_id,
            f'enrolments[{idx}][courseid]': course_id
        })

    # Flatten the enrollment data
    params = {}
    for enrolment in enrolments:
        params.update(enrolment)

    try:
        # Call the manual enrolment function
        result = await moodle._make_request(
            'enrol_manual_enrol_users',
            params
        )

        # Build response
        role_names = {5: 'Student', 4: 'Teacher', 3: 'Non-editing teacher', 1: 'Manager'}
        role_name = role_names.get(role_id, f'Role {role_id}')

        response_data = {
            'course_id': course_id,
            'users_enrolled': len(user_ids),
            'user_ids': user_ids,
            'role': role_name,
            'role_id': role_id
        }

        return format_response(response_data, "Users Enrolled Successfully", format)
    except Exception as e:
        raise Exception(f"Failed to enrol users: {str(e)}")

@mcp.tool(
    name="moodle_unenrol_users",
    description="Unenrol (remove) users from a course. REQUIRED: course_id (integer), user_ids (array of integers). WRITE OPERATION - DESTRUCTIVE - only works on whitelisted courses (default: course 7299). Example: course_id=7299, user_ids=[123,456]. This removes users from the course entirely.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,  # Removes enrollment
        "idempotentHint": True,   # Safe to call multiple times
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_unenrol_users(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    user_ids: list[int] = Field(description="List of user IDs to unenrol", min_length=1),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Remove one or more users from a course.

    SAFETY: This write operation is only allowed on whitelisted courses.
    Default whitelist: [7299] (Elizabeth's Moodle Playground)

    WARNING: This is a DESTRUCTIVE operation. Users will lose access to the course
    and all their progress/grades will be hidden (but not deleted).

    Args:
        course_id: Course ID (must be in whitelist!)
        user_ids: List of user IDs to unenrol
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation message with unenrollment details

    Raises:
        WriteOperationError: If course_id is not whitelisted

    Example use cases:
        - "Remove user 123 from course 7299"
        - "Unenrol users [456, 789] from course 7299"
        - "Drop user 234 from the course"
    """
    moodle = get_moodle_client(ctx)

    # Prepare unenrollment data
    unenrolments = []
    for idx, user_id in enumerate(user_ids):
        unenrolments.append({
            f'enrolments[{idx}][userid]': user_id,
            f'enrolments[{idx}][courseid]': course_id
        })

    # Flatten the unenrollment data
    params = {}
    for unenrolment in unenrolments:
        params.update(unenrolment)

    try:
        # Call the manual unenrolment function
        result = await moodle._make_request(
            'enrol_manual_unenrol_users',
            params
        )

        response_data = {
            'course_id': course_id,
            'users_unenrolled': len(user_ids),
            'user_ids': user_ids
        }

        return format_response(response_data, "Users Unenrolled Successfully", format)
    except Exception as e:
        raise Exception(f"Failed to unenrol users: {str(e)}")
