"""
Additional API helper utilities.

Most API functionality is in core/client.py. This module provides
higher-level helpers for common patterns.
"""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import Context
    from ..core.client import MoodleAPIClient

def get_moodle_client(ctx: "Context") -> "MoodleAPIClient":
    """
    Get MoodleAPIClient from FastMCP context.

    According to FastMCP docs, lifespan context is accessed via:
    ctx.request_context.lifespan_context

    Args:
        ctx: FastMCP context

    Returns:
        MoodleAPIClient instance

    Raises:
        RuntimeError: If moodle_client cannot be found in context
    """
    if ctx is None:
        raise RuntimeError("Context is None - ensure tool is called with ctx parameter")

    request_ctx = ctx.request_context

    if request_ctx is None:
        raise RuntimeError("request_context is None - server lifespan may not be initialized")

    # FastMCP stores lifespan yield dict in lifespan_context attribute
    if hasattr(request_ctx, 'lifespan_context'):
        lifespan_ctx = request_ctx.lifespan_context

        # Try dictionary access (this is the yield dict from lifespan)
        if isinstance(lifespan_ctx, dict):
            client = lifespan_ctx.get("moodle_client")
            if client is None:
                raise RuntimeError(f"moodle_client not found in lifespan_context. Keys: {list(lifespan_ctx.keys())}")
            return client

        # Try attribute access
        if hasattr(lifespan_ctx, 'moodle_client'):
            return lifespan_ctx.moodle_client

    # Fallback: try direct access (older FastMCP versions or different transport)
    if isinstance(request_ctx, dict):
        client = request_ctx.get("moodle_client")
        if client:
            return client

    if hasattr(request_ctx, 'moodle_client'):
        return request_ctx.moodle_client

    raise RuntimeError(
        f"Cannot find moodle_client in context. "
        f"request_context type: {type(request_ctx).__name__}, "
        f"has lifespan_context: {hasattr(request_ctx, 'lifespan_context')}"
    )

async def resolve_user_id(
    moodle: "MoodleAPIClient",
    user_id: int | None = None
) -> int:
    """
    Resolve user ID to current user if not provided.

    This helper eliminates the repeated pattern of checking if user_id is None
    and fetching the current user's ID from site info.

    Args:
        moodle: Moodle API client instance
        user_id: Optional user ID (if None, fetches current user)

    Returns:
        Resolved user ID

    Example:
        # Before (repeated 10+ times across codebase):
        if user_id is None:
            site_info = await moodle.get_site_info()
            user_id = site_info['userid']

        # After (1 line):
        user_id = await resolve_user_id(moodle, user_id)
    """
    if user_id is None:
        site_info = await moodle.get_site_info()
        return site_info['userid']
    return user_id
