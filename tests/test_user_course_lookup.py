"""
Unit tests for user course lookup functionality.

Tests the workflow: Search user by name → Get user's courses

Run with:
    PYTHONPATH=src pytest tests/test_user_course_lookup.py -v
    PYTHONPATH=src pytest tests/test_user_course_lookup.py::TestUserCourseLookup::test_lookup_andy_click -v -s
"""

import pytest
import json
from moodle_mcp.core.client import MoodleAPIClient
from moodle_mcp.core.config import get_config
from moodle_mcp.tools.users import moodle_search_users
from moodle_mcp.tools.courses import moodle_list_user_courses
from moodle_mcp.models.base import ResponseFormat


def unwrap_tool(tool):
    """Unwrap a FunctionTool to get the underlying function."""
    return tool.fn if hasattr(tool, 'fn') else tool


# Unwrap tools
moodle_search_users = unwrap_tool(moodle_search_users)
moodle_list_user_courses = unwrap_tool(moodle_list_user_courses)


class MockContext:
    """Mock FastMCP Context for testing."""

    def __init__(self, moodle_client: MoodleAPIClient):
        self.request_context = MockRequestContext(moodle_client)


class MockRequestContext:
    """Mock request context with lifespan_context."""

    def __init__(self, moodle_client: MoodleAPIClient):
        self.lifespan_context = {
            "moodle_client": moodle_client
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
    """Create a mock context for each test."""
    return MockContext(moodle_client)


@pytest.mark.asyncio
class TestUserCourseLookup:
    """Test the complete user course lookup workflow."""

    async def test_lookup_andy_click(self, ctx):
        """
        Test looking up courses for Andy Click.

        This is the complete workflow:
        1. Search for "Andy Click" by name
        2. Extract user_id from results
        3. Get all courses for that user_id
        """
        search_query = "Andy Click"

        print(f"\n{'='*70}")
        print(f"TESTING: User Course Lookup for '{search_query}'")
        print(f"{'='*70}\n")

        # Step 1: Search for user
        print(f"Step 1: Searching for user '{search_query}'...")
        user_results = await moodle_search_users(
            search_query=search_query,
            limit=5,
            format=ResponseFormat.JSON,
            ctx=ctx
        )

        # Verify we got a result
        assert isinstance(user_results, str), "Search results should be a string"
        print(f"✓ Search completed")

        # Parse JSON results
        try:
            user_data = json.loads(user_results)
        except json.JSONDecodeError as e:
            pytest.fail(f"Failed to parse search results as JSON: {e}\nGot: {user_results}")

        # Check if we found users
        if not user_data or len(user_data) == 0:
            pytest.skip(f"No users found matching '{search_query}' - test environment may not have this user")

        print(f"✓ Found {len(user_data)} user(s)\n")

        # Display found users
        for i, user in enumerate(user_data, 1):
            print(f"  {i}. {user.get('fullname', 'Unknown')} (ID: {user.get('id')})")
            if user.get('email'):
                print(f"     Email: {user.get('email')}")
            if user.get('username'):
                print(f"     Username: {user.get('username')}")
            print()

        # Step 2: Get courses for first matching user
        selected_user = user_data[0]
        user_id = selected_user.get('id')
        user_fullname = selected_user.get('fullname', 'Unknown')

        assert user_id is not None, "User should have an ID"
        print(f"Step 2: Getting courses for {user_fullname} (ID: {user_id})...\n")

        # Get courses in Markdown format for human-readable output
        courses_markdown = await moodle_list_user_courses(
            user_id=user_id,
            include_hidden=False,
            format=ResponseFormat.MARKDOWN,
            ctx=ctx
        )

        assert isinstance(courses_markdown, str), "Courses result should be a string"
        print(f"✓ Courses retrieved (Markdown)\n")
        print(f"{'='*70}")
        print(courses_markdown)
        print(f"{'='*70}\n")

        # Also get in JSON format for programmatic validation
        courses_json = await moodle_list_user_courses(
            user_id=user_id,
            include_hidden=False,
            format=ResponseFormat.JSON,
            ctx=ctx
        )

        # Parse and validate JSON
        try:
            courses_data = json.loads(courses_json)
        except json.JSONDecodeError as e:
            pytest.fail(f"Failed to parse courses as JSON: {e}\nGot: {courses_json}")

        print(f"✓ Courses retrieved (JSON)")
        print(f"  Total courses: {courses_data.get('count', 'unknown')}\n")

        # Validate structure
        assert 'courses' in courses_data or 'count' in courses_data, \
            "JSON should contain 'courses' or 'count' field"

    async def test_search_user_variations(self, ctx):
        """Test different search variations for finding users."""
        test_queries = [
            "Andy",
            "Click",
            "Andy Click",
        ]

        print(f"\n{'='*70}")
        print("TESTING: Search User Variations")
        print(f"{'='*70}\n")

        for query in test_queries:
            print(f"Testing search query: '{query}'")

            result = await moodle_search_users(
                search_query=query,
                limit=3,
                format=ResponseFormat.JSON,
                ctx=ctx
            )

            assert isinstance(result, str), f"Search for '{query}' should return string"

            try:
                data = json.loads(result)
                print(f"  ✓ Found {len(data) if data else 0} user(s)")
            except json.JSONDecodeError:
                print(f"  ✗ Invalid JSON response")

            print()

    async def test_invalid_user_search(self, ctx):
        """Test searching for a non-existent user."""
        print(f"\n{'='*70}")
        print("TESTING: Invalid User Search")
        print(f"{'='*70}\n")

        # Search for a user that definitely doesn't exist
        result = await moodle_search_users(
            search_query="ThisUserDefinitelyDoesNotExist12345",
            limit=5,
            format=ResponseFormat.MARKDOWN,
            ctx=ctx
        )

        print(f"Search result:\n{result}\n")

        # Should return a message about no users found
        assert isinstance(result, str)
        assert "no" in result.lower() or "not found" in result.lower()

    async def test_get_courses_for_current_user(self, ctx, moodle_client):
        """Test getting courses for the currently authenticated user."""
        print(f"\n{'='*70}")
        print("TESTING: Current User Courses")
        print(f"{'='*70}\n")

        user_id = moodle_client.current_user_id
        print(f"Current user ID: {user_id}\n")

        # Get courses without specifying user_id (should default to current user)
        result = await moodle_list_user_courses(
            user_id=None,  # Should use current user
            include_hidden=False,
            format=ResponseFormat.MARKDOWN,
            ctx=ctx
        )

        print(result)
        print()

        assert isinstance(result, str)
        assert "course" in result.lower() or "enrolled" in result.lower() or "no courses" in result.lower()

    async def test_include_hidden_courses(self, ctx, moodle_client):
        """Test including hidden courses in results."""
        print(f"\n{'='*70}")
        print("TESTING: Include Hidden Courses")
        print(f"{'='*70}\n")

        user_id = moodle_client.current_user_id

        # Get visible courses only
        visible_result = await moodle_list_user_courses(
            user_id=user_id,
            include_hidden=False,
            format=ResponseFormat.JSON,
            ctx=ctx
        )

        # Get all courses (including hidden)
        all_result = await moodle_list_user_courses(
            user_id=user_id,
            include_hidden=True,
            format=ResponseFormat.JSON,
            ctx=ctx
        )

        visible_data = json.loads(visible_result)
        all_data = json.loads(all_result)

        visible_count = visible_data.get('count', 0)
        all_count = all_data.get('count', 0)

        print(f"Visible courses: {visible_count}")
        print(f"All courses (including hidden): {all_count}")
        print(f"Hidden courses: {all_count - visible_count}\n")

        # All courses should be >= visible courses
        assert all_count >= visible_count, \
            "All courses count should be >= visible courses count"


@pytest.mark.asyncio
class TestUserCourseLookupEdgeCases:
    """Test edge cases and error handling."""

    async def test_short_search_query(self, ctx):
        """Test that search requires minimum 2 characters."""
        # This should fail validation (min_length=2)
        with pytest.raises(Exception):
            await moodle_search_users(
                search_query="A",  # Only 1 character
                limit=5,
                format=ResponseFormat.MARKDOWN,
                ctx=ctx
            )

    async def test_invalid_user_id(self, ctx):
        """Test getting courses for non-existent user ID."""
        # Try to get courses for a user ID that likely doesn't exist
        result = await moodle_list_user_courses(
            user_id=999999,
            include_hidden=False,
            format=ResponseFormat.MARKDOWN,
            ctx=ctx
        )

        # Should return an error message or empty result
        assert isinstance(result, str)
        # May return empty or error depending on Moodle's behavior

    async def test_json_vs_markdown_format(self, ctx, moodle_client):
        """Test that both JSON and Markdown formats work correctly."""
        user_id = moodle_client.current_user_id

        # Get in Markdown
        markdown_result = await moodle_list_user_courses(
            user_id=user_id,
            include_hidden=False,
            format=ResponseFormat.MARKDOWN,
            ctx=ctx
        )

        # Get in JSON
        json_result = await moodle_list_user_courses(
            user_id=user_id,
            include_hidden=False,
            format=ResponseFormat.JSON,
            ctx=ctx
        )

        assert isinstance(markdown_result, str)
        assert isinstance(json_result, str)

        # JSON should be parseable
        json_data = json.loads(json_result)
        assert isinstance(json_data, dict)

        # Markdown should have headers or course text
        assert "#" in markdown_result or "course" in markdown_result.lower() or "no" in markdown_result.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
