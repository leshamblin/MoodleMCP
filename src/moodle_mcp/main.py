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

    print(f"Initializing Moodle MCP server...", file=sys.stderr)
    print(f"Environment: {config.environment_name}", file=sys.stderr)

    # SAFETY WARNING for production
    if config.is_production:
        print(f"⚠️  WARNING: Using PRODUCTION instance!", file=sys.stderr)
        print(f"⚠️  Set MOODLE_ENV=dev or unset to use development", file=sys.stderr)

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
        print(f"  Server will continue, but API calls may fail.", file=sys.stderr)

    # Count tools after they're registered
    tool_count = len(server._tool_manager._tools) if hasattr(server, '_tool_manager') else 0
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
    instructions="Moodle LMS integration server providing read-only access to Moodle Web Services API",
    lifespan=lifespan
)

# Set the mcp instance in server.py so tools can register with it
import moodle_mcp.server
moodle_mcp.server.mcp = mcp

# Import all tool modules AFTER setting mcp instance
# These imports have side effects - they register tools with the server
from moodle_mcp.tools import site, courses, users, grades, assignments, messages, calendar, forums, groups, enrollment, quiz, completion, badges

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
