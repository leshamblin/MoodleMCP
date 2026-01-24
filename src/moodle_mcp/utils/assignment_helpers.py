"""
Helper functions for assignment-related operations.

These helpers eliminate code duplication and simplify complex assignment
search and retrieval logic.
"""

from typing import Any
from ..core.client import MoodleAPIClient


async def find_assignment_by_id(
    moodle: MoodleAPIClient,
    assignment_id: int,
    user_id: int | None = None
) -> dict[str, Any] | None:
    """
    Find a specific assignment by ID across all user's courses.

    Since Moodle doesn't have a single assignment endpoint, this searches
    through all courses the user is enrolled in to find the assignment.

    Args:
        moodle: Moodle API client
        assignment_id: Assignment ID to find
        user_id: User ID (defaults to current user if None)

    Returns:
        Assignment dict if found, None otherwise

    Example:
        >>> assignment = await find_assignment_by_id(moodle, 123)
        >>> if assignment:
        >>>     print(f"Found: {assignment['name']}")
    """
    # Get site info if user_id not provided
    if user_id is None:
        site_info = await moodle.get_site_info()
        user_id = site_info['userid']

    # Get user's courses
    courses_data = await moodle._make_request(
        'core_enrol_get_users_courses',
        {'userid': user_id}
    )

    # Search through courses for the assignment
    for course in courses_data:
        try:
            assignments_data = await moodle._make_request(
                'mod_assign_get_assignments',
                {'courseids[0]': course['id']}
            )

            courses_list = assignments_data.get('courses', [])
            if courses_list and courses_list[0].get('assignments'):
                for assignment in courses_list[0]['assignments']:
                    if assignment.get('id') == assignment_id:
                        # Add course info for context
                        assignment['course_id'] = course['id']
                        assignment['course_name'] = course['fullname']
                        return assignment
        except Exception:
            # Skip courses with errors (permissions, etc.)
            continue

    return None


async def get_assignments_for_user(
    moodle: MoodleAPIClient,
    user_id: int | None = None,
    include_course_name: bool = True
) -> list[dict[str, Any]]:
    """
    Get all assignments for a user across all enrolled courses.

    Args:
        moodle: Moodle API client
        user_id: User ID (defaults to current user if None)
        include_course_name: Whether to add coursename to each assignment

    Returns:
        List of assignment dicts with course information

    Example:
        >>> assignments = await get_assignments_for_user(moodle)
        >>> for a in assignments:
        >>>     print(f"{a['coursename']}: {a['name']}")
    """
    # Get site info if user_id not provided
    if user_id is None:
        site_info = await moodle.get_site_info()
        user_id = site_info['userid']

    # Get user's courses
    courses_data = await moodle._make_request(
        'core_enrol_get_users_courses',
        {'userid': user_id}
    )

    # Collect assignments from all courses
    all_assignments = []
    for course in courses_data:
        try:
            assignments_data = await moodle._make_request(
                'mod_assign_get_assignments',
                {'courseids[0]': course['id']}
            )

            courses_list = assignments_data.get('courses', [])
            if courses_list and courses_list[0].get('assignments'):
                for assignment in courses_list[0]['assignments']:
                    # Add course information
                    assignment['course_id'] = course['id']
                    if include_course_name:
                        assignment['coursename'] = course['fullname']
                    all_assignments.append(assignment)
        except Exception:
            # Skip courses with errors (permissions, etc.)
            continue

    return all_assignments


async def get_assignments_for_course(
    moodle: MoodleAPIClient,
    course_id: int
) -> list[dict[str, Any]]:
    """
    Get all assignments in a specific course.

    Args:
        moodle: Moodle API client
        course_id: Course ID

    Returns:
        List of assignment dicts, empty list if none found

    Example:
        >>> assignments = await get_assignments_for_course(moodle, 7299)
        >>> print(f"Found {len(assignments)} assignments")
    """
    assignments_data = await moodle._make_request(
        'mod_assign_get_assignments',
        {'courseids[0]': course_id}
    )

    courses = assignments_data.get('courses', [])
    if courses and courses[0].get('assignments'):
        return courses[0]['assignments']

    return []
