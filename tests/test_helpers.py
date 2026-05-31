"""
Test helper utilities for dynamic tool discovery and testing.

This module eliminates the need to manually import and unwrap each tool,
automatically discovering all registered tools from the MCP instance.
"""

from typing import Any, Callable
from fastmcp import Context
from moodle_mcp.core.client import MoodleAPIClient
from moodle_mcp.core.config import get_config


def unwrap_tool(tool: Any) -> Callable:
    """
    Unwrap a FunctionTool to get the underlying function.

    Args:
        tool: A FunctionTool or regular function

    Returns:
        The underlying callable function
    """
    return tool.fn if hasattr(tool, 'fn') else tool


def discover_tools(mcp_instance) -> dict[str, Callable]:
    """
    Dynamically discover all tools from the MCP instance.

    This eliminates the need to manually import and list every tool.
    Tools are automatically unwrapped and returned in a dictionary.

    Args:
        mcp_instance: The FastMCP server instance with registered tools

    Returns:
        Dictionary mapping tool names to unwrapped callables

    Example:
        >>> from moodle_mcp.server import mcp
        >>> tools = discover_tools(mcp)
        >>> assert 'moodle_get_site_info' in tools
        >>> assert callable(tools['moodle_get_site_info'])
    """
    tools = {}

    # FastMCP 3.x: list_tools() is an async coroutine returning a list of
    # FunctionTool. discover_tools is a sync helper that may be called either
    # outside any event loop (asyncio.run) or from within pytest-asyncio's
    # running loop (asyncio.run would raise) -- run it on a worker thread in
    # the latter case so it always gets a clean loop.
    list_tools = getattr(mcp_instance, 'list_tools', None)
    if callable(list_tools):
        tool_objs = _run_coroutine_sync(list_tools())
        for tool_obj in tool_objs:
            tools[tool_obj.name] = unwrap_tool(tool_obj)
        return tools

    # Fallback: older FastMCP stored tools in _tool_manager._tools
    if hasattr(mcp_instance, '_tool_manager') and hasattr(mcp_instance._tool_manager, '_tools'):
        for tool_name, tool_obj in mcp_instance._tool_manager._tools.items():
            tools[tool_name] = unwrap_tool(tool_obj)

    return tools


def _run_coroutine_sync(coro):
    """
    Run a coroutine to completion from synchronous code, whether or not an
    event loop is already running in the current thread.
    """
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop: safe to use asyncio.run directly.
        return asyncio.run(coro)

    # A loop is already running in this thread (e.g. pytest-asyncio). Run the
    # coroutine on a separate thread with its own loop.
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(asyncio.run, coro).result()


def get_tool_by_name(mcp_instance, tool_name: str) -> Callable | None:
    """
    Get a specific tool by name from the MCP instance.

    Args:
        mcp_instance: The FastMCP server instance
        tool_name: Name of the tool (e.g., 'moodle_get_site_info')

    Returns:
        The unwrapped tool function, or None if not found
    """
    tools = discover_tools(mcp_instance)
    return tools.get(tool_name)


def get_tools_by_category(mcp_instance) -> dict[str, list[str]]:
    """
    Categorize tools by their module (e.g., site, courses, users).

    Args:
        mcp_instance: The FastMCP server instance

    Returns:
        Dictionary mapping categories to lists of tool names

    Example:
        >>> categories = get_tools_by_category(mcp)
        >>> assert 'site' in categories
        >>> assert 'moodle_get_site_info' in categories['site']
    """
    categories = {}

    for tool_name in discover_tools(mcp_instance).keys():
        if True:
            # Extract category from tool name (e.g., 'moodle_get_site_info' -> 'site')
            if tool_name.startswith('moodle_'):
                # Extract the second part after 'moodle_'
                parts = tool_name.split('_')
                if len(parts) >= 3:
                    # Try to determine category
                    # moodle_get_site_info -> site
                    # moodle_list_user_courses -> courses (heuristic)

                    # Check for known category keywords
                    tool_lower = tool_name.lower()
                    if 'site' in tool_lower or 'connection' in tool_lower or 'function' in tool_lower:
                        category = 'site'
                    elif 'course' in tool_lower:
                        category = 'courses'
                    elif 'user' in tool_lower or 'participant' in tool_lower:
                        category = 'users'
                    elif 'grade' in tool_lower:
                        category = 'grades'
                    elif 'assignment' in tool_lower:
                        category = 'assignments'
                    elif 'message' in tool_lower or 'conversation' in tool_lower:
                        category = 'messages'
                    elif 'calendar' in tool_lower or 'event' in tool_lower:
                        category = 'calendar'
                    elif 'forum' in tool_lower or 'discussion' in tool_lower:
                        category = 'forums'
                    elif 'group' in tool_lower:
                        category = 'groups'
                    elif 'enrol' in tool_lower:
                        category = 'enrollment'
                    elif 'quiz' in tool_lower:
                        category = 'quiz'
                    elif 'completion' in tool_lower or 'progress' in tool_lower:
                        category = 'completion'
                    elif 'badge' in tool_lower:
                        category = 'badges'
                    else:
                        category = 'other'

                    if category not in categories:
                        categories[category] = []
                    categories[category].append(tool_name)

    return categories


class MockContext:
    """
    Mock FastMCP Context for testing.

    This provides the same interface as the real Context but with
    a controllable lifespan_context for testing.
    """

    def __init__(self, moodle_client: MoodleAPIClient, config: Any = None):
        """
        Initialize mock context.

        Args:
            moodle_client: The Moodle API client instance
            config: Optional config override (defaults to get_config())
        """
        self.request_context = MockRequestContext(
            moodle_client,
            config or get_config()
        )


class MockRequestContext:
    """Mock request context with lifespan_context."""

    def __init__(self, moodle_client: MoodleAPIClient, config: Any):
        """
        Initialize mock request context.

        Args:
            moodle_client: The Moodle API client instance
            config: The configuration object
        """
        self.lifespan_context = {
            "moodle_client": moodle_client,
            "config": config
        }
