"""
Aggregate "dashboard" tools that answer a common multi-step question in one
call, so an agent does not have to chain list-courses -> upcoming -> grades.
"""

from dataclasses import dataclass, field
from typing import Annotated, Any

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors
from ..utils.api_helpers import get_moodle_client, get_resolver


@dataclass
class OverviewCourse:
    id: int
    fullname: str | None = None
    shortname: str | None = None
    progress: float | None = None


@dataclass
class OverviewEvent:
    id: int
    name: str | None = None
    timestart: int | None = None
    course_id: int | None = None


@dataclass
class OverviewGrade:
    course_id: int
    course_name: str | None = None
    item_name: str | None = None
    grade: str | None = None


@dataclass
class StudentOverview:
    """A one-call snapshot: courses, upcoming deadlines, and recent grades."""

    user_id: int
    courses: list[OverviewCourse] = field(default_factory=list)
    upcoming_events: list[OverviewEvent] = field(default_factory=list)
    recent_grades: list[OverviewGrade] = field(default_factory=list)
    course_count: int = 0


@mcp.tool(
    name="moodle_get_student_overview",
    description=(
        "One-call snapshot for a student: their enrolled courses, upcoming "
        "calendar events/deadlines, and recent grades. Use this instead of "
        "chaining moodle_list_user_courses + moodle_get_upcoming_events + "
        "moodle_get_user_grades. Accepts a user id/username/email; omit for the "
        "current user. Example: user='student@example.com' or omit for self."
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
async def moodle_get_student_overview(
    user: Annotated[
        int | str | None,
        Field(description="User id, username, or email; omit for current user"),
    ] = None,
    max_events: Annotated[
        int, Field(description="Max upcoming events to include", ge=1, le=50)
    ] = 10,
    max_grade_courses: Annotated[
        int,
        Field(description="Max courses to pull recent grades from", ge=1, le=20),
    ] = 5,
    ctx: Context = None,
) -> StudentOverview:
    """Aggregate courses, upcoming events, and recent grades in one call."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    uid = await resolver.user_id(user)

    # 1) Enrolled courses
    courses_raw = await moodle.call(
        "core_enrol_get_users_courses", {"userid": uid}
    )
    courses = [
        OverviewCourse(
            id=c.get("id", 0),
            fullname=c.get("fullname"),
            shortname=c.get("shortname"),
            progress=c.get("progress"),
        )
        for c in (courses_raw or [])
    ]

    # 2) Upcoming events (current-user calendar view; best-effort)
    events: list[OverviewEvent] = []
    try:
        ev_raw = await moodle.call(
            "core_calendar_get_calendar_upcoming_view", {}
        )
        for e in (ev_raw or {}).get("events", [])[:max_events]:
            course = e.get("course")
            cid = course.get("id") if isinstance(course, dict) else e.get("courseid")
            events.append(
                OverviewEvent(
                    id=e.get("id", 0),
                    name=e.get("name"),
                    timestart=e.get("timestart"),
                    course_id=cid,
                )
            )
    except Exception:
        # Calendar view may be unavailable for some tokens; degrade gracefully.
        events = []

    # 3) Recent grades across the first few courses (best-effort per course)
    grades: list[OverviewGrade] = []
    for c in courses[:max_grade_courses]:
        try:
            gdata = await moodle.call(
                "gradereport_user_get_grade_items",
                {"courseid": c.id, "userid": uid},
            )
            grades.extend(_recent_grades(gdata, c.id, c.fullname))
        except Exception:
            continue

    return StudentOverview(
        user_id=uid,
        courses=courses,
        upcoming_events=events,
        recent_grades=grades,
        course_count=len(courses),
    )


def _recent_grades(
    gdata: Any, course_id: int, course_name: str | None
) -> list[OverviewGrade]:
    """Pull graded (non-empty) items from a gradereport payload."""
    out: list[OverviewGrade] = []
    reports = (gdata or {}).get("usergrades", []) if isinstance(gdata, dict) else []
    for report in reports:
        for item in report.get("gradeitems", []) or []:
            graded = item.get("gradeformatted")
            if graded in (None, "", "-"):
                continue
            out.append(
                OverviewGrade(
                    course_id=course_id,
                    course_name=course_name,
                    item_name=item.get("itemname"),
                    grade=graded,
                )
            )
    return out
