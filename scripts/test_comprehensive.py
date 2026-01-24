#!/usr/bin/env python3
"""
Comprehensive test of ALL Moodle MCP tools - READ ONLY operations.
First discovers valid IDs (courses, users) then tests tools with those IDs.

Run with: python test_comprehensive.py
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


async def test_comprehensive():
    """Test all tools comprehensively by discovering IDs first."""
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

    print("="*80)
    print("MOODLE MCP COMPREHENSIVE TEST SUITE (READ-ONLY)")
    print("="*80)
    print(f"Server: {config.url}")
    print()
    print("Phase 1: Discovering valid IDs from server...")
    print("="*80)

    # Phase 1: Discover valid IDs
    discovered_ids = {
        'course_id': None,
        'user_id': None,
        'current_user_id': None,
    }

    try:
        # Get current user ID
        import json
        result = await get_callable(users.moodle_get_current_user)(format="json", ctx=ctx)
        if result:
            data = json.loads(result)
            if 'userid' in data:
                discovered_ids['current_user_id'] = data['userid']
                print(f"✓ Found current user ID: {discovered_ids['current_user_id']}")
    except Exception as e:
        print(f"✗ Could not get current user ID: {e}")

    # Try to get a course ID (needs user_id first)
    if discovered_ids['current_user_id']:
        try:
            result = await get_callable(courses.moodle_list_user_courses)(
                user_id=discovered_ids['current_user_id'],
                format="json",
                ctx=ctx
            )
            if result:
                data = json.loads(result)
                if data.get('courses') and len(data['courses']) > 0:
                    discovered_ids['course_id'] = data['courses'][0]['id']
                    print(f"✓ Found course ID: {discovered_ids['course_id']}")
        except Exception as e:
            print(f"✗ Could not get course ID: {str(e)[:100]}")

    # Use current user ID as user_id for tests
    if discovered_ids['current_user_id']:
        discovered_ids['user_id'] = discovered_ids['current_user_id']

    print()
    print("="*80)
    print("Phase 2: Testing all tools with discovered IDs...")
    print("="*80)
    print()

    # Phase 2: Define all tests
    tools_to_test = []

    # Site tools (3) - No IDs needed
    tools_to_test.extend([
        ("Site", "moodle_get_site_info", get_callable(site.moodle_get_site_info), {"format": "markdown"}),
        ("Site", "moodle_test_connection", get_callable(site.moodle_test_connection), {}),
        ("Site", "moodle_get_available_functions", get_callable(site.moodle_get_available_functions), {"format": "markdown"}),
    ])

    # Course tools
    if discovered_ids['user_id']:
        tools_to_test.append(
            ("Course", "moodle_list_user_courses", get_callable(courses.moodle_list_user_courses),
             {"user_id": discovered_ids['user_id'], "format": "markdown"})
        )

    tools_to_test.extend([
        ("Course", "moodle_get_course_categories", get_callable(courses.moodle_get_course_categories), {"format": "markdown"}),
    ])

    if discovered_ids['user_id']:
        tools_to_test.append(
            ("Course", "moodle_get_recent_courses", get_callable(courses.moodle_get_recent_courses),
             {"user_id": discovered_ids['user_id'], "format": "markdown"})
        )

    # Add course-specific tools if we have a course ID
    if discovered_ids['course_id']:
        tools_to_test.extend([
            ("Course", "moodle_get_course_details", get_callable(courses.moodle_get_course_details),
             {"course_id": discovered_ids['course_id'], "format": "markdown"}),
            ("Course", "moodle_get_course_contents", get_callable(courses.moodle_get_course_contents),
             {"course_id": discovered_ids['course_id'], "format": "markdown"}),
            ("Course", "moodle_get_enrolled_users", get_callable(courses.moodle_get_enrolled_users),
             {"course_id": discovered_ids['course_id'], "format": "markdown"}),
        ])

    # User tools
    tools_to_test.extend([
        ("User", "moodle_get_current_user", get_callable(users.moodle_get_current_user), {"format": "markdown"}),
    ])

    # Add user-specific tools if we have a user ID
    if discovered_ids['user_id']:
        tools_to_test.extend([
            ("User", "moodle_get_user_profile", get_callable(users.moodle_get_user_profile),
             {"user_id": discovered_ids['user_id'], "format": "markdown"}),
            ("User", "moodle_get_user_preferences", get_callable(users.moodle_get_user_preferences),
             {"user_id": discovered_ids['user_id'], "format": "markdown"}),
        ])

    # Grade tools (require course or user ID)
    if discovered_ids['user_id']:
        tools_to_test.extend([
            ("Grade", "moodle_get_gradebook_overview", get_callable(grades.moodle_get_gradebook_overview),
             {"user_id": discovered_ids['user_id'], "format": "markdown"}),
            ("Grade", "moodle_get_student_grade_summary", get_callable(grades.moodle_get_student_grade_summary),
             {"user_id": discovered_ids['user_id'], "format": "markdown"}),
        ])

    if discovered_ids['course_id'] and discovered_ids['user_id']:
        tools_to_test.extend([
            ("Grade", "moodle_get_course_grades", get_callable(grades.moodle_get_course_grades),
             {"course_id": discovered_ids['course_id'], "user_id": discovered_ids['user_id'], "format": "markdown"}),
            ("Grade", "moodle_get_user_grades", get_callable(grades.moodle_get_user_grades),
             {"course_id": discovered_ids['course_id'], "user_id": discovered_ids['user_id'], "format": "markdown"}),
        ])

    if discovered_ids['course_id']:
        tools_to_test.extend([
            ("Grade", "moodle_get_grade_items", get_callable(grades.moodle_get_grade_items),
             {"course_id": discovered_ids['course_id'], "format": "markdown"}),
            ("Grade", "moodle_get_grade_report", get_callable(grades.moodle_get_grade_report),
             {"course_id": discovered_ids['course_id'], "format": "markdown"}),
        ])

    # Assignment tools
    if discovered_ids['user_id']:
        tools_to_test.append(
            ("Assignment", "moodle_get_user_assignments", get_callable(assignments.moodle_get_user_assignments),
             {"user_id": discovered_ids['user_id'], "format": "markdown"})
        )

    if discovered_ids['course_id']:
        tools_to_test.append(
            ("Assignment", "moodle_list_assignments", get_callable(assignments.moodle_list_assignments),
             {"course_id": discovered_ids['course_id'], "format": "markdown"})
        )

    # Message tools (no IDs needed for these)
    tools_to_test.extend([
        ("Message", "moodle_get_messages", get_callable(messages.moodle_get_messages), {"format": "markdown"}),
        ("Message", "moodle_get_unread_count", get_callable(messages.moodle_get_unread_count), {}),
    ])

    # Calendar tools
    tools_to_test.extend([
        ("Calendar", "moodle_get_calendar_events", get_callable(calendar.moodle_get_calendar_events), {"format": "markdown"}),
        ("Calendar", "moodle_get_upcoming_events", get_callable(calendar.moodle_get_upcoming_events), {"format": "markdown"}),
    ])

    if discovered_ids['course_id']:
        tools_to_test.append(
            ("Calendar", "moodle_get_course_events", get_callable(calendar.moodle_get_course_events),
             {"course_id": discovered_ids['course_id'], "format": "markdown"})
        )

    # Run all tests
    results = {}
    total = len(tools_to_test)

    for i, (category, tool_name, tool_func, kwargs) in enumerate(tools_to_test, 1):
        print(f"[{i}/{total}] Testing {tool_name}...", end=" ", flush=True)
        try:
            result = await tool_func(**kwargs, ctx=ctx)
            if isinstance(result, str) and len(result) > 0:
                # Check for error messages
                if ("error" in result.lower() and "unexpected" in result.lower()) or "failed" in result.lower():
                    status = "✗ FAIL"
                else:
                    status = "✓ PASS"
            else:
                status = "✗ FAIL (empty)"
            results[tool_name] = (category, status, None)
            print(status)
        except Exception as e:
            error_msg = str(e)[:80]
            results[tool_name] = (category, f"✗ ERROR", error_msg)
            print(f"✗ ERROR")
            if len(error_msg) < 60:
                print(f"    {error_msg}")

    # Print detailed results by category
    print()
    print("="*80)
    print("DETAILED RESULTS BY CATEGORY")
    print("="*80)

    categories = {}
    for tool_name, (category, status, error) in results.items():
        if category not in categories:
            categories[category] = []
        categories[category].append((tool_name, status, error))

    for category in sorted(categories.keys()):
        print(f"\n{category} Tools (READ-ONLY):")
        print("-" * 80)
        for tool_name, status, error in sorted(categories[category]):
            print(f"  {tool_name:50} {status}")
            if error:
                print(f"    → {error}")

    # Summary
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)

    passed = sum(1 for _, (_, status, _) in results.items() if status == "✓ PASS")
    failed = sum(1 for _, (_, status, _) in results.items() if status.startswith("✗ FAIL"))
    errors = sum(1 for _, (_, status, _) in results.items() if status.startswith("✗ ERROR"))

    print(f"Total Tests: {len(results)}")
    print(f"  ✓ Passed:  {passed}")
    print(f"  ✗ Failed:  {failed}")
    print(f"  ✗ Errors:  {errors}")
    print()

    success_rate = (passed / len(results) * 100) if results else 0
    print(f"Success Rate: {success_rate:.1f}%")
    print()
    print("Discovered IDs used for testing:")
    for key, value in discovered_ids.items():
        if value:
            print(f"  {key}: {value}")
    print()
    print("="*80)
    print("NOTE: All tested tools are READ-ONLY operations.")
    print("No data was modified during these tests.")
    print("="*80)

    await client.close()

    return errors == 0 and failed == 0


if __name__ == "__main__":
    try:
        success = asyncio.run(test_comprehensive())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
