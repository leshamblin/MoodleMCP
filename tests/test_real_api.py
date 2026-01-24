"""
Real API integration tests - calls live Moodle server with actual data.

These tests use the real API and verify that tools work correctly with live data.
Run with: pytest tests/test_real_api.py -v
"""

import pytest
import os
import json
from fastmcp import Context

# Force DEV mode for all tests
os.environ['MOODLE_ENV'] = 'dev'
os.environ['MOODLE_DEV_COURSE_WHITELIST'] = '7299'

from moodle_mcp.core.client import MoodleAPIClient
from moodle_mcp.core.config import get_config

# Import tools and unwrap them
from moodle_mcp.tools.site import (
    moodle_get_site_info,
    moodle_test_connection,
    moodle_get_available_functions
)
from moodle_mcp.tools.courses import (
    moodle_list_user_courses,
    moodle_get_course_details,
    moodle_get_course_contents,
    moodle_get_enrolled_users
)
from moodle_mcp.tools.users import (
    moodle_get_current_user,
    moodle_get_user_profile,
    moodle_get_course_participants
)
from moodle_mcp.tools.groups import (
    moodle_get_course_groups,
    moodle_get_group_members,
    moodle_add_group_members
)
from moodle_mcp.tools.completion import (
    moodle_get_course_completion_status,
    moodle_get_activities_completion_status
)
from moodle_mcp.tools.badges import (
    moodle_get_user_badges
)

# Unwrap FunctionTool objects
def unwrap_tool(tool):
    """Unwrap a FunctionTool to get the underlying function."""
    return tool.fn if hasattr(tool, 'fn') else tool

# Unwrap all tools
moodle_get_site_info = unwrap_tool(moodle_get_site_info)
moodle_test_connection = unwrap_tool(moodle_test_connection)
moodle_get_available_functions = unwrap_tool(moodle_get_available_functions)
moodle_list_user_courses = unwrap_tool(moodle_list_user_courses)
moodle_get_course_details = unwrap_tool(moodle_get_course_details)
moodle_get_course_contents = unwrap_tool(moodle_get_course_contents)
moodle_get_enrolled_users = unwrap_tool(moodle_get_enrolled_users)
moodle_get_current_user = unwrap_tool(moodle_get_current_user)
moodle_get_user_profile = unwrap_tool(moodle_get_user_profile)
moodle_get_course_groups = unwrap_tool(moodle_get_course_groups)
moodle_get_group_members = unwrap_tool(moodle_get_group_members)
moodle_add_group_members = unwrap_tool(moodle_add_group_members)
moodle_get_course_participants = unwrap_tool(moodle_get_course_participants)
moodle_get_course_completion_status = unwrap_tool(moodle_get_course_completion_status)
moodle_get_activities_completion_status = unwrap_tool(moodle_get_activities_completion_status)
moodle_get_user_badges = unwrap_tool(moodle_get_user_badges)


class MockContext:
    """Mock FastMCP Context for testing."""

    def __init__(self, moodle_client: MoodleAPIClient):
        self.request_context = MockRequestContext(moodle_client)


class MockRequestContext:
    """Mock request context with lifespan_context."""

    def __init__(self, moodle_client: MoodleAPIClient):
        self.lifespan_context = {
            "moodle_client": moodle_client,
            "config": get_config()
        }


@pytest.fixture
async def moodle_client():
    """Create a Moodle API client for each test."""
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
    """Create a mock context with the Moodle client."""
    return MockContext(moodle_client)


@pytest.mark.asyncio
class TestSiteTools:
    """Test site information tools with real API."""

    async def test_get_site_info_markdown(self, ctx):
        """Test getting site info in markdown format."""
        result = await moodle_get_site_info(format="markdown", ctx=ctx)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Moodle Projects" in result or "Site" in result
        print(f"\n📍 Site Info:\n{result[:200]}...")

    async def test_get_site_info_json(self, ctx):
        """Test getting site info in JSON format."""
        result = await moodle_get_site_info(format="json", ctx=ctx)

        assert isinstance(result, str)
        assert "{" in result  # JSON format
        print(f"\n📍 Site Info (JSON):\n{result[:200]}...")

    async def test_connection(self, ctx):
        """Test connection validation."""
        result = await moodle_test_connection(ctx=ctx)

        assert isinstance(result, str)
        assert "✓" in result or "success" in result.lower()
        print(f"\n✅ Connection Test:\n{result}")

    async def test_available_functions(self, ctx):
        """Test listing available functions."""
        result = await moodle_get_available_functions(format="markdown", ctx=ctx)

        assert isinstance(result, str)
        assert "function" in result.lower()
        # Should have many functions
        assert result.count("core_") > 10
        print(f"\n📋 Functions (first 200 chars):\n{result[:200]}...")


@pytest.mark.asyncio
class TestCourseTools:
    """Test course tools with real API."""

    async def test_list_user_courses(self, ctx, moodle_client):
        """Test listing user's courses."""
        result = await moodle_list_user_courses(
            user_id=moodle_client.current_user_id,
            format="markdown",
            ctx=ctx
        )

        assert isinstance(result, str)
        assert len(result) > 0
        # User should have at least one course
        assert "course" in result.lower() or "enrolled" in result.lower()
        print(f"\n📚 User Courses (first 300 chars):\n{result[:300]}...")

    async def test_get_course_details(self, ctx):
        """Test getting details for course 7299."""
        result = await moodle_get_course_details(
            course_id=7299,
            format="markdown",
            ctx=ctx
        )

        assert isinstance(result, str)
        assert "Elizabeth's Moodle Playground" in result or "MoodlePlayground" in result
        assert "7299" in result
        print(f"\n📖 Course Details:\n{result[:300]}...")

    async def test_get_course_contents(self, ctx, moodle_client):
        """Test getting course contents for course 7299."""
        result = await moodle_get_course_contents(
            course_id=7299,
            format="markdown",
            ctx=ctx
        )

        assert isinstance(result, str)
        assert len(result) > 0
        # Should have sections
        assert "section" in result.lower() or "module" in result.lower()
        print(f"\n📑 Course Contents (first 300 chars):\n{result[:300]}...")

    async def test_get_enrolled_users(self, ctx):
        """Test getting enrolled users for course 7299."""
        result = await moodle_get_enrolled_users(
            course_id=7299,
            limit=20,
            offset=0,
            format="markdown",
            ctx=ctx
        )

        assert isinstance(result, str)
        assert len(result) > 0
        # Should have at least the current user
        assert "user" in result.lower() or "enrolled" in result.lower()
        print(f"\n👥 Enrolled Users (first 300 chars):\n{result[:300]}...")


@pytest.mark.asyncio
class TestUserTools:
    """Test user tools with real API."""

    async def test_get_current_user(self, ctx):
        """Test getting current user info."""
        result = await moodle_get_current_user(format="markdown", ctx=ctx)

        assert isinstance(result, str)
        assert "Elizabeth" in result or "Shamblin" in result
        assert "leshamb2" in result
        print(f"\n👤 Current User:\n{result[:300]}...")

    async def test_get_user_profile(self, ctx, moodle_client):
        """Test getting user profile by ID."""
        user_id = moodle_client.current_user_id
        result = await moodle_get_user_profile(
            user_id=user_id,
            format="markdown",
            ctx=ctx
        )

        assert isinstance(result, str)
        assert "Elizabeth" in result or "Shamblin" in result
        print(f"\n👤 User Profile:\n{result[:300]}...")


@pytest.mark.asyncio
class TestGroupTools:
    """Test group tools with real API."""

    async def test_get_course_groups(self, ctx):
        """Test getting groups for course 7299."""
        result = await moodle_get_course_groups(
            course_id=7299,
            format="markdown",
            ctx=ctx
        )

        assert isinstance(result, str)
        assert len(result) > 0
        # Course might have no groups, so just check for valid response
        assert "group" in result.lower() or "no groups" in result.lower()
        print(f"\n👥 Course Groups:\n{result[:300]}...")


@pytest.mark.asyncio
class TestCompletionTools:
    """Test completion tracking tools with real API."""

    async def test_get_course_completion_status(self, ctx, moodle_client):
        """Test getting course completion status."""
        user_id = moodle_client.current_user_id
        result = await moodle_get_course_completion_status(
            course_id=7299,
            user_id=user_id,
            format="markdown",
            ctx=ctx
        )

        assert isinstance(result, str)
        assert len(result) > 0
        assert "completion" in result.lower() or "complete" in result.lower()
        print(f"\n✅ Course Completion:\n{result[:300]}...")

    async def test_get_activities_completion_status(self, ctx, moodle_client):
        """Test getting activities completion status."""
        user_id = moodle_client.current_user_id
        result = await moodle_get_activities_completion_status(
            course_id=7299,
            user_id=user_id,
            format="markdown",
            ctx=ctx
        )

        assert isinstance(result, str)
        assert len(result) > 0
        # Might have no activities or no completion data
        assert "activity" in result.lower() or "no activities" in result.lower() or "completion" in result.lower()
        print(f"\n📋 Activities Completion:\n{result[:300]}...")


@pytest.mark.asyncio
class TestBadgeTools:
    """Test badge tools with real API."""

    async def test_get_user_badges(self, ctx, moodle_client):
        """Test getting user badges."""
        user_id = moodle_client.current_user_id
        result = await moodle_get_user_badges(
            user_id=user_id,
            course_id=0,
            page=0,
            per_page=0,
            search="",
            only_public=False,
            format="markdown",
            ctx=ctx
        )

        assert isinstance(result, str)
        assert len(result) > 0
        # User might have no badges
        assert "badge" in result.lower() or "no badges" in result.lower()
        print(f"\n🏆 User Badges:\n{result[:300]}...")


@pytest.mark.asyncio
class TestAllToolsBasic:
    """Test that all basic tools can be called without errors."""

    async def test_all_no_param_tools(self, ctx):
        """Test all tools that don't require parameters."""

        tools_to_test = [
            ("Site Info", lambda: moodle_get_site_info(format="markdown", ctx=ctx)),
            ("Test Connection", lambda: moodle_test_connection(ctx=ctx)),
            ("List Courses", lambda: moodle_list_user_courses(user_id=None, format="markdown", ctx=ctx)),
            ("Current User", lambda: moodle_get_current_user(format="markdown", ctx=ctx)),
        ]

        results = []
        for name, tool_func in tools_to_test:
            try:
                result = await tool_func()
                assert isinstance(result, str)
                assert len(result) > 0
                results.append(f"✅ {name}")
            except Exception as e:
                results.append(f"❌ {name}: {e}")

        print("\n" + "\n".join(results))

        # All tools should pass
        failed = [r for r in results if r.startswith("❌")]
        assert len(failed) == 0, f"Some tools failed: {failed}"


@pytest.mark.asyncio
class TestDebugJustinCase:
    """Debug test for adding Justin Case to Group 1."""

    async def test_debug_add_justin_to_group1(self, ctx, moodle_client):
        """Debug adding Justin Case to Group 1 in course 7299."""
        print("\n" + "=" * 70)
        print("DEBUGGING: Adding Justin Case to Group 1 in Course 7299")
        print("=" * 70)

        # Step 1: Get course participants
        print("\n1. Getting course participants from course 7299...")
        try:
            participants_json = await moodle_get_course_participants(
                course_id=7299, limit=100, offset=0, format='json', ctx=ctx
            )
            data = json.loads(participants_json)

            print(f"   Found {data.get('total', 0)} total participants")
            print(f"   Showing {data.get('showing', 0)} participants\n")

            # Find Justin Case
            justin = None
            for p in data.get('participants', []):
                fullname = p.get('fullname', '')
                if 'justin' in fullname.lower() and 'case' in fullname.lower():
                    justin = p
                    print(f"   ✅ Found Justin Case:")
                    print(f"      ID: {justin.get('id')}")
                    print(f"      Full Name: {justin.get('fullname')}")
                    print(f"      Email: {justin.get('email', 'N/A')}")
                    break

            if not justin:
                print(f"   ⚠️  Justin Case not found. Here are the first 10 participants:")
                for p in data.get('participants', [])[:10]:
                    print(f"      - {p.get('fullname')} (ID: {p.get('id')})")
                justin_id = None
            else:
                justin_id = justin.get('id')
        except Exception as e:
            print(f"   ❌ Error: {e}")
            justin_id = None

        # Step 2: Get groups
        print("\n2. Getting groups in course 7299...")
        try:
            groups_json = await moodle_get_course_groups(course_id=7299, format='json', ctx=ctx)
            groups = json.loads(groups_json)

            print(f"   Found {len(groups)} groups:")
            group1 = None
            for g in groups:
                name = g.get('name', '')
                print(f"      - {name} (ID: {g.get('id')})")
                if 'group 1' in name.lower():
                    group1 = g

            if group1:
                print(f"\n   ✅ Found target group:")
                print(f"      ID: {group1.get('id')}")
                print(f"      Name: {group1.get('name')}")
                group1_id = group1.get('id')
            else:
                print(f"\n   ⚠️  'Group 1' not found in groups")
                group1_id = None
        except Exception as e:
            print(f"   ❌ Error: {e}")
            group1_id = None

        # Step 3: Try to add user to group
        if justin_id and group1_id:
            print(f"\n3. Attempting to add Justin Case (ID: {justin_id}) to Group 1 (ID: {group1_id})...")
            try:
                result = await moodle_add_group_members(
                    course_id=7299,
                    group_id=group1_id,
                    user_ids=[justin_id],
                    format='markdown',
                    ctx=ctx
                )
                print(f"   ✅ SUCCESS! Result:\n")
                print(result)
            except Exception as e:
                import traceback
                print(f"   ❌ ERROR adding user to group:")
                print(f"      Error Type: {type(e).__name__}")
                print(f"      Error Message: {str(e)}")
                print(f"\n   Full Traceback:")
                print("      " + "\n      ".join(traceback.format_exc().split("\n")))
                print(f"\n   Possible reasons:")
                print(f"      1. User is already in the group")
                print(f"      2. Insufficient permissions")
                print(f"      3. Group or user doesn't exist in this course")
                print(f"      4. API configuration issue")
        else:
            print(f"\n3. ❌ Cannot proceed:")
            print(f"      Justin Case ID: {justin_id}")
            print(f"      Group 1 ID: {group1_id}")

        print("\n" + "=" * 70)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
