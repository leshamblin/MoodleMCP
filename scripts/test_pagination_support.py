"""
Test which Moodle API functions support pagination parameters.

This script tests various Moodle web service functions to determine
if they support limitfrom/limitnum (offset/limit) pagination parameters.
"""

import asyncio
import json
from moodle_mcp.core.config import get_config
from moodle_mcp.core.client import MoodleAPIClient


async def test_function_pagination(client: MoodleAPIClient, function_name: str, base_params: dict, test_params: dict):
    """
    Test if a function supports pagination parameters.

    Args:
        client: Moodle API client
        function_name: Name of the web service function
        base_params: Required parameters for the function
        test_params: Pagination parameters to test (limitfrom, limitnum, page, perpage)

    Returns:
        dict: Results of the test
    """
    print(f"\n{'='*70}")
    print(f"Testing: {function_name}")
    print(f"{'='*70}")

    results = {
        'function': function_name,
        'supports_pagination': False,
        'param_style': None,
        'errors': []
    }

    # Test 1: Without pagination (baseline)
    try:
        print(f"  1. Baseline (no pagination params)...")
        baseline_data = await client._make_request(function_name, base_params)
        baseline_count = len(baseline_data) if isinstance(baseline_data, list) else len(baseline_data.get('users', [])) if 'users' in baseline_data else 0
        print(f"     ✓ Baseline returned {baseline_count} items")
        results['baseline_count'] = baseline_count
    except Exception as e:
        print(f"     ✗ Baseline failed: {e}")
        results['errors'].append(f"Baseline: {e}")
        return results

    # Test 2: With limitfrom/limitnum
    if 'limitfrom' in test_params and 'limitnum' in test_params:
        try:
            print(f"  2. Testing limitfrom={test_params['limitfrom']}, limitnum={test_params['limitnum']}...")
            params_with_limit = {**base_params, **test_params}
            limited_data = await client._make_request(function_name, params_with_limit)
            limited_count = len(limited_data) if isinstance(limited_data, list) else len(limited_data.get('users', [])) if 'users' in limited_data else 0
            print(f"     ✓ With limitfrom/limitnum returned {limited_count} items")

            if limited_count <= test_params['limitnum'] and limited_count < baseline_count:
                results['supports_pagination'] = True
                results['param_style'] = 'limitfrom/limitnum'
                print(f"     ✓ PAGINATION SUPPORTED! (limitfrom/limitnum)")
            else:
                print(f"     ? Unclear - same count or unexpected behavior")
        except Exception as e:
            print(f"     ✗ limitfrom/limitnum failed: {e}")
            results['errors'].append(f"limitfrom/limitnum: {e}")

    # Test 3: With page/perpage
    if 'page' in test_params and 'perpage' in test_params:
        try:
            print(f"  3. Testing page={test_params['page']}, perpage={test_params['perpage']}...")
            params_with_page = {**base_params, 'page': test_params['page'], 'perpage': test_params['perpage']}
            paged_data = await client._make_request(function_name, params_with_page)
            paged_count = len(paged_data) if isinstance(paged_data, list) else len(paged_data.get('users', [])) if 'users' in paged_data else 0
            print(f"     ✓ With page/perpage returned {paged_count} items")

            if paged_count <= test_params['perpage'] and paged_count < baseline_count:
                results['supports_pagination'] = True
                results['param_style'] = 'page/perpage'
                print(f"     ✓ PAGINATION SUPPORTED! (page/perpage)")
            else:
                print(f"     ? Unclear - same count or unexpected behavior")
        except Exception as e:
            print(f"     ✗ page/perpage failed: {e}")
            results['errors'].append(f"page/perpage: {e}")

    return results


async def main():
    """Test pagination support for various Moodle API functions."""
    config = get_config()
    client = MoodleAPIClient(base_url=config.url, token=config.token)

    try:
        # Get current user info and a test course
        site_info = await client.get_site_info()
        user_id = site_info['userid']
        print(f"\n{'='*70}")
        print(f"Testing Pagination Support - User ID: {user_id}")
        print(f"{'='*70}")

        # Get a course to test with
        courses = await client._make_request('core_enrol_get_users_courses', {'userid': user_id})
        if not courses:
            print("No courses found for testing. Exiting.")
            return

        test_course_id = courses[0]['id']
        print(f"Using test course ID: {test_course_id}")

        all_results = []

        # Test 1: core_enrol_get_enrolled_users
        all_results.append(await test_function_pagination(
            client,
            'core_enrol_get_enrolled_users',
            {'courseid': test_course_id},
            {'limitfrom': 0, 'limitnum': 5}
        ))

        # Test 2: core_course_search_courses
        all_results.append(await test_function_pagination(
            client,
            'core_course_search_courses',
            {'criterianame': 'search', 'criteriavalue': ''},
            {'limitfrom': 0, 'limitnum': 5, 'page': 0, 'perpage': 5}
        ))

        # Test 3: core_user_get_users_by_field
        all_results.append(await test_function_pagination(
            client,
            'core_user_get_users_by_field',
            {'field': 'id', 'values[0]': user_id},
            {'limitfrom': 0, 'limitnum': 1}
        ))

        # Test 4: core_course_get_courses (all courses)
        all_results.append(await test_function_pagination(
            client,
            'core_course_get_courses',
            {},
            {'limitfrom': 0, 'limitnum': 5}
        ))

        # Test 5: core_enrol_get_users_courses
        all_results.append(await test_function_pagination(
            client,
            'core_enrol_get_users_courses',
            {'userid': user_id},
            {'limitfrom': 0, 'limitnum': 3}
        ))

        # Test 6: core_message_get_conversations
        all_results.append(await test_function_pagination(
            client,
            'core_message_get_conversations',
            {'userid': user_id},
            {'limitfrom': 0, 'limitnum': 5}
        ))

        # Summary
        print(f"\n{'='*70}")
        print("SUMMARY - Pagination Support Test Results")
        print(f"{'='*70}\n")

        supported = [r for r in all_results if r['supports_pagination']]
        not_supported = [r for r in all_results if not r['supports_pagination']]

        print(f"✓ SUPPORTED ({len(supported)}):")
        for r in supported:
            print(f"  - {r['function']} [{r['param_style']}]")

        print(f"\n✗ NOT SUPPORTED or UNCLEAR ({len(not_supported)}):")
        for r in not_supported:
            print(f"  - {r['function']}")
            if r['errors']:
                for err in r['errors']:
                    print(f"      Error: {err}")

        print(f"\n{'='*70}")
        print("RECOMMENDATIONS:")
        print(f"{'='*70}\n")

        if supported:
            print("1. Functions that support pagination should pass params to API:")
            for r in supported:
                print(f"   - {r['function']} using {r['param_style']}")

        if not_supported:
            print(f"\n2. Functions without pagination support should use client-side slicing:")
            for r in not_supported:
                print(f"   - {r['function']}")

        print("\n3. Current implementation status:")
        print("   - messages.py: Already using limitfrom/limitnum ✓")
        print("   - badges.py: Already using page/perpage ✓")
        print("   - courses.py: Mixed (some client-side, needs review)")
        print("   - users.py: Client-side only (needs API params if supported)")
        print("   - forums.py: Using perpage for discussions")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
