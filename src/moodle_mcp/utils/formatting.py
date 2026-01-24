"""
Response formatting utilities for JSON and Markdown output.
"""

import json
from typing import Any
from datetime import datetime
from pydantic import BaseModel

def format_as_json(data: Any, pretty: bool = True) -> str:
    """
    Format data as JSON string.

    Handles Pydantic models, lists, and nested structures.

    Args:
        data: Data to format (Pydantic model, list, dict, etc.)
        pretty: Whether to pretty-print with indentation

    Returns:
        JSON-formatted string
    """
    if isinstance(data, BaseModel):
        json_data = data.model_dump(mode='json')
    elif isinstance(data, list):
        if len(data) > 0 and isinstance(data[0], BaseModel):
            json_data = [item.model_dump(mode='json') for item in data]
        else:
            json_data = data
    else:
        json_data = data

    indent = 2 if pretty else None
    return json.dumps(json_data, indent=indent, default=str, ensure_ascii=False)

def format_as_markdown(
    data: Any,
    title: str | None = None,
    include_count: bool = True
) -> str:
    """
    Format data as Markdown for better LLM readability.

    Markdown is ~15% more token-efficient than JSON and more human-readable.

    Args:
        data: Data to format (Pydantic model, list, dict, etc.)
        title: Optional title for the markdown document
        include_count: Whether to include item count for lists

    Returns:
        Markdown-formatted string
    """
    lines = []

    if title:
        lines.append(f"# {title}\n")

    if isinstance(data, list):
        if include_count:
            lines.append(f"**Total items:** {len(data)}\n")

        if len(data) == 0:
            lines.append("*No items found*\n")
        else:
            for i, item in enumerate(data, 1):
                if isinstance(item, BaseModel):
                    # Format Pydantic model
                    item_dict = item.model_dump()
                    item_name = _get_display_name(item_dict)
                    lines.append(f"## {i}. {item_name}")
                    lines.extend(_format_dict_fields(item_dict))
                    lines.append("")
                elif isinstance(item, dict):
                    # Format plain dict
                    item_name = _get_display_name(item)
                    lines.append(f"## {i}. {item_name}")
                    lines.extend(_format_dict_fields(item))
                    lines.append("")
                else:
                    # Simple value
                    lines.append(f"{i}. {item}")

    elif isinstance(data, BaseModel):
        item_dict = data.model_dump()
        lines.extend(_format_dict_fields(item_dict))

    elif isinstance(data, dict):
        lines.extend(_format_dict_fields(data))

    else:
        # Simple value
        lines.append(str(data))

    return "\n".join(lines)

def _get_display_name(item_dict: dict[str, Any]) -> str:
    """Extract a display name from dict, preferring fullname > name > id."""
    if 'fullname' in item_dict:
        return item_dict['fullname']
    elif 'name' in item_dict:
        return item_dict['name']
    elif 'title' in item_dict:
        return item_dict['title']
    elif 'id' in item_dict:
        return f"Item {item_dict['id']}"
    else:
        return "Item"

def _format_dict_fields(data: dict[str, Any]) -> list[str]:
    """Format dictionary fields as markdown bullet points."""
    lines = []

    for field, value in data.items():
        if value is None or value == '' or value == []:
            continue  # Skip empty values

        # Format field name
        field_name = field.replace('_', ' ').title()

        # Format value based on type
        if isinstance(value, bool):
            formatted_value = "✓" if value else "✗"
        elif isinstance(value, (list, tuple)):
            if len(value) == 0:
                continue  # Skip empty lists
            elif len(value) <= 5:
                # Small lists - inline
                formatted_value = ", ".join(str(v) for v in value)
            else:
                # Large lists - count only
                formatted_value = f"{len(value)} items"
        elif isinstance(value, dict):
            # Nested dict - format as sub-items
            formatted_value = _format_nested_dict(value)
        elif isinstance(value, int) and field in ['startdate', 'enddate', 'timestart', 'timemodified', 'timecreated', 'lastaccess', 'firstaccess']:
            # Format timestamps as human-readable dates
            if value > 0:
                formatted_value = datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S UTC')
            else:
                continue  # Skip zero timestamps
        else:
            formatted_value = str(value)

        lines.append(f"- **{field_name}:** {formatted_value}")

    return lines

def _format_nested_dict(data: dict[str, Any]) -> str:
    """Format nested dictionary inline."""
    items = []
    for k, v in data.items():
        if v is not None and v != '' and v != []:
            items.append(f"{k}: {v}")
    return "; ".join(items) if items else "N/A"

def truncate_response(content: str, max_chars: int = 50000) -> str:
    """
    Truncate response if it exceeds character limit.

    Adds clear truncation notice to help LLM understand data was cut off.

    Args:
        content: Response content to check/truncate
        max_chars: Maximum allowed characters

    Returns:
        Potentially truncated content with notice
    """
    if len(content) <= max_chars:
        return content

    # Truncate at max_chars
    truncated = content[:max_chars]

    # Try to truncate at a newline for cleaner break
    last_newline = truncated.rfind('\n', max_chars - 500, max_chars)
    if last_newline > 0:
        truncated = truncated[:last_newline]

    # Add truncation notice
    notice = (
        f"\n\n---\n\n"
        f"⚠ **Response truncated at {len(truncated):,} characters** "
        f"(original: {len(content):,} characters)\n\n"
        f"To see more results:\n"
        f"- Use pagination parameters (limit, offset, or cursor)\n"
        f"- Add filters to narrow down results\n"
        f"- Request specific items by ID"
    )

    return truncated + notice

def format_response(
    data: Any,
    title: str | None = None,
    format_type: "ResponseFormat" = None
) -> str:
    """
    Format data based on format type.

    This helper eliminates the repeated pattern of checking format type
    and calling format_as_json or format_as_markdown.

    Args:
        data: Data to format (dict, list, or Pydantic model)
        title: Optional title for markdown format
        format_type: Output format (markdown or json)

    Returns:
        Formatted response string

    Example:
        # Before (repeated 30+ times across codebase):
        if format == ResponseFormat.JSON:
            result = format_as_json(data)
        else:
            result = format_as_markdown(data, title)
        return result

        # After (1 line):
        return format_response(data, title, format)
    """
    from ..models.base import ResponseFormat

    # Default to markdown if not specified
    if format_type is None:
        format_type = ResponseFormat.MARKDOWN

    if format_type == ResponseFormat.JSON:
        return format_as_json(data)
    else:
        return format_as_markdown(data, title)
