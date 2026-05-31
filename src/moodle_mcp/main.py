"""
Main entry point for Moodle MCP server with lifespan management.

This module sets up the server lifespan context, which provides persistent
connections and configuration to all tools via Context injection.
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# Add src directory to path for imports to work when run directly
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from fastmcp import FastMCP
from moodle_mcp.core.client import MoodleAPIClient
from moodle_mcp.core.config import get_config

@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncGenerator[dict, None]:
    """
    Manage server lifespan: initialize resources on startup, cleanup on shutdown.

    The yielded dictionary is accessible to all tools via ctx.request_context.lifespan_context.
    This allows sharing the Moodle API client connection pool across all tool calls.

    Args:
        server: The FastMCP server instance

    Yields:
        dict: Context dictionary with 'moodle_client' and 'config' keys
    """
    config = get_config()

    print("Initializing Moodle MCP server...", file=sys.stderr)
    print(f"Environment: {config.environment_name}", file=sys.stderr)

    # SAFETY WARNING for production
    if config.is_production:
        print("⚠️  WARNING: Using PRODUCTION instance!", file=sys.stderr)
        print("⚠️  Set MOODLE_ENV=dev or unset to use development", file=sys.stderr)

    print(f"Connecting to: {config.url}", file=sys.stderr)

    # Initialize Moodle API client with connection pooling
    moodle_client = MoodleAPIClient(
        base_url=config.url,
        token=config.token,
        timeout=config.api_timeout,
        max_connections=config.max_connections,
        max_keepalive=config.max_keepalive_connections
    )

    # Test connection on startup
    try:
        site_info = await moodle_client.get_site_info()
        print(f"✓ Connected to Moodle: {site_info.get('sitename')}", file=sys.stderr)
        print(f"✓ User: {site_info.get('fullname')} ({site_info.get('username')})", file=sys.stderr)
        print(f"✓ Version: {site_info.get('release')}", file=sys.stderr)
    except Exception as e:
        print(f"⚠ Warning: Could not verify Moodle connection: {e}", file=sys.stderr)
        print("  Server will continue, but API calls may fail.", file=sys.stderr)

    # Count tools after they're registered (public API in FastMCP 3.x)
    try:
        tool_count = len(await server.list_tools())
    except Exception:
        tool_count = 0
    print(f"Server ready with {tool_count} tools registered.\n", file=sys.stderr)

    # Yield context available to all tools via ctx.request_context.lifespan_context
    yield {
        "moodle_client": moodle_client,
        "config": config
    }

    # Cleanup on shutdown
    print("\nShutting down Moodle MCP server...", file=sys.stderr)
    await moodle_client.close()
    print("✓ Moodle MCP server shutdown complete", file=sys.stderr)

# Create FastMCP server with lifespan BEFORE importing tools
mcp = FastMCP(
    name="moodle_mcp",
    instructions=(
        "Read and write access to a Moodle LMS (courses, users, grades, "
        "assignments, quizzes, forums, groups, calendar, messages, badges, "
        "completion).\n\n"
        "You rarely need to look up IDs first: most tools accept human-friendly "
        "references and resolve them internally -- a user by id, username, or "
        "email; a course by id, shortname, or idnumber; an activity by its name. "
        "Pass the name you already have.\n\n"
        "Write operations are guarded for safety. In DEV they are allowed only on "
        "whitelisted courses (default: course 7299); in PROD they are blocked "
        "unless explicitly enabled. A blocked write returns a clear 'blocked for "
        "safety' error -- do not retry it against the same course.\n\n"
        "Start with moodle_get_site_info to confirm the connection and identity, "
        "or moodle_list_user_courses to see what a user can access."
    ),
    lifespan=lifespan
)

# Set the mcp instance in server.py so tools can register with it
import moodle_mcp.server
moodle_mcp.server.mcp = mcp

# Import all tool modules AFTER setting mcp instance.
# These imports have side effects - they register tools with the server via the
# @mcp.tool decorator, so the names are intentionally unused (noqa: F401).
from moodle_mcp.tools import (  # noqa: F401
    site, courses, users, grades, assignments, messages, calendar,
    forums, groups, enrollment, quiz, completion, badges,
)

# PROD write lockdown: when running against production with writes disabled,
# hide every write-tagged tool from the client entirely. This is belt-and-
# suspenders with the @require_write_permission decorator (which blocks at
# call time); disabling by tag also removes them from tool listings.
# (Write tools are tagged {"write"} during the per-module refactor.)
_config = get_config()
if _config.is_production and not _config.prod_allow_writes:
    try:
        mcp.disable(tags={"write"})
        print("⚠️  PROD write lockdown: 'write'-tagged tools disabled.", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  Could not apply PROD write lockdown via tags: {e}", file=sys.stderr)

def main():
    """Entry point for running the server."""
    # Use stdio transport for Claude Desktop integration (default)
    # Use --http flag for local development/debugging
    if "--http" in sys.argv:
        # HTTP mode for development/debugging
        mcp.run(transport="http", host="localhost", port=8000)
    else:
        # Default to stdio for Claude Desktop
        mcp.run()

if __name__ == "__main__":
    main()
