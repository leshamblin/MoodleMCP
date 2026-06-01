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
class GradesTable:
    """Gradebook overview rows (overall grades) for a course/user."""

    course_id: int
    grades: list[dict[str, Any]] = field(default_factory=list)


def _grade_items(data: Any) -> list[dict[str, Any]]:
    """Extract the list of per-user grade item groups from a response."""
    if isinstance(data, dict):
        return data.get("usergrades", [])
    return data if isinstance(data, list) else []


def _category_rows(data: Any) -> list[dict[str, Any]]:
    """Pull the deduped grade-category rows from a gradereport response.

    gradereport_user_get_grade_items returns usergrades[].gradeitems[], each
    tagged with an itemtype; keep only the 'category' rows.
    """
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
    return categories


@mcp.tool(
    name="moodle_get_grades",
    description=(
        "Get a user's grade items from the gradebook. Omit 'course' to "
        "aggregate across every enrolled course ('what are all my grades?'); "
        "pass a course (id/shortname/name) for just that one. Omit 'user' for "
        "the current user. Set items='categories' to return only the grade "
        "category structure (weighting/organization) instead of individual "
        "items. Backed by gradereport_user_get_grade_items. "
        "Example: course='CS101', user='student@example.com'."
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
async def moodle_get_grades(
    course: Annotated[
        int | str | None,
        Field(description="Course id, shortname, or name; omit to aggregate all enrolled courses"),
    ] = None,
    user: Annotated[
        int | str | None,
        Field(description="User id, username, or email; omit for current user"),
    ] = None,
    items: Annotated[
        str,
        Field(description="'all' for grade items (default) or 'categories' for the category structure only"),
    ] = "all",
    ctx: Context = None,
) -> UserGrades:
    """Get a user's grade items (one course or aggregated); items='categories'
    returns just the deduped category structure."""
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

        if items == "categories":
            entries = _category_rows(data)
        else:
            entries = _grade_items(data)

        if entries or course is not None:
            courses.append(
                CourseUserGrades(
                    course_id=cid,
                    course_name=c.get("fullname", ""),
                    grade_items=entries,
                )
            )

    return UserGrades(user_id=uid, courses=courses, count=len(courses))


@mcp.tool(
    name="moodle_get_grade_overview",
    description=(
        "Get a user's overall (final) grade in each of their courses -- the "
        "gradebook overview, one row per course. SELF-SCOPED: this reports the "
        "current user's grades; passing another 'user' only works if the token "
        "has the 'view grades of other users' capability and otherwise returns "
        "a permission error (it does NOT silently return your own grades). "
        "Optionally pass 'course' to return just that course's row. Backed by "
        "gradereport_overview_get_course_grades. "
        "Example: course=7299 to filter to one course."
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
async def moodle_get_grade_overview(
    user: Annotated[
        int | str | None,
        Field(description="User id, username, or email; omit for current user"),
    ] = None,
    course: Annotated[
        int | str | None,
        Field(description="Optional: filter to one course id/shortname/name"),
    ] = None,
    ctx: Context = None,
) -> GradesTable:
    """A user's overall grade per course; optionally filtered to one course."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)

    uid = await resolver.user_id(user)
    # This endpoint is user-scoped (returns one row per enrolled course); it
    # does not accept a courseid, so any course filter is applied client-side.
    data = await moodle.call(
        "gradereport_overview_get_course_grades", {"userid": uid}
    )
    grades = data.get("grades", []) if isinstance(data, dict) else []

    cid = 0
    if course is not None:
        cid = await resolver.course_id(course)
        grades = [g for g in grades if g.get("courseid") == cid]

    return GradesTable(course_id=cid, grades=grades)


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
