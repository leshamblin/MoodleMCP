"""
Calendar and event tools - READ and WRITE operations.
"""

from pydantic import Field
from fastmcp import Context
from datetime import datetime, timedelta

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors, require_write_permission
from ..utils.api_helpers import get_moodle_client
from ..utils.formatting import format_response
from ..models.base import ResponseFormat

@mcp.tool(
    name="moodle_get_calendar_events",
    description="Get calendar events for authenticated user's calendar over a date range. NO PARAMETERS REQUIRED. Optional: days_ahead (1-365, default=30). Example: days_ahead=60. Returns events including assignments, quizzes, and deadlines.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_calendar_events(
    days_ahead: int = Field(default=30, description="Number of days ahead to fetch events", ge=1, le=365),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get calendar events for a specified date range.

    Returns upcoming events including assignments, quizzes, and other deadlines.

    Args:
        days_ahead: Number of days ahead to fetch events
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of calendar events

    Example use cases:
        - "What events are coming up?"
        - "Show my calendar for the next week"
        - "Get calendar events for the next 60 days"
    """
    moodle = get_moodle_client(ctx)

    # Calculate time range
    time_now = int(datetime.now().timestamp())
    time_end = int((datetime.now() + timedelta(days=days_ahead)).timestamp())

    # Get calendar events
    events_data = await moodle._make_request(
        'core_calendar_get_calendar_events',
        {
            'options[timestart]': time_now,
            'options[timeend]': time_end
        }
    )

    events = events_data.get('events', [])

    if not events:
        return f"No calendar events found for the next {days_ahead} days."

    return format_response(events, f"Calendar Events (Next {days_ahead} Days)", format)

@mcp.tool(
    name="moodle_get_upcoming_events",
    description="Get upcoming deadlines and events sorted chronologically. NO PARAMETERS REQUIRED. Optional: limit (1-50, default=10). Returns next upcoming events with dates and types.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_upcoming_events(
    limit: int = Field(default=10, description="Maximum number of events", ge=1, le=50),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get upcoming deadlines and events sorted by date.

    Shows the next upcoming events in chronological order.

    Args:
        limit: Maximum number of events to return
        format: Output format (markdown or json)
        ctx: Context

    Returns:
        List of upcoming events

    Example use cases:
        - "What's due soon?"
        - "Show my upcoming deadlines"
        - "What events are next?"
    """
    moodle = get_moodle_client(ctx)

    # Get upcoming events (next 60 days)
    time_now = int(datetime.now().timestamp())
    time_end = int((datetime.now() + timedelta(days=60)).timestamp())

    events_data = await moodle._make_request(
        'core_calendar_get_calendar_events',
        {
            'options[timestart]': time_now,
            'options[timeend]': time_end
        }
    )

    events = events_data.get('events', [])

    # Sort by timestart and limit
    events_sorted = sorted(events, key=lambda x: x.get('timestart', 0))[:limit]

    if not events_sorted:
        return "No upcoming events found."

    return format_response(events_sorted, "Upcoming Events", format)

@mcp.tool(
    name="moodle_get_course_events",
    description="Get calendar events specific to one course. REQUIRED: course_id (integer). Optional: days_ahead (1-365, default=60). Example: course_id=2292, days_ahead=30.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_course_events(
    course_id: int = Field(description="Course ID", gt=0),
    days_ahead: int = Field(default=60, description="Number of days ahead", ge=1, le=365),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get calendar events for a specific course.

    Shows events and deadlines specific to one course.

    Args:
        course_id: Course ID
        days_ahead: Number of days ahead to fetch
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of course events

    Example use cases:
        - "What events are in course 42?"
        - "Show deadlines for course 15"
        - "Get calendar for course 8"
    """
    moodle = get_moodle_client(ctx)

    # Get calendar events
    time_now = int(datetime.now().timestamp())
    time_end = int((datetime.now() + timedelta(days=days_ahead)).timestamp())

    events_data = await moodle._make_request(
        'core_calendar_get_calendar_events',
        {
            'options[timestart]': time_now,
            'options[timeend]': time_end,
            'events[courseids][0]': course_id
        }
    )

    events = events_data.get('events', [])

    # Filter to only course events
    course_events = [e for e in events if e.get('courseid') == course_id]

    if not course_events:
        return f"No events found for course {course_id}."

    return format_response(course_events, f"Events for Course {course_id}", format)

# ============================================================================
# WRITE OPERATIONS - Require write permission for course events
# ============================================================================

@mcp.tool(
    name="moodle_create_calendar_event",
    description="Create a calendar event. REQUIRED: course_id (integer), event_name (string), event_time (unix timestamp). Optional: description (string), duration (seconds, default=0). WRITE OPERATION - only works on whitelisted courses (default: course 7299). Example: course_id=7299, event_name='Team Meeting', event_time=1735689600, description='Discuss project', duration=3600.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_create_calendar_event(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    event_name: str = Field(description="Event name/title", min_length=1, max_length=255),
    event_time: int = Field(description="Event start time as unix timestamp", gt=0),
    description: str | None = Field(None, description="Optional event description"),
    duration: int = Field(default=0, description="Event duration in seconds", ge=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Create a new calendar event in a course.

    SAFETY: This write operation is only allowed on whitelisted courses.
    Default whitelist: [7299] (Elizabeth's Moodle Playground)

    Args:
        course_id: Course ID (must be in whitelist!)
        event_name: Event name/title
        event_time: Event start time as unix timestamp
        description: Optional event description
        duration: Event duration in seconds (0 for no duration)
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation message with event ID

    Raises:
        WriteOperationError: If course_id is not whitelisted

    Example use cases:
        - "Create a calendar event for team meeting"
        - "Add an event to the course calendar"
        - "Schedule a study session event"
    """
    moodle = get_moodle_client(ctx)

    # Prepare event data
    params = {
        'events[0][name]': event_name,
        'events[0][courseid]': course_id,
        'events[0][eventtype]': 'course',
        'events[0][timestart]': event_time,
        'events[0][timeduration]': duration,
        'events[0][visible]': 1
    }

    if description:
        params['events[0][description]'] = description
        params['events[0][format]'] = 1  # HTML format

    try:
        result = await moodle._make_request(
            'core_calendar_create_calendar_events',
            params
        )

        # Result is an array of created events
        if isinstance(result, dict) and 'events' in result:
            events = result['events']
            if events and len(events) > 0:
                event = events[0]
                event_id = event.get('id')
            else:
                event_id = None
        else:
            event_id = None

        if not event_id:
            return "Event created but no ID returned. It may have been created successfully."

        response_data = {
            'event_id': event_id,
            'event_name': event_name,
            'course_id': course_id,
            'event_time': event_time,
            'event_time_readable': datetime.fromtimestamp(event_time).strftime('%Y-%m-%d %H:%M'),
            'duration': duration
        }

        return format_response(response_data, "Calendar Event Created", format)
    except Exception as e:
        raise Exception(f"Failed to create calendar event: {str(e)}")

@mcp.tool(
    name="moodle_delete_calendar_event",
    description="Delete a calendar event. REQUIRED: course_id (integer), event_id (integer). Optional: repeat (boolean, default=False) to delete all repeat instances. WRITE OPERATION - DESTRUCTIVE - only works on whitelisted courses (default: course 7299). Example: course_id=7299, event_id=123, repeat=False. Use moodle_get_course_events to get event_id.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_delete_calendar_event(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    event_id: int = Field(description="Event ID to delete", gt=0),
    repeat: bool = Field(default=False, description="Delete all repeat instances"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Delete a calendar event.

    SAFETY: This write operation is only allowed on whitelisted courses.
    Default whitelist: [7299] (Elizabeth's Moodle Playground)

    NOTE: This is a DESTRUCTIVE operation. The event will be permanently deleted.

    Args:
        course_id: Course ID (must be in whitelist!)
        event_id: ID of the event to delete
        repeat: Whether to delete all repeat instances
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation message

    Raises:
        WriteOperationError: If course_id is not whitelisted

    Example use cases:
        - "Delete calendar event 123"
        - "Remove event from course calendar"
        - "Delete recurring event and all instances"
    """
    moodle = get_moodle_client(ctx)

    # Prepare delete data
    params = {
        'events[0][eventid]': event_id,
        'events[0][repeat]': 1 if repeat else 0
    }

    try:
        result = await moodle._make_request(
            'core_calendar_delete_calendar_events',
            params
        )

        response_data = {
            'event_id': event_id,
            'course_id': course_id,
            'deleted': True,
            'repeat_deleted': repeat
        }

        return format_response(response_data, "Calendar Event Deleted", format)
    except Exception as e:
        raise Exception(f"Failed to delete calendar event: {str(e)}")
