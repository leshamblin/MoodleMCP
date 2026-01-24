#!/usr/bin/env python3
"""
Example script: Look up all courses for a specific user by name.

This demonstrates the two-step process:
1. Search for user by name to get user_id
2. Get all courses for that user_id

Usage:
    python examples/lookup_user_courses.py "Andy Click"
    python examples/lookup_user_courses.py "Andy Click" --json
    python examples/lookup_user_courses.py "Andy Click" --include-hidden
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from moodle_mcp.core.client import MoodleAPIClient
from moodle_mcp.core.config import get_config
from moodle_mcp.tools.users import moodle_search_users
from moodle_mcp.tools.courses import moodle_list_user_courses
from moodle_mcp.models.base import ResponseFormat


class MockContext:
    """Mock FastMCP Context for standalone execution."""

    def __init__(self, moodle_client: MoodleAPIClient):
        self.request_context = MockRequestContext(moodle_client)


class MockRequestContext:
    """Mock request context with lifespan_context."""

    def __init__(self, moodle_client: MoodleAPIClient):
        self.lifespan_context = {
            "moodle_client": moodle_client
        }


async def lookup_user_courses(
    user_name: str,
    include_hidden: bool = False,
    output_format: ResponseFormat = ResponseFormat.MARKDOWN
):
    """
    Look up all courses for a user by their name.

    Args:
        user_name: Full name or partial name to search for
        include_hidden: Whether to include hidden courses
        output_format: Output format (MARKDOWN or JSON)

    Returns:
        Formatted string with user's courses
    """
    # Initialize Moodle client
    config = get_config()
    client = MoodleAPIClient(
        base_url=config.url,
        token=config.token,
        timeout=config.api_timeout,
        max_connections=config.max_connections,
        max_keepalive=config.max_keepalive_connections
    )

    # Create mock context
    ctx = MockContext(client)

    try:
        print(f"🔍 Searching for user: '{user_name}'...")
        print()

        # Step 1: Search for user by name
        # Unwrap the tool function if needed
        search_func = moodle_search_users.fn if hasattr(moodle_search_users, 'fn') else moodle_search_users

        user_results = await search_func(
            search_query=user_name,
            limit=5,
            format=ResponseFormat.JSON,
            ctx=ctx
        )

        # Parse JSON to find user_id
        import json
        try:
            user_data = json.loads(user_results)
        except json.JSONDecodeError:
            print("❌ Error: Could not parse user search results")
            print(user_results)
            return

        # Check if we found any users
        if not user_data or len(user_data) == 0:
            print(f"❌ No users found matching '{user_name}'")
            print()
            print("💡 Tips:")
            print("   - Try a partial name (e.g., 'Andy' or 'Click')")
            print("   - Check the spelling")
            print("   - Try searching by email if you know it")
            return

        # Display found users
        print(f"✅ Found {len(user_data)} user(s):")
        print()
        for i, user in enumerate(user_data, 1):
            print(f"{i}. {user.get('fullname', 'Unknown')} (ID: {user.get('id')})")
            if user.get('email'):
                print(f"   Email: {user.get('email')}")
            if user.get('username'):
                print(f"   Username: {user.get('username')}")
            print()

        # Use first user for course lookup
        selected_user = user_data[0]
        user_id = selected_user.get('id')
        user_fullname = selected_user.get('fullname', 'Unknown')

        if not user_id:
            print("❌ Error: Selected user has no ID")
            return

        print(f"📚 Looking up courses for: {user_fullname} (ID: {user_id})...")
        print()

        # Step 2: Get courses for this user
        # Unwrap the tool function if needed
        courses_func = moodle_list_user_courses.fn if hasattr(moodle_list_user_courses, 'fn') else moodle_list_user_courses

        courses_result = await courses_func(
            user_id=user_id,
            include_hidden=include_hidden,
            format=output_format,
            ctx=ctx
        )

        # Display results
        print("="*70)
        print(courses_result)
        print("="*70)

    finally:
        # Clean up
        await client.close()


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Look up all courses for a Moodle user by name",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python examples/lookup_user_courses.py "Andy Click"
  python examples/lookup_user_courses.py "Andy Click" --json
  python examples/lookup_user_courses.py "Andy Click" --include-hidden
  python examples/lookup_user_courses.py "Andy" --json

Environment:
  Set MOODLE_ENV=dev or MOODLE_ENV=prod to switch environments
  Ensure .env file has MOODLE_DEV_URL and MOODLE_DEV_TOKEN configured
        """
    )

    parser.add_argument(
        "user_name",
        help="Full name or partial name of the user to search for"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format instead of Markdown"
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden courses in the results"
    )

    args = parser.parse_args()

    # Determine output format
    output_format = ResponseFormat.JSON if args.json else ResponseFormat.MARKDOWN

    # Run the async function
    asyncio.run(lookup_user_courses(
        user_name=args.user_name,
        include_hidden=args.include_hidden,
        output_format=output_format
    ))


if __name__ == "__main__":
    main()
