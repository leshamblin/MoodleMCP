"""Grade-related MCP tools for Moodle."""

from dataclasses import dataclass, field
from typing import Annotated, Any

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors, require_write_permission
from ..utils.api_helpers import get_moodle_client, get_resolver
from ..models.results import GradeSaveResult, BulkGradeResult


@dataclass
class CourseUserGrades:
    """A user's grade items within one course."""

    course_id: int
    course_name: str
    grade_items: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class UserGrades:
    """A user's grades.

    When a single course is requested, ``courses`` holds one entry. When no
    course is given, it holds one entry per enrolled course (aggregated view).
    """

    user_id: int
    courses: list[CourseUserGrades] = field(default_factory=list)
    count: int = 0


@dataclass
class CourseGrades:
    """Gradebook contents for an entire course."""

    course_id: int
    user_grades: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class GradeItems:
    """Grade items (assignments, quizzes, categories) for a course."""

    course_id: int
    user_id: int | None = None
    grade_items: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class GradesTable:
    """Formatted gradebook table for a course."""

    course_id: int
    grades: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class UserGradeSummary:
    """Summary of a user's grades across all enrolled courses."""

    user_id: int
    grades: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class GradeCategories:
    """Grade category structure for a course."""

    course_id: int
    categories: list[dict[str, Any]] = field(default_factory=list)
    count: int = 0


def _grade_items(data: Any) -> list[dict[str, Any]]:
    """Extract the list of per-user grade item groups from a response."""
    if isinstance(data, dict):
        return data.get("usergrades", [])
    return data if isinstance(data, list) else []


@mcp.tool(
    name="moodle_get_user_grades",
    description="""Get a user's grades, optionally across ALL their courses.

Returns grade items (scores, percentages, feedback) grouped by course.
- Omit `course` to aggregate grades across every course the user is enrolled
  in (useful for "what are all my grades?").
- Pass `course` to get just that course.
Omit `user` for the current user.""",
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_user_grades(
    user: Annotated[
        int | str | None,
        Field(description="User ID (int), username, or email; omit for current user"),
    ] = None,
    course: Annotated[
        int | str | None,
        Field(description="Optional course (ID, shortname, or fullname); omit for all enrolled courses"),
    ] = None,
    ctx: Context = None,
) -> UserGrades:
    """Get a user's grades, for one course or aggregated across all courses."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)

    uid = await resolver.user_id(user)

    # Determine the set of courses to report on.
    if course is not None:
        cid = await resolver.course_id(course)
        targets = [{"id": cid, "fullname": str(course)}]
    else:
        enrolled = await moodle.call(
            "core_enrol_get_users_courses", {"userid": uid}
        )
        targets = enrolled or []

    courses: list[CourseUserGrades] = []
    for c in targets:
        cid = c.get("id")
        try:
            data = await moodle.call(
                "gradereport_user_get_grade_items",
                {"courseid": cid, "userid": uid},
            )
        except Exception:
            # Skip courses where this user's grades can't be retrieved
            # (e.g. permissions); keep aggregating the rest.
            continue
        items = _grade_items(data)
        if items or course is not None:
            courses.append(
                CourseUserGrades(
                    course_id=cid,
                    course_name=c.get("fullname", ""),
                    grade_items=items,
                )
            )

    return UserGrades(user_id=uid, courses=courses, count=len(courses))


@mcp.tool(
    name="moodle_get_course_grades",
    description="""Get the gradebook for an entire course.

Returns all grade items and student grades.
Useful for reviewing overall class performance.""",
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_course_grades(
    course: Annotated[
        int | str,
        Field(description="Course ID (int), shortname, or fullname"),
    ],
    ctx: Context = None,
) -> CourseGrades:
    """Get the gradebook for a course (instructor/admin view)."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)

    cid = await resolver.course_id(course)

    # Prefer the course-wide gradebook endpoint (item definitions for the whole
    # course). Fall back to the per-user grade report if the token's service
    # doesn't expose it.
    try:
        data = await moodle.call("core_grades_get_gradeitems", {"courseid": cid})
        grade_items = data.get("gradeitems", data) if isinstance(data, dict) else data
        return CourseGrades(course_id=cid, user_grades=grade_items or [])
    except Exception:
        data = await moodle.call(
            "gradereport_user_get_grade_items", {"courseid": cid}
        )
        return CourseGrades(course_id=cid, user_grades=_grade_items(data))


@mcp.tool(
    name="moodle_get_grade_items",
    description="""Get all grade items (assignments, quizzes, etc.) for a course.

Returns the structure of the gradebook including categories and items.
Useful for understanding how a course is graded.""",
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_grade_items(
    course: Annotated[
        int | str,
        Field(description="Course ID (int), shortname, or fullname"),
    ],
    user: Annotated[
        int | str | None,
        Field(description="Optional: specific user (ID, username, or email) to filter grades"),
    ] = None,
    ctx: Context = None,
) -> GradeItems:
    """Get all grade items for a course."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)

    cid = await resolver.course_id(course)
    uid = await resolver.user_id(user)

    params: dict[str, Any] = {"courseid": cid}
    if uid is not None:
        params["userid"] = uid

    data = await moodle.call("gradereport_user_get_grade_items", params)

    return GradeItems(course_id=cid, user_id=uid, grade_items=_grade_items(data))


@mcp.tool(
    name="moodle_get_grades_table",
    description="""Get the formatted grades table for a course.

Returns grades in a table format similar to the Moodle gradebook view.
Useful for a comprehensive view of all grades.""",
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_grades_table(
    course: Annotated[
        int | str,
        Field(description="Course ID (int), shortname, or fullname"),
    ],
    user: Annotated[
        int | str | None,
        Field(description="Optional: specific user (ID, username, or email)"),
    ] = None,
    ctx: Context = None,
) -> GradesTable:
    """Get the formatted grades table for a course."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)

    cid = await resolver.course_id(course)
    # user is accepted for parity with the gradebook view but the
    # overview endpoint is course-scoped.
    await resolver.user_id(user)

    data = await moodle.call(
        "gradereport_overview_get_course_grades",
        {"courseid": cid},
    )

    grades = data.get("grades", []) if isinstance(data, dict) else []
    return GradesTable(course_id=cid, grades=grades)


@mcp.tool(
    name="moodle_get_user_grade_summary",
    description="""Get a summary of a user's grades across all their courses.

Returns overall grades for each enrolled course.
Useful for tracking a student's overall academic performance.""",
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_user_grade_summary(
    user: Annotated[
        int | str,
        Field(description="User ID (int), username, or email address"),
    ],
    ctx: Context = None,
) -> UserGradeSummary:
    """Get a summary of a user's grades across all courses."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)

    uid = await resolver.user_id(user)

    data = await moodle.call(
        "gradereport_overview_get_course_grades",
        {"userid": uid},
    )

    grades = data.get("grades", []) if isinstance(data, dict) else []
    return UserGradeSummary(user_id=uid, grades=grades)


@mcp.tool(
    name="moodle_get_grade_categories",
    description="""Get grade categories for a course.

Returns the category structure used to organize grades.
Useful for understanding grade weighting and organization.""",
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_grade_categories(
    course: Annotated[
        int | str,
        Field(description="Course ID (int), shortname, or fullname"),
    ],
    ctx: Context = None,
) -> GradeCategories:
    """Get the grade categories (not individual items) for a course."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)

    cid = await resolver.course_id(course)

    # gradereport_user_get_grade_items returns usergrades[].gradeitems[],
    # each tagged with an itemtype. Keep only the category rows so the result
    # is genuinely the category structure, deduped across users.
    data = await moodle.call(
        "gradereport_user_get_grade_items",
        {"courseid": cid},
    )

    seen: set = set()
    categories: list[dict[str, Any]] = []
    for usergrade in _grade_items(data):
        for item in usergrade.get("gradeitems", []) or []:
            if item.get("itemtype") != "category":
                continue
            key = item.get("id")
            if key in seen:
                continue
            seen.add(key)
            categories.append(item)

    return GradeCategories(course_id=cid, categories=categories, count=len(categories))


@mcp.tool(
    name="moodle_save_assignment_grade",
    description=(
        "WRITE: save or update one student's grade for an assignment, with an "
        "optional feedback comment. Modifies real grades; only works on "
        "write-whitelisted courses (course 7299 in DEV). 'assignment' accepts "
        "the activity name or instance id; 'user' accepts id/username/email. "
        "Idempotent: re-saving the same grade is safe. "
        "Example: course=7299, assignment='Lab Report 1', "
        "user='student@example.com', grade=92, feedback='Great work'."
    ),
    tags={"write", "grading"},
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission('course')
async def moodle_save_assignment_grade(
    course: Annotated[
        int | str,
        Field(description="Course id, shortname, or name (must be whitelisted)"),
    ],
    assignment: Annotated[
        int | str,
        Field(description="Assignment name or instance id"),
    ],
    user: Annotated[
        int | str,
        Field(description="Student user id, username, or email"),
    ],
    grade: Annotated[
        float,
        Field(description="The grade value to assign"),
    ],
    feedback: Annotated[
        str,
        Field(description="Optional feedback comment for the student"),
    ] = "",
    workflow_state: Annotated[
        str,
        Field(description="Marking workflow state (e.g. 'released'); empty to leave unchanged"),
    ] = "released",
    ctx: Context = None,
) -> GradeSaveResult:
    """Save a grade for an assignment submission (assignment accepts a name)."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)

    cid = await resolver.course_id(course)
    act = await resolver.activity(course, assignment, modname="assign")
    uid = await resolver.user_id(user)

    # mod_assign_save_grade returns null on success.
    await moodle.call(
        "mod_assign_save_grade",
        {
            "assignmentid": act.instance,
            "userid": uid,
            "grade": grade,
            "attemptnumber": -1,
            "addattempt": 0,
            "workflowstate": workflow_state,
            "applytoall": 0,
            "plugindata": {
                "assignfeedbackcomments_editor": {
                    "text": feedback,
                    "format": 1,
                }
            },
        },
    )

    return GradeSaveResult(
        course_id=cid,
        assignment_id=act.instance,
        user_id=uid,
        grade=grade,
        feedback_saved=bool(feedback),
        workflow_state=workflow_state,
    )


@mcp.tool(
    name="moodle_update_grades",
    description=(
        "WRITE: bulk-update grades for many students on one activity via the "
        "gradebook. Modifies real grades; only works on write-whitelisted "
        "courses (course 7299 in DEV). 'activity' accepts the activity name or "
        "its course-module id (cmid). 'grades' is a list of {studentid, grade}. "
        "Example: course=7299, activity='Lab Report 1', component='mod_assign', "
        "grades=[{'studentid': 624, 'grade': 88}]."
    ),
    tags={"write", "grading"},
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission('course')
async def moodle_update_grades(
    course: Annotated[
        int | str,
        Field(description="Course id, shortname, or name (must be whitelisted)"),
    ],
    activity: Annotated[
        int | str,
        Field(description="Activity name or course-module id (cmid)"),
    ],
    grades: Annotated[
        list[dict],
        Field(
            description="List of {studentid: int, grade: float} objects",
            min_length=1,
        ),
    ],
    component: Annotated[
        str,
        Field(description="The component (e.g., 'mod_assign')"),
    ] = "mod_assign",
    item_number: Annotated[
        int,
        Field(description="Grade item number within the activity", ge=0),
    ] = 0,
    ctx: Context = None,
) -> BulkGradeResult:
    """Bulk-update grades via the gradebook (activity resolves to its cmid)."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)

    cid = await resolver.course_id(course)
    activity_id = (await resolver.activity(course, activity)).cmid

    # activityid is the COURSE MODULE id (cmid), NOT the activity instance id.
    # core_grades_update_grades returns 0 (int) on success.
    await moodle.call(
        "core_grades_update_grades",
        {
            "source": "mod_mcp",
            "courseid": cid,
            "component": component,
            "activityid": activity_id,
            "itemnumber": item_number,
            "grades": [
                {"studentid": g.get("studentid"), "grade": g.get("grade")}
                for g in grades
            ],
        },
    )

    return BulkGradeResult(
        course_id=cid,
        assignment_id=activity_id,
        graded_count=len(grades),
        user_ids=[g.get("studentid") for g in grades],
    )
