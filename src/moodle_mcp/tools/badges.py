"""
Badge tools for Moodle MCP server - READ ONLY.

Badges are digital credentials awarded to users for achievements and
completion of learning objectives.

Tools:
- moodle_get_user_badges: Get badges earned by a user (READ)
- moodle_get_user_badge_by_hash: Get specific badge details by unique hash (READ)
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
# Kept here (not in models/results.py) since they're specific to badge tools.
# --------------------------------------------------------------------------- #
@dataclass
class Badge:
    id: int | None = None
    name: str | None = None
    description: str | None = None
    badgeurl: str | None = None
    issuername: str | None = None
    courseid: int | None = None
    dateissued: int | None = None
    dateexpire: int | None = None
    uniquehash: str | None = None


@dataclass
class UserBadges:
    userid: int
    badges: list[Badge] = field(default_factory=list)
    count: int = 0


def _badge(data: dict) -> Badge:
    """Build a Badge from a raw Moodle badge dict."""
    return Badge(
        id=data.get("id"),
        name=data.get("name"),
        description=data.get("description"),
        badgeurl=data.get("badgeurl"),
        issuername=data.get("issuername"),
        courseid=data.get("courseid"),
        dateissued=data.get("dateissued"),
        dateexpire=data.get("dateexpire"),
        uniquehash=data.get("uniquehash"),
    )


# ============================================================================
# READ OPERATIONS
# ============================================================================


@mcp.tool(
    name="moodle_get_user_badges",
    description=(
        "Get all badges earned by a user. Accepts a numeric user id, username, "
        "or email (omit for the current user). Optionally filter by course "
        "(numeric id, shortname, or idnumber). Example: user=123, course=7299. "
        "Returns the list of earned badges."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_user_badges(
    user: Annotated[
        int | str | None,
        Field(description="User id, username, or email; omit for current user"),
    ] = None,
    course: Annotated[
        int | str | None,
        Field(description="Course id, shortname, or idnumber to filter (omit for all)"),
    ] = None,
    page: Annotated[int, Field(description="Page number for pagination", ge=0)] = 0,
    per_page: Annotated[int, Field(description="Badges per page (0 = all)", ge=0)] = 0,
    search: Annotated[str, Field(description="Search string to filter badges")] = "",
    only_public: Annotated[
        bool, Field(description="Only return badges visible to others")
    ] = False,
    ctx: Context = None,
) -> UserBadges:
    """Get the badges a user has earned."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    uid = await resolver.user_id(user)

    params: dict = {"userid": uid}

    if course is not None:
        params["courseid"] = await resolver.course_id(course)

    if page > 0:
        params["page"] = page

    if per_page > 0:
        params["perpage"] = per_page

    if search:
        params["search"] = search

    if only_public:
        params["onlypublic"] = 1

    result = await moodle.call("core_badges_get_user_badges", params)

    raw = (result or {}).get("badges", []) if isinstance(result, dict) else (result or [])
    badges = [_badge(b) for b in raw]
    return UserBadges(userid=uid, badges=badges, count=len(badges))


@mcp.tool(
    name="moodle_get_user_badge_by_hash",
    description=(
        "Get detailed information about a specific badge using its unique hash. "
        "REQUIRED: hash (string, unique badge identifier). "
        "Example: hash='abc123def456'. Returns detailed badge information."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_user_badge_by_hash(
    hash: Annotated[
        str, Field(description="Unique badge hash identifier", min_length=1)
    ],
    ctx: Context = None,
) -> Badge:
    """Get details for a specific badge by its unique hash."""
    moodle = get_moodle_client(ctx)

    result = await moodle.call(
        "core_badges_get_user_badge_by_hash", {"hash": hash}
    )

    data = (result or {}).get("badge", result) if isinstance(result, dict) else result
    if isinstance(data, list):
        data = data[0] if data else {}
    return _badge(data or {})
