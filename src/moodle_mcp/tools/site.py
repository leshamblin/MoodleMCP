"""
Site information and connectivity tools.
"""

from fastmcp import Context
from mcp.types import ToolAnnotations

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors
from ..utils.api_helpers import get_moodle_client
from ..models.results import SiteInfo, ConnectionStatus, AvailableFunctions


@mcp.tool(
    name="moodle_get_site_info",
    description=(
        "Get Moodle site information and the authenticated user's identity "
        "(site name, version, and the current user's id, username, full name, "
        "and email). No parameters. Useful to discover the current user's id."
    ),
    tags={"read", "site"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_site_info(ctx: Context = None) -> SiteInfo:
    """
    Get site information and current user identity.

    Returns the site name/URL/version plus the authenticated user's id,
    username, full name, and email.

    Example use cases:
        - "What Moodle site am I connected to?"
        - "What is my user id?"
    """
    moodle = get_moodle_client(ctx)
    info = await moodle.get_site_info()
    return SiteInfo(
        sitename=info.get("sitename", ""),
        siteurl=info.get("siteurl", ""),
        release=info.get("release"),
        version=str(info.get("version")) if info.get("version") is not None else None,
        userid=info.get("userid", 0),
        username=info.get("username"),
        fullname=info.get("fullname"),
        useremail=info.get("useremail"),
        function_count=len(info.get("functions", []) or []),
    )


@mcp.tool(
    name="moodle_test_connection",
    description=(
        "Test the Moodle API connection and authentication. No parameters. "
        "Returns whether the token works plus basic site/user details."
    ),
    tags={"read", "site"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_test_connection(ctx: Context = None) -> ConnectionStatus:
    """
    Verify connectivity and that the authentication token is valid.

    Example use cases:
        - "Check if the Moodle connection is working"
        - "Test my API authentication"
    """
    moodle = get_moodle_client(ctx)
    info = await moodle.get_site_info()
    return ConnectionStatus(
        connected=True,
        sitename=info.get("sitename", ""),
        siteurl=info.get("siteurl", ""),
        release=info.get("release"),
        fullname=info.get("fullname"),
        username=info.get("username"),
        userid=info.get("userid", 0),
    )


@mcp.tool(
    name="moodle_get_available_functions",
    description=(
        "List the Moodle Web Services functions the current token can call. "
        "No parameters. Useful for debugging which API endpoints/permissions "
        "are available to this token."
    ),
    tags={"read", "site"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_available_functions(ctx: Context = None) -> AvailableFunctions:
    """
    Get the list of Web Service functions enabled for the current token.

    Example use cases:
        - "What API functions can I use?"
        - "Is enrol_manual_enrol_users available to my token?"
    """
    moodle = get_moodle_client(ctx)
    info = await moodle.get_site_info()
    names = sorted(f.get("name", "") for f in (info.get("functions", []) or []))
    return AvailableFunctions(functions=names, count=len(names))
