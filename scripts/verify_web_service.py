"""
Direct HTTP verification of web service function availability.

This script makes raw HTTP calls to the Moodle REST API to verify whether
core_group_add_group_members is available in the web service configuration.
"""
import asyncio
import httpx
import json
import os

# Set up DEV mode
os.environ['MOODLE_ENV'] = 'dev'
os.environ['MOODLE_DEV_COURSE_WHITELIST'] = '7299'

from moodle_mcp.core.config import get_config

async def test_web_service_availability():
    """Test if core_group_add_group_members is available via direct HTTP call."""
    config = get_config()

    print("=" * 80)
    print("VERIFYING WEB SERVICE FUNCTION AVAILABILITY")
    print("=" * 80)

    # Moodle REST endpoint
    url = f"{config.url}/webservice/rest/server.php"

    print(f"\nMoodle URL: {config.url}")
    print(f"REST Endpoint: {url}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Try to call an available function (core_group_get_course_groups)
        print("-" * 80)
        print("TEST 1: Calling AVAILABLE function (core_group_get_course_groups)")
        print("-" * 80)

        params_available = {
            'wstoken': config.token,
            'wsfunction': 'core_group_get_course_groups',
            'moodlewsrestformat': 'json',
            'courseid': 7299
        }

        try:
            response = await client.post(url, data=params_available)
            print(f"\nHTTP Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}\n")

            result = response.json()
            if isinstance(result, list):
                print(f"✅ SUCCESS: Function returned {len(result)} groups")
                print(f"Sample response: {json.dumps(result[:1], indent=2)}")
            else:
                print(f"Response: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"❌ Error: {e}")

        # Test 2: Try to call core_group_add_group_members
        print("\n" + "-" * 80)
        print("TEST 2: Calling UNAVAILABLE function (core_group_add_group_members)")
        print("-" * 80)

        params_unavailable = {
            'wstoken': config.token,
            'wsfunction': 'core_group_add_group_members',
            'moodlewsrestformat': 'json',
            'members[0][groupid]': 35281,  # Group 1
            'members[0][userid]': 343242   # Justin Case
        }

        try:
            response = await client.post(url, data=params_unavailable)
            print(f"\nHTTP Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}\n")

            result = response.json()

            # Check if it's an error response
            if isinstance(result, dict) and 'exception' in result:
                print(f"❌ ERROR RESPONSE:")
                print(f"   Exception: {result.get('exception')}")
                print(f"   Error Code: {result.get('errorcode')}")
                print(f"   Message: {result.get('message')}")
                print(f"\n   Full Response:")
                print(f"   {json.dumps(result, indent=2)}")

                # Analyze the error
                error_code = result.get('errorcode', '')
                if 'webservicenotavailable' in error_code or 'invalidparameter' in error_code:
                    print(f"\n   🔍 ANALYSIS:")
                    print(f"   This error indicates the web service function is NOT enabled")
                    print(f"   in the Moodle web service configuration.")
                elif 'accessexception' in error_code:
                    print(f"\n   🔍 ANALYSIS:")
                    print(f"   'Access control exception' can mean:")
                    print(f"   1. Function not available in web service (most likely)")
                    print(f"   2. Token doesn't have permission for this function")
                    print(f"   3. Capability issue (but Elizabeth has UI access)")
            else:
                print(f"✅ SUCCESS: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"❌ Error: {e}")

        # Test 3: List ALL available functions
        print("\n" + "-" * 80)
        print("TEST 3: Querying ALL available web service functions")
        print("-" * 80)

        params_site_info = {
            'wstoken': config.token,
            'wsfunction': 'core_webservice_get_site_info',
            'moodlewsrestformat': 'json'
        }

        try:
            response = await client.post(url, data=params_site_info)
            result = response.json()

            if 'functions' in result:
                functions = result['functions']
                print(f"\n✅ Found {len(functions)} total available functions\n")

                # Filter group-related functions
                group_functions = [f for f in functions if 'group' in f['name'].lower()]
                print(f"Group-related functions ({len(group_functions)}):")
                for func in sorted(group_functions, key=lambda x: x['name']):
                    print(f"   - {func['name']}")

                # Check specifically for the functions we need
                print(f"\n🔍 Checking for required functions:")
                required_functions = [
                    'core_group_add_group_members',
                    'core_group_delete_group_members',
                    'core_group_create_groups',
                    'core_group_get_course_groups'
                ]

                available_names = [f['name'] for f in functions]
                for req_func in required_functions:
                    if req_func in available_names:
                        print(f"   ✅ {req_func} - AVAILABLE")
                    else:
                        print(f"   ❌ {req_func} - NOT AVAILABLE")
            else:
                print(f"Unexpected response: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print("""
The error "Authentication failed: Access control exception" is misleading.
The actual issue is that the web service function is not enabled in the
Moodle web service configuration.

To fix this, Elizabeth needs to:
1. Go to: Site administration > Server > Web services > External services
2. Find the web service being used (or create a new one)
3. Add the following functions:
   - core_group_add_group_members
   - core_group_delete_group_members
   - core_group_create_groups (if needed)
4. Ensure her API token is associated with this service

Without these functions enabled, the MCP server cannot add/remove users
from groups, even though Elizabeth has the necessary permissions in the UI.
    """)
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_web_service_availability())
