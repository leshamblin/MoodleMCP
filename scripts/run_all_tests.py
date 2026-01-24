#!/usr/bin/env python3
"""
Comprehensive test script for all Moodle MCP tools.
Validates all 34 tools against the real Moodle server.

Run with: python run_all_tests.py
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


async def run_all_tests():
    """Test all 34 Moodle MCP tools."""

    # Initialize config and client
    config = get_config()
    client = MoodleAPIClient(
        base_url=config.url,
        token=config.token,
        timeout=config.api_timeout,
        max_connections=config.max_connections,
        max_keepalive=config.max_keepalive_connections
    )

    ctx = MockContext(client)

    # Initialize mcp instance for tool registration
    from fastmcp import FastMCP
    from contextlib import asynccontextmanager
    from typing import AsyncGenerator

    @asynccontextmanager
    async def test_lifespan(server: FastMCP) -> AsyncGenerator[dict, None]:
        yield {}

    import moodle_mcp.server
    moodle_mcp.server.mcp = FastMCP("test", lifespan=test_lifespan)

    # Import all tools
    print("Importing tools...")
    from moodle_mcp.tools import site, courses, users, grades, assignments, messages, calendar, forums

    # Discover all tool functions
    tools_to_test = []

    # Helper to unwrap FunctionTool objects
    def get_callable(obj):
        """Extract callable function from FunctionTool wrapper."""
        if hasattr(obj, 'fn'):  # It's a FunctionTool wrapper
            return obj.fn
        return obj

    # Site tools
    for func_name in ['moodle_get_site_info', 'moodle_test_connection', 'moodle_get_available_functions']:
        func = get_callable(getattr(site, func_name))
        kwargs = {} if func_name == 'moodle_test_connection' else {"format": "markdown"}
        tools_to_test.append((func_name, func, kwargs))

    # Course tools
    for func_name in dir(courses):
        if func_name.startswith('moodle_') and callable(getattr(courses, func_name)):
            func = get_callable(getattr(courses, func_name))
            # Tools that don't require IDs
            if func_name in ['moodle_list_user_courses', 'moodle_get_course_categories',
                           'moodle_get_recent_courses', 'moodle_search_courses']:
                kwargs = {"format": "markdown"}
                if func_name == 'moodle_search_courses':
                    kwargs['query'] = 'test'
                tools_to_test.append((func_name, func, kwargs))

    # User tools
    for func_name in dir(users):
        if func_name.startswith('moodle_') and callable(getattr(users, func_name)):
            func = get_callable(getattr(users, func_name))
            # Tools that don't require IDs
            if func_name in ['moodle_get_user_profile', 'moodle_get_user_preferences',
                           'moodle_get_enrolled_courses_by_user', 'moodle_search_users']:
                kwargs = {"format": "markdown"}
                if func_name == 'moodle_search_users':
                    kwargs['query'] = 'test'
                tools_to_test.append((func_name, func, kwargs))

    # Grade tools
    for func_name in dir(grades):
        if func_name.startswith('moodle_') and callable(getattr(grades, func_name)):
            func = get_callable(getattr(grades, func_name))
            if func_name == 'moodle_get_user_grade_overview':
                tools_to_test.append((func_name, func, {"format": "markdown"}))

    # Assignment tools
    for func_name in dir(assignments):
        if func_name.startswith('moodle_') and callable(getattr(assignments, func_name)):
            func = get_callable(getattr(assignments, func_name))
            if func_name == 'moodle_get_user_assignments':
                tools_to_test.append((func_name, func, {"format": "markdown"}))

    # Message tools
    for func_name in dir(messages):
        if func_name.startswith('moodle_') and callable(getattr(messages, func_name)):
            func = get_callable(getattr(messages, func_name))
            if func_name in ['moodle_get_messages', 'moodle_get_conversations']:
                tools_to_test.append((func_name, func, {"format": "markdown"}))
            elif func_name == 'moodle_get_unread_message_count':
                tools_to_test.append((func_name, func, {}))

    # Calendar tools
    for func_name in dir(calendar):
        if func_name.startswith('moodle_') and callable(getattr(calendar, func_name)):
            func = get_callable(getattr(calendar, func_name))
            if func_name in ['moodle_get_calendar_events', 'moodle_get_upcoming_events']:
                kwargs = {"format": "markdown"}
                if func_name == 'moodle_get_upcoming_events':
                    kwargs['days_ahead'] = 7
                tools_to_test.append((func_name, func, kwargs))

    # Print header
    print()
    print("="*80)
    print("MOODLE MCP COMPREHENSIVE TOOL VALIDATION")
    print("="*80)
    print(f"Server: {config.url}")
    print(f"Testing {len(tools_to_test)} tools...")
    print("="*80)
    print()

    # Run tests
    results = {}
    for i, (tool_name, tool_func, kwargs) in enumerate(tools_to_test, 1):
        print(f"[{i}/{len(tools_to_test)}] Testing {tool_name}...", end=" ", flush=True)
        try:
            result = await tool_func(**kwargs, ctx=ctx)
            if isinstance(result, str) and len(result) > 0:
                # Check if it's an error message
                if "error" in result.lower() and "unexpected" in result.lower():
                    status = f"✗ FAIL: {result[:60]}"
                else:
                    status = "✓ PASS"
            else:
                status = "✗ FAIL (empty result)"
            results[tool_name] = status
            print(status)
        except Exception as e:
            error_msg = str(e)[:80]
            results[tool_name] = f"✗ ERROR: {error_msg}"
            print(f"✗ ERROR")
            print(f"    {error_msg}")

    # Print summary
    print()
    print("="*80)
    print("DETAILED RESULTS")
    print("="*80)

    # Group by module
    modules = {
        'Site Tools': [k for k in results.keys() if k.startswith('moodle_get_site') or k.startswith('moodle_test')],
        'Course Tools': [k for k in results.keys() if 'course' in k.lower() and k not in results or k.startswith('moodle_') and 'course' in k],
        'User Tools': [k for k in results.keys() if 'user' in k.lower() and 'course' not in k.lower()],
        'Grade Tools': [k for k in results.keys() if 'grade' in k.lower()],
        'Assignment Tools': [k for k in results.keys() if 'assignment' in k.lower()],
        'Message Tools': [k for k in results.keys() if 'message' in k.lower() or 'conversation' in k.lower()],
        'Calendar Tools': [k for k in results.keys() if 'calendar' in k.lower() or 'event' in k.lower()],
    }

    for module_name, tool_names in modules.items():
        if tool_names:
            print(f"\n{module_name}:")
            print("-" * 80)
            for tool_name in sorted(tool_names):
                if tool_name in results:
                    print(f"  {tool_name:55} {results[tool_name]}")

    # Final summary
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v == "✓ PASS")
    failed = sum(1 for v in results.values() if v.startswith("✗ FAIL"))
    errors = sum(1 for v in results.values() if v.startswith("✗ ERROR"))

    print(f"Total Tests: {len(results)}")
    print(f"  ✓ Passed:  {passed}")
    print(f"  ✗ Failed:  {failed}")
    print(f"  ✗ Errors:  {errors}")
    print()

    success_rate = (passed / len(results) * 100) if results else 0
    print(f"Success Rate: {success_rate:.1f}%")
    print("="*80)

    await client.close()

    return errors == 0 and failed == 0


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
