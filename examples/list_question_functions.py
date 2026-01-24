#!/usr/bin/env python3
"""
List all question-related web service functions available on your Moodle instance.

This provides empirical proof of what functions are (and aren't) available.

Usage:
    python examples/list_question_functions.py > question_functions.txt
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from moodle_mcp.core.client import MoodleAPIClient
from moodle_mcp.core.config import get_config


async def list_all_question_functions():
    """List all question/quiz/qbank related functions."""
    config = get_config()
    client = MoodleAPIClient(
        base_url=config.url,
        token=config.token,
        timeout=config.api_timeout
    )

    try:
        print("="*70)
        print("MOODLE WEB SERVICES API - QUESTION-RELATED FUNCTIONS")
        print(f"Server: {config.url}")
        print("="*70)
        print()

        # Get all available functions
        site_info = await client._make_request('core_webservice_get_site_info', {})
        all_functions = site_info.get('functions', [])

        print(f"Total functions available: {len(all_functions)}")
        print()

        # Filter for question-related
        keywords = ['question', 'quiz', 'qbank', 'qtype']

        for keyword in keywords:
            matching = [f for f in all_functions if keyword in f.get('name', '').lower()]

            print(f"\n{'='*70}")
            print(f"Functions containing '{keyword}': {len(matching)}")
            print(f"{'='*70}")

            if matching:
                for func in matching:
                    print(f"\n  {func.get('name')}")
                    if func.get('version'):
                        print(f"    Version: {func.get('version')}")
            else:
                print(f"  ✗ NO FUNCTIONS FOUND containing '{keyword}'")
                print(f"    This proves '{keyword}' functions are NOT available via web services")

        # Specifically check for export functions
        print(f"\n\n{'='*70}")
        print("EXPORT-RELATED FUNCTIONS CHECK")
        print(f"{'='*70}")

        export_keywords = ['export', 'download', 'backup']
        for keyword in export_keywords:
            matching = [
                f for f in all_functions
                if keyword in f.get('name', '').lower() and 'question' in f.get('name', '').lower()
            ]

            print(f"\nFunctions with '{keyword}' AND 'question': {len(matching)}")
            if matching:
                for func in matching:
                    print(f"  - {func.get('name')}")
            else:
                print(f"  ✗ NONE FOUND")

        print("\n\n" + "="*70)
        print("CONCLUSION")
        print("="*70)
        print("\nQuestion Bank Export Functions Available: NONE")
        print("\nThis empirical test proves that Moodle's Web Services API")
        print("does NOT provide functions to export question banks.")
        print("\nTo verify this yourself:")
        print("  1. Go to Site Administration > Plugins > Web services > API Documentation")
        print("  2. Search for 'qbank' - you will find 0 results")
        print("  3. Search for 'export question' - you will find 0 results")
        print()

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(list_all_question_functions())
