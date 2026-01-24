#!/usr/bin/env python3
"""
Simple test script to validate all Moodle MCP tools against the real server.

Run with: python test_all_tools.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from moodle_mcp.core.client import MoodleAPIClient
from moodle_mcp.core.config import get_config


class MockContext:
    """Mock FastMCP Context for testing."""
    def __init__(self, moodle_client: MoodleAPIClient):
        self.request_context = MockRequestContext(moodle_client)


class MockRequestContext:
    """Mock request context with lifespan_context."""
    def __init__(self, moodle_client: MoodleAPIClient):
        self.lifespan_context = {"moodle_client": moodle_client}


async def test_tools():
    """Test all tools that don't require parameters."""
    config = get_config()
    client = MoodleAPIClient(
        base_url=config.url,
        token=config.token,
        timeout=config.api_timeout,
        max_connections=config.max_connections,
        max_keepalive=config.max_keepalive_connections
    )

    ctx = MockContext(client)

    # Import tools AFTER creating mcp instance
    from fastmcp import FastMCP
    from contextlib import asynccontextmanager
    from typing import AsyncGenerator

    @asynccontextmanager
    async def test_lifespan(server: FastMCP) -> AsyncGenerator[dict, None]:
        yield {}

    import moodle_mcp.server
    moodle_mcp.server.mcp = FastMCP("test", lifespan=test_lifespan)

    # Now import tools
    from moodle_mcp.tools.site import (
        moodle_get_site_info, moodle_test_connection, moodle_get_available_functions
    )
    from moodle_mcp.tools.courses import (
        moodle_list_user_courses, moodle_get_course_categories, moodle_get_recent_courses
    )
    from moodle_mcp.tools.users import (
        moodle_get_user_profile, moodle_get_user_preferences, moodle_get_current_user
    )
    from moodle_mcp.tools.grades import moodle_get_user_grade_overview
    from moodle_mcp.tools.assignments import moodle_get_user_assignments
    from moodle_mcp.tools.messages import (
        moodle_get_messages, moodle_get_conversations, moodle_get_unread_message_count
    )
    from moodle_mcp.tools.calendar import moodle_get_calendar_events, moodle_get_upcoming_events

    # Helper to unwrap FunctionTool objects
    def get_callable(obj):
        """Extract callable function from FunctionTool wrapper."""
        if hasattr(obj, 'fn'):
            return obj.fn
        return obj

    # Test tools (all READ-ONLY operations)
    tools_to_test = [
        # Site tools (3)
        ("moodle_get_site_info", get_callable(moodle_get_site_info), {"format": "markdown"}),
        ("moodle_test_connection", get_callable(moodle_test_connection), {}),
        ("moodle_get_available_functions", get_callable(moodle_get_available_functions), {"format": "markdown"}),

        # Course tools (3)
        ("moodle_list_user_courses", get_callable(moodle_list_user_courses), {"format": "markdown"}),
        ("moodle_get_course_categories", get_callable(moodle_get_course_categories), {"format": "markdown"}),
        ("moodle_get_recent_courses", get_callable(moodle_get_recent_courses), {"format": "markdown"}),

        # User tools (3)
        ("moodle_get_user_profile", get_callable(moodle_get_user_profile), {"format": "markdown"}),
        ("moodle_get_user_preferences", get_callable(moodle_get_user_preferences), {"format": "markdown"}),
        ("moodle_get_current_user", get_callable(moodle_get_current_user), {"format": "markdown"}),

        # Grades tools (1)
        ("moodle_get_user_grade_overview", get_callable(moodle_get_user_grade_overview), {"format": "markdown"}),

        # Assignment tools (1)
        ("moodle_get_user_assignments", get_callable(moodle_get_user_assignments), {"format": "markdown"}),

        # Message tools (3)
        ("moodle_get_messages", get_callable(moodle_get_messages), {"format": "markdown"}),
        ("moodle_get_conversations", get_callable(moodle_get_conversations), {"format": "markdown"}),
        ("moodle_get_unread_message_count", get_callable(moodle_get_unread_message_count), {}),

        # Calendar tools (2)
        ("moodle_get_calendar_events", get_callable(moodle_get_calendar_events), {"format": "markdown"}),
        ("moodle_get_upcoming_events", get_callable(moodle_get_upcoming_events), {"format": "markdown"}),
    ]

    print("="*70)
    print("MOODLE MCP TOOL VALIDATION")
    print("="*70)
    print(f"Testing {len(tools_to_test)} tools against live server...")
    print()

    results = {}
    for tool_name, tool_func, kwargs in tools_to_test:
        try:
            result = await tool_func(**kwargs, ctx=ctx)
            status = "✓ PASS" if isinstance(result, str) and len(result) > 0 else "✗ FAIL (empty)"
            results[tool_name] = status
        except Exception as e:
            results[tool_name] = f"✗ ERROR: {str(e)[:60]}"

    # Print results
    print("="*70)
    print("RESULTS")
    print("="*70)
    for tool_name, status in results.items():
        print(f"{tool_name:50} {status}")
    print("="*70)

    # Summary
    passed = sum(1 for v in results.values() if v.startswith("✓"))
    failed = len(results) - passed

    print(f"\nSummary: {passed}/{len(results)} passed, {failed} failed")

    await client.close()

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(test_tools())
    sys.exit(0 if success else 1)
