"""
User management tools - READ ONLY.
"""

from dataclasses import dataclass, field
from typing import Annotated

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors
from ..utils.api_helpers import get_moodle_client, get_resolver


# --------------------------------------------------------------------------- #
# Local structured-output models (FastMCP 3.x).
# Kept here (not in models/results.py) since they're specific to user tools.
# --------------------------------------------------------------------------- #
@dataclass
class UserProfile:
    id: int
    username: str | None = None
    firstname: str | None = None
    lastname: str | None = None
    fullname: str | None = None
    email: str | None = None
    department: str | None = None
    institution: str | None = None
    city: str | None = None
    country: str | None = None
    profileimageurl: str | None = None
    firstaccess: int | None = None
    lastaccess: int | None = None
    description: str | None = None


@dataclass
class UserList:
    users: list[UserProfile] = field(default_factory=list)
    count: int = 0


@dataclass
class UserPreferenceItem:
    name: str
    value: str | None = None


@dataclass
class UserPreferencesResult:
    userid: int
    preferences: list[UserPreferenceItem] = field(default_factory=list)
    count: int = 0


@dataclass
class Participant:
    id: int
    fullname: str | None = None
    email: str | None = None
    roles: list[str] = field(default_factory=list)


@dataclass
class CourseParticipants:
    course_id: int
    participants: list[Participant] = field(default_factory=list)
    total: int = 0
    count: int = 0


def _user_profile(data: dict) -> UserProfile:
    """Build a UserProfile from a raw Moodle user dict."""
    return UserProfile(
        id=data.get("id", 0),
        username=data.get("username"),
        firstname=data.get("firstname"),
        lastname=data.get("lastname"),
        fullname=data.get("fullname"),
        email=data.get("email"),
        department=data.get("department"),
        institution=data.get("institution"),
        city=data.get("city"),
        country=data.get("country"),
        profileimageurl=data.get("profileimageurl"),
        firstaccess=data.get("firstaccess"),
        lastaccess=data.get("lastaccess"),
        description=data.get("description"),
    )


@mcp.tool(
    name="moodle_get_current_user",
    description=(
        "Get the profile of the currently authenticated user, including the "
        "user id needed by many other tools. No parameters. Use this FIRST to "
        "discover your own user id."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_current_user(ctx: Context = None) -> UserProfile:
    """Get the profile of the currently authenticated user."""
    moodle = get_moodle_client(ctx)
    info = await moodle.get_site_info()
    return UserProfile(
        id=info.get("userid", 0),
        username=info.get("username"),
        fullname=info.get("fullname"),
        email=info.get("useremail"),
    )


@mcp.tool(
    name="moodle_get_user_profile",
    description=(
        "Get a detailed profile for a user. Accepts a numeric user id, a "
        "username, or an email (omit to use the current user). "
        "Example: user='jdoe' or user=624."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_user_profile(
    user: Annotated[
        int | str | None,
        Field(description="User id, username, or email; omit for current user"),
    ] = None,
    ctx: Context = None,
) -> UserProfile:
    """Get a detailed profile for a user."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    uid = await resolver.user_id(user)

    users_data = await moodle.call(
        "core_user_get_users_by_field", {"field": "id", "values": [uid]}
    )
    if not users_data:
        from ..core.exceptions import MoodleNotFoundError
        raise MoodleNotFoundError(f"User {uid} not found.")

    return _user_profile(users_data[0])


@mcp.tool(
    name="moodle_search_users",
    description=(
        "Search for users by name or email. Provide at least 2 characters. "
        "Example: search_query='Smith' or search_query='jdoe@example.com'. "
        "Returns matching users with their ids."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_search_users(
    search_query: Annotated[
        str, Field(description="Search term (name or email)", min_length=2)
    ],
    limit: Annotated[
        int, Field(description="Maximum results", ge=1, le=100)
    ] = 20,
    ctx: Context = None,
) -> UserList:
    """Search users by name or email."""
    moodle = get_moodle_client(ctx)

    query = search_query.strip()
    found: dict[int, dict] = {}

    # core_user_get_users (criteria search) is often not granted to a token's
    # service and rejects 'fullname' outright. Prefer core_user_get_users_by_field,
    # which only needs moodle/user:viewdetails. It matches a single field exactly.
    async def _by_field(field_name: str, value: str) -> list[dict]:
        try:
            data = await moodle.call(
                "core_user_get_users_by_field", {"field": field_name, "values": [value]}
            )
            return data or []
        except Exception:
            return []

    async def _by_criteria(criteria: list[dict]) -> list[dict]:
        try:
            data = await moodle.call("core_user_get_users", {"criteria": criteria})
            return (data or {}).get("users", []) if isinstance(data, dict) else []
        except Exception:
            return []

    if "@" in query:
        for u in await _by_field("email", query):
            found[u["id"]] = u
    else:
        # Try the criteria search (firstname/lastname) where the token allows it;
        # silently fall back to nothing if the function is not in the service.
        parts = query.split()
        if len(parts) >= 2:
            for u in await _by_criteria([
                {"key": "firstname", "value": parts[0]},
                {"key": "lastname", "value": " ".join(parts[1:])},
            ]):
                found[u["id"]] = u
        for token in parts:
            for field_name in ("lastname", "firstname"):
                for u in await _by_criteria([{"key": field_name, "value": token}]):
                    found[u["id"]] = u

    users = [_user_profile(u) for u in list(found.values())[:limit]]
    return UserList(users=users, count=len(users))


@mcp.tool(
    name="moodle_get_user_preferences",
    description=(
        "Get a user's preferences and settings (language, theme, timezone, "
        "etc.). Accepts a numeric user id, a username, or an email (omit for "
        "the current user). Example: user='jdoe' or user=624."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_user_preferences(
    user: Annotated[
        int | str | None,
        Field(description="User id, username, or email; omit for current user"),
    ] = None,
    ctx: Context = None,
) -> UserPreferencesResult:
    """Get a user's preferences and settings."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    uid = await resolver.user_id(user)

    items: list[UserPreferenceItem] = []
    try:
        prefs_data = await moodle.call(
            "core_user_get_user_preferences", {"userid": uid}
        )
        for p in (prefs_data or {}).get("preferences", []) or []:
            items.append(
                UserPreferenceItem(name=p.get("name", ""), value=p.get("value"))
            )
    except Exception:
        # Fallback to basic user info if the preferences function is unavailable.
        users_data = await moodle.call(
            "core_user_get_users_by_field", {"field": "id", "values": [uid]}
        )
        if users_data:
            u = users_data[0]
            for name in ("lang", "theme", "timezone", "mailformat"):
                items.append(UserPreferenceItem(name=name, value=u.get(name)))

    return UserPreferencesResult(userid=uid, preferences=items, count=len(items))


@mcp.tool(
    name="moodle_get_course_participants",
    description=(
        "List the participants (students, teachers, etc.) enrolled in a course, "
        "with their roles. Accepts a numeric course id, shortname, or idnumber. "
        "Example: course=7299. Supports limit/offset pagination."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_course_participants(
    course: Annotated[
        int | str, Field(description="Course id, shortname, or idnumber")
    ],
    limit: Annotated[
        int, Field(description="Maximum results", ge=1, le=100)
    ] = 20,
    offset: Annotated[
        int, Field(description="Offset for pagination", ge=0)
    ] = 0,
    ctx: Context = None,
) -> CourseParticipants:
    """List a course's participants with their roles."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    cid = await resolver.course_id(course)

    users_data = await moodle.call(
        "core_enrol_get_enrolled_users", {"courseid": cid}
    )
    users_data = users_data or []

    total = len(users_data)
    page = users_data[offset:offset + limit]

    participants = [
        Participant(
            id=u.get("id", 0),
            fullname=u.get("fullname"),
            email=u.get("email"),
            roles=[r.get("shortname", "") for r in (u.get("roles", []) or [])],
        )
        for u in page
    ]

    return CourseParticipants(
        course_id=cid,
        participants=participants,
        total=total,
        count=len(participants),
    )
