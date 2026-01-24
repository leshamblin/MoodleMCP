"""
Pytest configuration for Moodle MCP tests.

IMPORTANT: All tests ALWAYS use DEVELOPMENT server with course 7299 whitelisted.
"""

import sys
import os
from pathlib import Path

# FORCE DEVELOPMENT MODE FOR ALL TESTS
# This ensures tests never touch production and only use whitelisted course 7299
os.environ['MOODLE_ENV'] = 'dev'
os.environ['MOODLE_DEV_COURSE_WHITELIST'] = '7299'

print("="*80)
print("PYTEST CONFIGURATION: Forcing DEVELOPMENT mode")
print("  MOODLE_ENV=dev")
print("  MOODLE_DEV_COURSE_WHITELIST=7299")
print("="*80)

# Add src directory to Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

# Initialize the mcp instance before importing tools
from fastmcp import FastMCP
import moodle_mcp.server

# Create a dummy lifespan for tests
from contextlib import asynccontextmanager
from typing import AsyncGenerator

@asynccontextmanager
async def test_lifespan(server: FastMCP) -> AsyncGenerator[dict, None]:
    """Dummy lifespan for tests - actual client is provided by fixtures."""
    yield {}

# Create mcp instance for tool registration
moodle_mcp.server.mcp = FastMCP(
    name="moodle_mcp_test",
    instructions="Test server",
    lifespan=test_lifespan
)

# Import all tool modules to register tools with the test mcp instance
from moodle_mcp.tools import (
    site, courses, users, grades, assignments, messages,
    calendar, forums, groups, enrollment, quiz, completion, badges
)

# Import test helpers for dynamic tool discovery
import pytest
from moodle_mcp.core.client import MoodleAPIClient
from moodle_mcp.core.config import get_config
from .test_helpers import discover_tools, MockContext


@pytest.fixture(scope="session")
def all_tools():
    """
    Dynamically discover all registered tools.

    Returns a dictionary of tool_name -> callable for all registered tools.
    This eliminates the need to manually import and list every tool.

    Example:
        def test_site_info(all_tools):
            get_site_info = all_tools['moodle_get_site_info']
            result = await get_site_info(ctx=ctx)
    """
    return discover_tools(moodle_mcp.server.mcp)


@pytest.fixture
async def moodle_client():
    """
    Create a Moodle API client for each test.

    The client is automatically configured from environment variables
    and includes the current user ID for convenience.
    """
    config = get_config()
    client = MoodleAPIClient(
        base_url=config.url,
        token=config.token,
        timeout=config.api_timeout,
        max_connections=config.max_connections,
        max_keepalive=config.max_keepalive_connections
    )

    # Get site info to have user_id available
    site_info = await client.get_site_info()
    client.current_user_id = site_info.get('userid')

    yield client

    # Close client safely
    try:
        await client.close()
    except RuntimeError:
        # Event loop already closed, ignore
        pass


@pytest.fixture
def ctx(moodle_client):
    """
    Create a mock context for each test.

    The context includes the moodle_client and config in lifespan_context,
    matching the structure used by the real FastMCP server.
    """
    return MockContext(moodle_client)
