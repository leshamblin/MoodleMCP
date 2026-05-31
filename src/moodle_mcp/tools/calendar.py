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
from ..utils.api_helpers import get_moodle_client


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
        "Get calendar events for the authenticated user's calendar over a date "
        "range. NO PARAMETERS REQUIRED. Optional: days_ahead (1-365, default=30). "
        "Example: days_ahead=60. Returns events including assignments, quizzes, "
        "and deadlines."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_calendar_events(
    days_ahead: Annotated[
        int, Field(description="Number of days ahead to fetch events", ge=1, le=365)
    ] = 30,
    ctx: Context = None,
) -> CalendarEventList:
    """Get the current user's calendar events over a date range."""
    moodle = get_moodle_client(ctx)

    time_now = int(datetime.now().timestamp())
    time_end = int((datetime.now() + timedelta(days=days_ahead)).timestamp())

    events_data = await moodle.call(
        "core_calendar_get_calendar_events",
        {
            "options[timestart]": time_now,
            "options[timeend]": time_end,
        },
    )

    events = [_calendar_event(e) for e in (events_data or {}).get("events", [])]
    return CalendarEventList(events=events, count=len(events))


@mcp.tool(
    name="moodle_get_upcoming_events",
    description=(
        "Get upcoming deadlines and events sorted chronologically. NO PARAMETERS "
        "REQUIRED. Optional: limit (1-50, default=10). Returns next upcoming events "
        "with dates and types."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_upcoming_events(
    limit: Annotated[
        int, Field(description="Maximum number of events", ge=1, le=50)
    ] = 10,
    ctx: Context = None,
) -> CalendarEventList:
    """Get upcoming deadlines and events sorted by date."""
    moodle = get_moodle_client(ctx)

    time_now = int(datetime.now().timestamp())
    time_end = int((datetime.now() + timedelta(days=60)).timestamp())

    events_data = await moodle.call(
        "core_calendar_get_calendar_events",
        {
            "options[timestart]": time_now,
            "options[timeend]": time_end,
        },
    )

    raw = (events_data or {}).get("events", [])
    events_sorted = sorted(raw, key=lambda x: x.get("timestart", 0))[:limit]
    events = [_calendar_event(e) for e in events_sorted]
    return CalendarEventList(events=events, count=len(events))


@mcp.tool(
    name="moodle_get_course_events",
    description=(
        "Get calendar events specific to one course. REQUIRED: course_id (integer). "
        "Optional: days_ahead (1-365, default=60). Example: course_id=2292, "
        "days_ahead=30."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_course_events(
    course_id: Annotated[int, Field(description="Course ID", gt=0)],
    days_ahead: Annotated[
        int, Field(description="Number of days ahead", ge=1, le=365)
    ] = 60,
    ctx: Context = None,
) -> CalendarEventList:
    """Get calendar events for a specific course."""
    moodle = get_moodle_client(ctx)

    time_now = int(datetime.now().timestamp())
    time_end = int((datetime.now() + timedelta(days=days_ahead)).timestamp())

    events_data = await moodle.call(
        "core_calendar_get_calendar_events",
        {
            "options[timestart]": time_now,
            "options[timeend]": time_end,
            "events[courseids][0]": course_id,
        },
    )

    course_events = [
        _calendar_event(e)
        for e in (events_data or {}).get("events", [])
        if e.get("courseid") == course_id
    ]
    return CalendarEventList(events=course_events, count=len(course_events))


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
        "repeat=False. Use moodle_get_course_events to get event_id."
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
