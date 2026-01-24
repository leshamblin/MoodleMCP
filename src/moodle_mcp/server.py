"""
Central FastMCP server instance.

This module exports the main MCP server instance that all tools and resources
register with. The actual instance is created in main.py with lifespan context.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

# This will be set by main.py
mcp: "FastMCP" = None  # type: ignore

# Export for use in other modules
__all__ = ["mcp"]
