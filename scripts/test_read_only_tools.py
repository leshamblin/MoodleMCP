#!/usr/bin/env python3
"""
Test all READ-ONLY Moodle MCP tools that don't require specific IDs.
These tools only read data from Moodle - no modifications.

Run with: python test_read_only_tools.py
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


async def test_read_only_tools():
    """Test all READ-ONLY tools that don't require parameters."""
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

    # Import all tool modules
    from moodle_mcp.tools import site, courses, users, grades, assignments, messages, calendar

    # Helper to unwrap FunctionTool objects
    def get_callable(obj):
        """Extract callable function from FunctionTool wrapper."""
        if hasattr(obj, 'fn'):
            return obj.fn
        return obj

    # Define READ-ONLY tools to test (no IDs required)
    tools_to_test = [
        # Site tools (3) - READ ONLY
        ("moodle_get_site_info", get_callable(site.moodle_get_site_info), {"format": "markdown"}),
        ("moodle_test_connection", get_callable(site.moodle_test_connection), {}),
        ("moodle_get_available_functions", get_callable(site.moodle_get_available_functions), {"format": "markdown"}),

        # Course tools (3) - READ ONLY
        ("moodle_list_user_courses", get_callable(courses.moodle_list_user_courses), {"format": "markdown"}),
        ("moodle_get_course_categories", get_callable(courses.moodle_get_course_categories), {"format": "markdown"}),
        ("moodle_get_recent_courses", get_callable(courses.moodle_get_recent_courses), {"format": "markdown"}),

        # User tools (3) - READ ONLY
        ("moodle_get_user_profile", get_callable(users.moodle_get_user_profile), {"format": "markdown"}),
        ("moodle_get_user_preferences", get_callable(users.moodle_get_user_preferences), {"format": "markdown"}),
        ("moodle_get_current_user", get_callable(users.moodle_get_current_user), {"format": "markdown"}),

        # Grades tools (2) - READ ONLY
        ("moodle_get_gradebook_overview", get_callable(grades.moodle_get_gradebook_overview), {"format": "markdown"}),
        ("moodle_get_student_grade_summary", get_callable(grades.moodle_get_student_grade_summary), {"format": "markdown"}),

        # Assignment tools (1) - READ ONLY
        ("moodle_get_user_assignments", get_callable(assignments.moodle_get_user_assignments), {"format": "markdown"}),

        # Message tools (2) - READ ONLY
        ("moodle_get_messages", get_callable(messages.moodle_get_messages), {"format": "markdown"}),
        ("moodle_get_unread_count", get_callable(messages.moodle_get_unread_count), {}),

        # Calendar tools (2) - READ ONLY
        ("moodle_get_calendar_events", get_callable(calendar.moodle_get_calendar_events), {"format": "markdown"}),
        ("moodle_get_upcoming_events", get_callable(calendar.moodle_get_upcoming_events), {"format": "markdown"}),
    ]

    print("="*80)
    print("MOODLE MCP READ-ONLY TOOL VALIDATION")
    print("="*80)
    print(f"Server: {config.url}")
    print(f"Testing {len(tools_to_test)} READ-ONLY tools...")
    print("="*80)
    print()

    results = {}
    for i, (tool_name, tool_func, kwargs) in enumerate(tools_to_test, 1):
        print(f"[{i}/{len(tools_to_test)}] Testing {tool_name}...", end=" ", flush=True)
        try:
            result = await tool_func(**kwargs, ctx=ctx)
            if isinstance(result, str) and len(result) > 0:
                # Check for error messages
                if "error" in result.lower() and ("unexpected" in result.lower() or "failed" in result.lower()):
                    status = "✗ FAIL"
                else:
                    status = "✓ PASS"
            else:
                status = "✗ FAIL (empty)"
            results[tool_name] = status
            print(status)
        except Exception as e:
            error_msg = str(e)[:80]
            results[tool_name] = f"✗ ERROR: {error_msg}"
            print(f"✗ ERROR")
            print(f"    {error_msg}")

    # Print detailed results
    print()
    print("="*80)
    print("DETAILED RESULTS BY CATEGORY")
    print("="*80)

    categories = {
        'Site Tools (READ ONLY)': [k for k in results.keys() if k.startswith('moodle_get_site') or k.startswith('moodle_test')],
        'Course Tools (READ ONLY)': [k for k in results.keys() if k.startswith('moodle_list_user_courses') or k.startswith('moodle_get_course') or k.startswith('moodle_get_recent')],
        'User Tools (READ ONLY)': [k for k in results.keys() if k.startswith('moodle_get_user') or k.startswith('moodle_get_current')],
        'Grade Tools (READ ONLY)': [k for k in results.keys() if 'grade' in k.lower()],
        'Assignment Tools (READ ONLY)': [k for k in results.keys() if 'assignment' in k.lower()],
        'Message Tools (READ ONLY)': [k for k in results.keys() if 'message' in k.lower() or 'unread' in k.lower()],
        'Calendar Tools (READ ONLY)': [k for k in results.keys() if 'calendar' in k.lower() or 'upcoming' in k.lower()],
    }

    for category_name, tool_names in categories.items():
        if tool_names:
            print(f"\n{category_name}:")
            print("-" * 80)
            for tool_name in sorted(tool_names):
                if tool_name in results:
                    print(f"  {tool_name:50} {results[tool_name]}")

    # Summary
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v == "✓ PASS")
    failed = sum(1 for v in results.values() if v.startswith("✗ FAIL"))
    errors = sum(1 for v in results.values() if v.startswith("✗ ERROR"))

    print(f"Total READ-ONLY Tests: {len(results)}")
    print(f"  ✓ Passed:  {passed}")
    print(f"  ✗ Failed:  {failed}")
    print(f"  ✗ Errors:  {errors}")
    print()

    success_rate = (passed / len(results) * 100) if results else 0
    print(f"Success Rate: {success_rate:.1f}%")
    print("="*80)
    print()
    print("NOTE: All tested tools are READ-ONLY operations.")
    print("No data was modified during these tests.")
    print("="*80)

    await client.close()

    return errors == 0 and failed == 0


if __name__ == "__main__":
    try:
        success = asyncio.run(test_read_only_tools())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
