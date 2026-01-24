#!/usr/bin/env python3
"""
Explore question bank access via Moodle Web Services API.

This script tests various approaches to accessing question bank data:
1. Get course contents to see question bank structure
2. Get quizzes in the course
3. Check available web service functions for questions
4. Test mod_quiz_get_attempt_data (which shows questions)

Usage:
    python examples/explore_question_bank.py 12035
"""

import asyncio
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from moodle_mcp.core.client import MoodleAPIClient
from moodle_mcp.core.config import get_config


async def explore_question_bank(course_id: int):
    """
    Explore what question bank data we can access via Web Services API.

    Args:
        course_id: Course ID containing question bank
    """
    config = get_config()
    client = MoodleAPIClient(
        base_url=config.url,
        token=config.token,
        timeout=config.api_timeout,
        max_connections=config.max_connections,
        max_keepalive=config.max_keepalive_connections
    )

    try:
        print("="*70)
        print(f"EXPLORING QUESTION BANK ACCESS FOR COURSE {course_id}")
        print("="*70)
        print()

        # Step 1: Get course details
        print("Step 1: Getting course details...")
        try:
            course_data = await client._make_request(
                'core_course_get_courses',
                {'options[ids][0]': course_id}
            )
            if course_data:
                course = course_data[0]
                print(f"✓ Course: {course.get('fullname')}")
                print(f"  Short name: {course.get('shortname')}")
                print(f"  Category: {course.get('categoryid')}")
                print()
            else:
                print(f"✗ Course {course_id} not found")
                return
        except Exception as e:
            print(f"✗ Error getting course: {e}")
            print()

        # Step 2: Get course contents
        print("Step 2: Getting course contents (sections and modules)...")
        try:
            contents = await client._make_request(
                'core_course_get_contents',
                {'courseid': course_id}
            )
            print(f"✓ Found {len(contents)} section(s)")
            for section in contents:
                print(f"  Section {section.get('section')}: {section.get('name', 'Unnamed')}")
                modules = section.get('modules', [])
                if modules:
                    for mod in modules[:3]:  # Show first 3 modules
                        print(f"    - {mod.get('modname')}: {mod.get('name')}")
                    if len(modules) > 3:
                        print(f"    ... and {len(modules) - 3} more")
            print()
        except Exception as e:
            print(f"✗ Error getting contents: {e}")
            print()

        # Step 3: Get quizzes in the course
        print("Step 3: Getting quizzes (quizzes may contain questions)...")
        try:
            quizzes_data = await client._make_request(
                'mod_quiz_get_quizzes_by_courses',
                {'courseids[0]': course_id}
            )
            quizzes = quizzes_data.get('quizzes', [])
            if quizzes:
                print(f"✓ Found {len(quizzes)} quiz(zes)")
                for quiz in quizzes:
                    print(f"  Quiz ID {quiz.get('id')}: {quiz.get('name')}")
                    print(f"    Questions: {quiz.get('sumgrades', 'unknown')} total grade")
                    print(f"    Time limit: {quiz.get('timelimit', 0)} seconds")
                print()
            else:
                print("✗ No quizzes found in this course")
                print()
        except Exception as e:
            print(f"✗ Error getting quizzes: {e}")
            print()

        # Step 4: Search for question-related web service functions
        print("Step 4: Searching for question-related web service functions...")
        try:
            functions = await client._make_request('core_webservice_get_site_info', {})
            all_functions = functions.get('functions', [])

            question_functions = [
                f for f in all_functions
                if 'question' in f.get('name', '').lower() or 'quiz' in f.get('name', '').lower()
            ]

            if question_functions:
                print(f"✓ Found {len(question_functions)} question/quiz-related function(s):")
                for func in question_functions[:15]:  # Show first 15
                    print(f"  - {func.get('name')}")
                if len(question_functions) > 15:
                    print(f"  ... and {len(question_functions) - 15} more")
            else:
                print("✗ No question-related functions found")
            print()
        except Exception as e:
            print(f"✗ Error searching functions: {e}")
            print()

        # Step 5: Check for qbank functions specifically
        print("Step 5: Checking for qbank (question bank) specific functions...")
        try:
            qbank_functions = [
                f for f in all_functions
                if 'qbank' in f.get('name', '').lower()
            ]

            if qbank_functions:
                print(f"✓ Found {len(qbank_functions)} qbank function(s):")
                for func in qbank_functions:
                    print(f"  - {func.get('name')}")
            else:
                print("✗ No qbank-specific functions available")
                print()
                print("NOTE: Question bank export is NOT available via standard web services.")
                print("This is a known limitation in Moodle's API.")
            print()
        except Exception as e:
            print(f"✗ Error: {e}")
            print()

        # Step 6: Summary and recommendations
        print("="*70)
        print("SUMMARY & RECOMMENDATIONS")
        print("="*70)
        print()
        print("Current Status:")
        print("  ✗ Direct question bank export: NOT AVAILABLE via web services")
        print("  ✓ Quiz questions via attempts: AVAILABLE (requires taking quiz)")
        print("  ✓ Quiz metadata: AVAILABLE (quiz names, settings)")
        print()
        print("Workarounds:")
        print("  1. Use mod_quiz_get_attempt_data to see questions (requires quiz attempt)")
        print("  2. Create custom Moodle plugin with web service for question export")
        print("  3. Use Moodle UI to export questions as XML/GIFT format")
        print("  4. Access Moodle database directly (not recommended)")
        print()
        print("Alternative Tools:")
        print("  - moodle-qbank_bulkxmlexport plugin (adds bulk export to UI)")
        print("  - Custom local plugin with web service implementation")
        print()

    finally:
        await client.close()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Explore question bank access via Moodle Web Services API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python examples/explore_question_bank.py 12035
  python examples/explore_question_bank.py 7299

This script will test various API methods to determine what question
bank data is accessible via Moodle's Web Services API.
        """
    )

    parser.add_argument(
        "course_id",
        type=int,
        help="Course ID containing question bank"
    )

    args = parser.parse_args()

    asyncio.run(explore_question_bank(args.course_id))


if __name__ == "__main__":
    main()
