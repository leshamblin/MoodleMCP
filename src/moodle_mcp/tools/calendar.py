"""
Calendar and event tools - READ and WRITE operations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Annotated

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors, require_write_permission
from ..utils.api_helpers import get_moodle_client, get_resolver


# --------------------------------------------------------------------------- #
# Local structured-output models (FastMCP 3.x).
# Kept here (not in models/results.py) since they're specific to calendar tools.
# --------------------------------------------------------------------------- #
@dataclass
class CalendarEvent:
    id: int
    name: str | None = None
    description: str | None = None
    eventtype: str | None = None
    courseid: int | None = None
    timestart: int | None = None
    timeduration: int | None = None


@dataclass
class CalendarEventList:
    events: list[CalendarEvent] = field(default_factory=list)
    count: int = 0


@dataclass
class CreatedCalendarEvent:
    event_id: int
    event_name: str
    course_id: int
    event_time: int
    event_time_readable: str
    duration: int


@dataclass
class DeletedCalendarEvent:
    event_id: int
    course_id: int
    deleted: bool
    repeat_deleted: bool


def _calendar_event(data: dict) -> CalendarEvent:
    """Build a CalendarEvent from a raw Moodle event dict."""
    return CalendarEvent(
        id=data.get("id", 0),
        name=data.get("name"),
        description=data.get("description"),
        eventtype=data.get("eventtype"),
        courseid=data.get("courseid"),
        timestart=data.get("timestart"),
        timeduration=data.get("timeduration"),
    )


@mcp.tool(
    name="moodle_get_calendar_events",
    description=(
        "Get calendar events (assignments, quizzes, deadlines) from the "
        "authenticated user's calendar over the next 'days_ahead' days. All "
        "params optional: pass 'course' (id/shortname/name) to return only that "
        "course's events; 'limit' to cap the count; 'sort_by_time=True' to sort "
        "soonest-first (the 'upcoming deadlines' view). "
        "Example: moodle_get_calendar_events(course=7299, sort_by_time=True, limit=10)."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_calendar_events(
    course: Annotated[
        int | str | None,
        Field(description="Course id, shortname, or name; omit for all of the user's events"),
    ] = None,
    days_ahead: Annotated[
        int, Field(description="Number of days ahead to fetch events", ge=1, le=365)
    ] = 30,
    limit: Annotated[
        int | None, Field(description="Optional max number of events to return", ge=1, le=200)
    ] = None,
    sort_by_time: Annotated[
        bool, Field(description="Sort events soonest-first (the 'upcoming' view)"),
    ] = False,
    ctx: Context = None,
) -> CalendarEventList:
    """User calendar events over a window, optionally filtered to one course,
    sorted, and limited (subsumes the old upcoming / course-events tools)."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)

    time_now = int(datetime.now().timestamp())
    time_end = int((datetime.now() + timedelta(days=days_ahead)).timestamp())

    events_data = await moodle.call(
        "core_calendar_get_calendar_events",
        {
            "options[timestart]": time_now,
            "options[timeend]": time_end,
        },
    )

    raw = (events_data or {}).get("events", [])

    if course is not None:
        cid = await resolver.course_id(course)
        raw = [e for e in raw if e.get("courseid") == cid]
    if sort_by_time:
        raw = sorted(raw, key=lambda x: x.get("timestart", 0))
    if limit is not None:
        raw = raw[:limit]

    events = [_calendar_event(e) for e in raw]
    return CalendarEventList(events=events, count=len(events))


# ============================================================================
# WRITE OPERATIONS - Require write permission for course events
# ============================================================================

@mcp.tool(
    name="moodle_create_calendar_event",
    description=(
        "Create a calendar event. REQUIRED: course_id (integer), event_name "
        "(string), event_time (unix timestamp). Optional: description (string), "
        "duration (seconds, default=0). WRITE OPERATION - only works on whitelisted "
        "courses (default: course 7299). Example: course_id=7299, "
        "event_name='Team Meeting', event_time=1735689600, "
        "description='Discuss project', duration=3600."
    ),
    tags={"write", "calendar"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False,
        idempotentHint=False, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_create_calendar_event(
    course_id: Annotated[
        int, Field(description="Course ID (must be whitelisted)", gt=0)
    ],
    event_name: Annotated[
        str, Field(description="Event name/title", min_length=1, max_length=255)
    ],
    event_time: Annotated[
        int, Field(description="Event start time as unix timestamp", gt=0)
    ],
    description: Annotated[
        str | None, Field(description="Optional event description")
    ] = None,
    duration: Annotated[
        int, Field(description="Event duration in seconds", ge=0)
    ] = 0,
    ctx: Context = None,
) -> CreatedCalendarEvent:
    """Create a calendar event in a course (whitelisted courses only)."""
    moodle = get_moodle_client(ctx)

    params = {
        "events[0][name]": event_name,
        "events[0][courseid]": course_id,
        "events[0][eventtype]": "course",
        "events[0][timestart]": event_time,
        "events[0][timeduration]": duration,
        "events[0][visible]": 1,
    }

    if description:
        params["events[0][description]"] = description
        params["events[0][format]"] = 1  # HTML format

    result = await moodle.call("core_calendar_create_calendar_events", params)

    # core_calendar_create_calendar_events returns {"events": [...], "warnings": [...]};
    # surface any per-row failures that arrived with HTTP 200.
    from ..core.client import raise_on_row_errors
    raise_on_row_errors(result.get("events", []))

    event_id = result["events"][0]["id"]

    return CreatedCalendarEvent(
        event_id=event_id,
        event_name=event_name,
        course_id=course_id,
        event_time=event_time,
        event_time_readable=datetime.fromtimestamp(event_time).strftime("%Y-%m-%d %H:%M"),
        duration=duration,
    )


@mcp.tool(
    name="moodle_delete_calendar_event",
    description=(
        "Delete a calendar event. REQUIRED: course_id (integer), event_id "
        "(integer). Optional: repeat (boolean, default=False) to delete all repeat "
        "instances. WRITE OPERATION - DESTRUCTIVE - only works on whitelisted "
        "courses (default: course 7299). Example: course_id=7299, event_id=123, "
        "repeat=False. Use moodle_get_calendar_events to get event_id."
    ),
    tags={"write", "calendar"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=True,
        idempotentHint=True, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_delete_calendar_event(
    course_id: Annotated[
        int, Field(description="Course ID (must be whitelisted)", gt=0)
    ],
    event_id: Annotated[int, Field(description="Event ID to delete", gt=0)],
    repeat: Annotated[
        bool, Field(description="Delete all repeat instances")
    ] = False,
    ctx: Context = None,
) -> DeletedCalendarEvent:
    """Delete a calendar event (whitelisted courses only)."""
    moodle = get_moodle_client(ctx)

    params = {
        "events[0][eventid]": event_id,
        "events[0][repeat]": 1 if repeat else 0,
    }

    await moodle.call("core_calendar_delete_calendar_events", params)

    return DeletedCalendarEvent(
        event_id=event_id,
        course_id=course_id,
        deleted=True,
        repeat_deleted=repeat,
    )
