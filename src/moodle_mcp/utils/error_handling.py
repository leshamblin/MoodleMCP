"""
Error handling utilities and decorators for consistent error messages.
"""

from functools import wraps
from typing import Callable, Any
from fastmcp import Context
from fastmcp.exceptions import ToolError
from ..core.exceptions import (
    MoodleAPIError,
    MoodleAuthError,
    MoodleConnectionError,
    MoodleNotFoundError,
    MoodlePermissionError,
    MoodleValidationError
)


class WriteOperationError(MoodlePermissionError):
    """Raised when a write operation is attempted on a non-whitelisted course."""
    pass

def handle_moodle_errors(func: Callable) -> Callable:
    """
    Decorator to handle Moodle-specific errors and convert to ToolError.

    Ensures user-friendly, actionable error messages reach the LLM client.
    All errors are converted to ToolError for proper MCP protocol handling.

    Usage:
        @mcp.tool()
        @handle_moodle_errors
        async def my_tool(...):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)
        except MoodleAuthError as e:
            # Authentication errors are critical - provide clear guidance
            raise ToolError(
                f"Authentication failed: {e}\n\n"
                "Please verify:\n"
                "1. MOODLE_TOKEN is correct and not expired\n"
                "2. Token has required web service permissions\n"
                "3. Web services are enabled on the Moodle site"
            )
        except MoodlePermissionError as e:
            # Permission denied - guide user on access requirements
            raise ToolError(
                f"Permission denied: {e}\n\n"
                "The current user lacks permission for this operation. "
                "Try using a different account or contact your Moodle administrator."
            )
        except MoodleNotFoundError as e:
            # Resource not found - suggest checking IDs
            raise ToolError(
                f"Not found: {e}\n\n"
                "Please verify the ID is correct and the resource exists."
            )
        except MoodleConnectionError as e:
            # Connection issues - suggest checking URL and network
            raise ToolError(
                f"Connection error: {e}\n\n"
                "Please verify:\n"
                "1. MOODLE_URL is correct and accessible\n"
                "2. Network connection is stable\n"
                "3. Moodle site is online"
            )
        except MoodleValidationError as e:
            # Input validation errors
            raise ToolError(f"Invalid input: {e}")
        except MoodleAPIError as e:
            # General Moodle API errors
            raise ToolError(f"Moodle API error: {e}")
        except ValueError as e:
            # Validation errors from Pydantic or other sources
            raise ToolError(f"Validation error: {e}")
        except Exception as e:
            # Unexpected errors - provide generic message
            # Check if we're in development mode to include debug info
            ctx: Context | None = kwargs.get('ctx')
            is_dev = True  # Default to dev if config unavailable

            if ctx is not None:
                try:
                    config = ctx.request_context.lifespan_context.get('config')
                    if config is not None:
                        is_dev = config.is_development()
                except:
                    pass  # Keep default if config access fails

            # In DEV: include exception type for debugging
            # In PROD: strip debug info for security
            if is_dev:
                error_msg = f"An unexpected error occurred: {type(e).__name__}\n\n"
            else:
                error_msg = "An unexpected error occurred.\n\n"

            raise ToolError(
                error_msg + "Please try again or contact the administrator if the issue persists."
            )

    return wrapper


def require_write_permission(course_id_param: str = 'course_id'):
    """
    Decorator to enforce write operation safety rules.

    SAFETY: Blocks write operations unless:
    - DEV mode AND course is in whitelist (default: [7299])
    - PROD mode AND prod_allow_writes=True (default: False)

    Usage:
        @mcp.tool()
        @handle_moodle_errors
        @require_write_permission('course_id')
        async def my_write_tool(course_id: int, ctx: Context = None):
            # This will only execute if course_id is allowed
            ...

    Args:
        course_id_param: Name of the parameter containing the course_id

    Raises:
        WriteOperationError: If write is not allowed for this course
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Extract course_id from kwargs
            course_id = kwargs.get(course_id_param)

            if course_id is None:
                raise WriteOperationError(
                    f"Write operation requires '{course_id_param}' parameter"
                )

            # Get config from context
            ctx: Context | None = kwargs.get('ctx')
            if ctx is None:
                raise WriteOperationError(
                    "Write operation requires Context (ctx parameter)"
                )

            config = ctx.request_context.lifespan_context.get('config')
            if config is None:
                raise WriteOperationError(
                    "Configuration not available in context"
                )

            # Check if write is allowed
            if not config.can_write_to_course(course_id):
                restriction_msg = config.get_write_restriction_message(course_id)
                raise WriteOperationError(
                    f"Write operation blocked for safety:\n\n{restriction_msg}"
                )

            # Write is allowed - proceed with function
            return await func(*args, **kwargs)

        return wrapper
    return decorator
