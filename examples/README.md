# Moodle MCP Server - Example Scripts

This directory contains standalone example scripts demonstrating common Moodle MCP operations.

## Available Examples

### 1. `lookup_user_courses.py` - Look Up User's Courses

Find all courses a user is enrolled in by searching for their name.

**Usage:**
```bash
# Basic usage - search by full name
python examples/lookup_user_courses.py "Andy Click"

# JSON output format
python examples/lookup_user_courses.py "Andy Click" --json

# Include hidden courses
python examples/lookup_user_courses.py "Andy Click" --include-hidden

# Search by partial name
python examples/lookup_user_courses.py "Andy"
```

**How it works:**
1. Searches for users matching the provided name
2. Displays all matching users with their IDs and emails
3. Gets all enrolled courses for the first matching user
4. Displays course details in Markdown or JSON format

**Requirements:**
- `.env` file configured with `MOODLE_DEV_URL` and `MOODLE_DEV_TOKEN`
- Valid Moodle Web Services token with user search permissions

## Running Examples

All examples can be run directly with Python:

```bash
# From project root
python examples/lookup_user_courses.py "User Name"
```

Or make them executable and run directly:

```bash
# Make executable (Unix/Mac)
chmod +x examples/lookup_user_courses.py

# Run directly
./examples/lookup_user_courses.py "User Name"
```

## Environment Configuration

Examples use the same `.env` configuration as the main MCP server:

```bash
# Development instance (default)
MOODLE_DEV_URL=https://moodle-dev.example.com
MOODLE_DEV_TOKEN=your_dev_token_here

# Production instance
MOODLE_PROD_URL=https://moodle.example.com
MOODLE_PROD_TOKEN=your_prod_token_here

# Select environment
MOODLE_ENV=dev  # or 'prod'
```

Switch environments:
```bash
MOODLE_ENV=prod python examples/lookup_user_courses.py "User Name"
```

## Creating New Examples

To create a new example script:

1. Create a new `.py` file in this directory
2. Import required tools from `moodle_mcp.tools.*`
3. Use the `MockContext` pattern for standalone execution
4. Add documentation and usage examples
5. Update this README

Example template:
```python
#!/usr/bin/env python3
"""
Example script: Description of what it does.

Usage:
    python examples/my_example.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from moodle_mcp.core.client import MoodleAPIClient
from moodle_mcp.core.config import get_config
# Import your tools here

# MockContext classes (copy from lookup_user_courses.py)

async def main():
    """Main async function."""
    # Your code here
    pass

if __name__ == "__main__":
    asyncio.run(main())
```

## Common Patterns

### Creating a Moodle Client

```python
from moodle_mcp.core.client import MoodleAPIClient
from moodle_mcp.core.config import get_config

config = get_config()
client = MoodleAPIClient(
    base_url=config.url,
    token=config.token,
    timeout=config.api_timeout,
    max_connections=config.max_connections,
    max_keepalive=config.max_keepalive_connections
)
```

### Using Tools with MockContext

```python
from moodle_mcp.tools.courses import moodle_list_user_courses

# Unwrap tool if needed
tool_func = moodle_list_user_courses.fn if hasattr(moodle_list_user_courses, 'fn') else moodle_list_user_courses

# Call the tool
result = await tool_func(
    user_id=123,
    format=ResponseFormat.MARKDOWN,
    ctx=ctx
)
```

### Cleanup

Always close the client when done:
```python
try:
    # Your code here
    pass
finally:
    await client.close()
```

## More Examples Needed?

If you'd like to see examples for specific use cases, please open an issue or submit a PR!

Common requests:
- Grading assignments
- Creating forum posts
- Managing enrollments
- Quiz workflows
- Bulk operations
