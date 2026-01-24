"""
Demonstration of dynamic tool discovery for testing.

This test file shows how to use the new dynamic discovery system
instead of manually importing and unwrapping every tool.

BEFORE (100+ lines of imports/unwrapping):
    from moodle_mcp.tools.site import moodle_get_site_info
    moodle_get_site_info = unwrap_tool(moodle_get_site_info)
    from moodle_mcp.tools.courses import moodle_list_user_courses
    moodle_list_user_courses = unwrap_tool(moodle_list_user_courses)
    ... (repeat 40+ times)

AFTER (automatic discovery):
    def test_something(all_tools, ctx):
        get_site_info = all_tools['moodle_get_site_info']
        result = await get_site_info(ctx=ctx)
"""

import pytest


@pytest.mark.asyncio
class TestDynamicDiscovery:
    """Demonstrate dynamic tool discovery."""

    async def test_all_tools_fixture_available(self, all_tools):
        """Test that the all_tools fixture discovers tools."""
        assert isinstance(all_tools, dict)
        assert len(all_tools) > 0, "Should discover at least some tools"

        # Should include site tools
        assert 'moodle_get_site_info' in all_tools
        assert 'moodle_test_connection' in all_tools

        # Should include course tools
        assert 'moodle_list_user_courses' in all_tools
        assert 'moodle_get_course_details' in all_tools

        # All tools should be callable
        for tool_name, tool_fn in all_tools.items():
            assert callable(tool_fn), f"{tool_name} should be callable"

    async def test_use_discovered_tool_site_info(self, all_tools, ctx):
        """Test using a discovered tool - site info."""
        # Get tool by name from discovery
        get_site_info = all_tools['moodle_get_site_info']

        # Use it like any other function
        result = await get_site_info(format="markdown", ctx=ctx)

        assert isinstance(result, str)
        assert "Moodle Site Information" in result or "Site" in result

    async def test_use_discovered_tool_test_connection(self, all_tools, ctx):
        """Test using a discovered tool - test connection."""
        test_connection = all_tools['moodle_test_connection']

        result = await test_connection(ctx=ctx)

        assert isinstance(result, str)
        assert "✓" in result or "Success" in result.lower()

    async def test_use_discovered_tool_list_courses(self, all_tools, ctx):
        """Test using a discovered tool - list courses."""
        list_courses = all_tools['moodle_list_user_courses']

        # Call without user_id (uses current user)
        result = await list_courses(format="json", ctx=ctx)

        assert isinstance(result, str)
        # Should be valid JSON or error message
        assert "{" in result or "No courses" in result

    async def test_tool_count(self, all_tools):
        """Verify we discover the expected number of tools."""
        # As of this implementation, we should have 40+ tools
        # This test will catch if tools are accidentally removed
        assert len(all_tools) >= 40, f"Expected 40+ tools, found {len(all_tools)}"

        # Print discovered tools for debugging
        print(f"\n\nDiscovered {len(all_tools)} tools:")
        for tool_name in sorted(all_tools.keys()):
            print(f"  - {tool_name}")


@pytest.mark.asyncio
class TestCategoryDiscovery:
    """Test tool categorization helper."""

    async def test_get_tools_by_category(self):
        """Test that tools can be categorized."""
        from .test_helpers import get_tools_by_category
        from moodle_mcp.server import mcp

        categories = get_tools_by_category(mcp)

        assert isinstance(categories, dict)
        assert len(categories) > 0

        # Should have major categories
        assert 'site' in categories
        assert 'courses' in categories
        assert 'users' in categories

        # Each category should have tools
        for category, tools in categories.items():
            assert isinstance(tools, list)
            assert len(tools) > 0, f"Category {category} should have tools"

        # Print categories for debugging
        print("\n\nTool Categories:")
        for category, tools in sorted(categories.items()):
            print(f"\n  {category.upper()} ({len(tools)} tools):")
            for tool in sorted(tools):
                print(f"    - {tool}")


@pytest.mark.asyncio
class TestMockContext:
    """Test the MockContext helper."""

    async def test_mock_context_structure(self, moodle_client):
        """Test that MockContext has the right structure."""
        from .test_helpers import MockContext

        ctx = MockContext(moodle_client)

        # Should have request_context
        assert hasattr(ctx, 'request_context')

        # request_context should have lifespan_context
        assert hasattr(ctx.request_context, 'lifespan_context')

        # lifespan_context should have moodle_client and config
        lifespan = ctx.request_context.lifespan_context
        assert 'moodle_client' in lifespan
        assert 'config' in lifespan

        # moodle_client should be the same instance
        assert lifespan['moodle_client'] is moodle_client

    async def test_ctx_fixture_works(self, ctx):
        """Test that the ctx fixture from conftest works."""
        # Should have the structure needed by tools
        assert hasattr(ctx, 'request_context')
        assert hasattr(ctx.request_context, 'lifespan_context')

        lifespan = ctx.request_context.lifespan_context
        assert 'moodle_client' in lifespan
        assert 'config' in lifespan
