# Moodle Web Service Configuration Issue

## Problem Summary

The MCP server tools for adding/removing users from groups are failing with:
```
MoodleAuthError: Authentication failed: Access control exception
```

However, this error message is **misleading**. The actual problem is that the required web service functions are **not enabled** in the Moodle web service configuration.

## Evidence from REST API Verification

Using direct HTTP calls to the Moodle REST API (`verify_web_service.py`), we confirmed:

### ✅ Available Functions Work
```
Function: core_group_get_course_groups
Status: ✅ SUCCESS - Returns 40 groups
HTTP Status: 200
```

### ❌ Required Functions Are Missing
```
Function: core_group_add_group_members
Status: ❌ ERROR - Access control exception
Error Code: accessexception
Debug Info: "Access to the function core_group_add_group_members() is not allowed.
             The service linked to the user token does not contain the function."
```

### Function Availability Report

Out of **450 total available functions**, only **12** are group-related:

**Available Group Functions:**
- ✅ core_group_get_course_groups
- ✅ core_group_get_course_groupings
- ✅ core_group_get_course_user_groups
- ✅ core_group_get_activity_allowed_groups
- ✅ core_group_get_activity_groupmode
- ✅ core_group_get_groups_for_selector
- ✅ core_grades_get_groups_for_search_widget
- ✅ core_grades_get_groups_for_selector
- ✅ mod_choicegroup_* (4 functions)

**Missing Group Functions:**
- ❌ `core_group_add_group_members` - **REQUIRED** for adding users to groups
- ❌ `core_group_delete_group_members` - **REQUIRED** for removing users from groups
- ❌ `core_group_create_groups` - **REQUIRED** for creating new groups

## Why This Happened

Elizabeth has full permissions as a professor/admin in the UI, which is why she can add students to groups via the web interface. However:

1. The **web service API** has its own separate permission system
2. The API token must be linked to a **web service** that explicitly includes these functions
3. Even with admin capabilities, if the function isn't in the web service definition, the API call will fail

## How to Fix

Elizabeth needs to configure the Moodle web service to include the missing functions:

### Step 1: Navigate to Web Services Configuration
1. Log in to Moodle as admin
2. Go to: **Site administration** → **Server** → **Web services** → **External services**

### Step 2: Find or Create the Service
- Look for the service associated with her API token
- If no service exists, create a new one:
  - Click "Add" to create a new external service
  - Name it something like "MCP API Service"
  - Enable it

### Step 3: Add Required Functions
Click on "Functions" for the service and add these functions:

**Critical Functions for Group Management:**
```
core_group_add_group_members      - Add users to groups
core_group_delete_group_members   - Remove users from groups
core_group_create_groups          - Create new groups
core_group_delete_groups          - Delete groups
core_group_get_group_members      - Get group membership
```

**Already Available (no action needed):**
```
core_group_get_course_groups      - List course groups
core_group_get_course_groupings   - List groupings
```

### Step 4: Link Token to Service
1. Go to: **Site administration** → **Server** → **Web services** → **Manage tokens**
2. Find Elizabeth's token (user: leshamb2@ncsu.edu)
3. Ensure it's linked to the service you just configured
4. If not, edit the token and select the correct service

### Step 5: Verify Configuration
Run the verification script to confirm all functions are now available:
```bash
source .venv/bin/activate
PYTHONPATH=src python3 verify_web_service.py
```

You should see:
```
🔍 Checking for required functions:
   ✅ core_group_add_group_members - AVAILABLE
   ✅ core_group_delete_group_members - AVAILABLE
   ✅ core_group_create_groups - AVAILABLE
   ✅ core_group_get_course_groups - AVAILABLE
```

## Testing After Configuration

Once the functions are enabled, test the group operations:

### Test 1: Add Justin Case to Group 1
```bash
source .venv/bin/activate
PYTHONPATH=src python3 debug_justin.py
```

Expected output:
```
✅ SUCCESS! Result:
Successfully added 1 user(s) to group 'Group 1'
```

### Test 2: Run Full Test Suite
```bash
pytest tests/test_real_api.py::TestDebugJustinCase -xvs
```

## Alternative: Check Service Capabilities

If you have SSH access to the Moodle server, you can check which functions are available for a service using the Moodle CLI:

```bash
php admin/cli/webservice_list_functions.php --serviceid=<service_id>
```

## Documentation References

- [Moodle Web Services API](https://docs.moodle.org/dev/Web_service_API_functions)
- [External Services Configuration](https://docs.moodle.org/en/External_services)
- [Web Services Tokens](https://docs.moodle.org/en/Using_web_services#Managing_tokens)

## Summary

This is **not a code bug** in the MCP server. The tools are correctly implemented and will work once the Moodle web service is configured to include the required functions.

The misleading error message "Authentication failed: Access control exception" should be interpreted as "This function is not available in your web service configuration" rather than "You don't have permissions."
