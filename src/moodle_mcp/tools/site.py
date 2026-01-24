"""
Site information and connectivity tools.
"""

from pydantic import Field
from fastmcp import Context

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors
from ..utils.formatting import format_response
from ..utils.api_helpers import get_moodle_client
from ..models.base import ResponseFormat

@mcp.tool(
    name="moodle_get_site_info",
    description="Get comprehensive Moodle site information including site name, version, user details (ID, username, email), and available functions. NO PARAMETERS REQUIRED - automatically uses authenticated user. Parameters: format (optional, 'markdown' or 'json'). Use this to get the current user's ID for other API calls.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_site_info(
    format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' (default, human-readable) or 'json' (machine-readable)"
    ),
    ctx: Context = None
) -> str:
    """
    Get comprehensive Moodle site information including site name, version, and current user details.

    This tool retrieves:
    - Site information (name, URL, version, release)
    - Current authenticated user information (ID, username, full name, email)
    - User capabilities and functions
    - Language and theme settings

    Args:
        format: Output format (markdown or json)
        ctx: FastMCP context (automatically injected)

    Returns:
        Formatted site information

    Example use cases:
        - "What Moodle site am I connected to?"
        - "Show me my user information"
        - "What version of Moodle is this?"
        - "Get the current user's ID"
    """
    moodle = get_moodle_client(ctx)
    site_info = await moodle.get_site_info()

    return format_response(site_info, "Moodle Site Information", format)

@mcp.tool(
    name="moodle_test_connection",
    description="Test Moodle API connection and verify authentication. NO PARAMETERS REQUIRED. Returns connection status, site info, and authenticated user details. Use this to verify the server is accessible and your token works.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_test_connection(ctx: Context = None) -> str:
    """
    Test Moodle API connection and authentication.

    This tool verifies:
    - Network connectivity to Moodle server
    - API endpoint availability
    - Authentication token validity
    - Basic API functionality

    Returns a simple success/failure message with connection details.

    Args:
        ctx: FastMCP context (automatically injected)

    Returns:
        Connection test result message

    Example use cases:
        - "Check if Moodle connection is working"
        - "Test my API authentication"
        - "Verify the server is reachable"
    """
    moodle = get_moodle_client(ctx)
    site_info = await moodle.get_site_info()

    # If we get here, connection is successful
    result = f"""✓ **Connection Successful**

**Site:** {site_info.get('sitename')}
**URL:** {site_info.get('siteurl')}
**Version:** {site_info.get('release')} (Moodle {site_info.get('version')})
**User:** {site_info.get('fullname')} ({site_info.get('username')})
**User ID:** {site_info.get('userid')}

The Moodle API is accessible and authentication is working correctly.
"""
    return result

@mcp.tool(
    name="moodle_get_available_functions",
    description="List all Moodle Web Services API functions available to the authenticated user. NO PARAMETERS REQUIRED. Optional: format ('markdown' or 'json', default='markdown'). Shows which API endpoints your token can access - useful for debugging permissions.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_available_functions(
    format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' (default) or 'json'"
    ),
    ctx: Context = None
) -> str:
    """
    Get list of available Moodle Web Service functions enabled for the current user.

    This tool shows which API functions the current authentication token can access.
    Useful for debugging permissions or discovering available functionality.

    Args:
        format: Output format (markdown or json)
        ctx: FastMCP context (automatically injected)

    Returns:
        List of available API functions

    Example use cases:
        - "What API functions can I use?"
        - "List available web services"
        - "Show me my API permissions"
    """
    moodle = get_moodle_client(ctx)
    site_info = await moodle.get_site_info()

    functions = site_info.get('functions', [])

    if not functions:
        return "No functions information available. This may indicate limited API access."

    response_data = {"functions": functions, "total_count": len(functions)}
    return format_response(response_data, "Available Moodle Web Service Functions", format)
