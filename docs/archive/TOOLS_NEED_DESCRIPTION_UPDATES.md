# Tools Needing Description Updates

## Current Status

Only **1 out of 34 tools** has a comprehensive description with parameter information:
- ✅ `moodle_get_site_info` - Has full parameter details

The remaining **33 tools** have generic descriptions that don't clearly indicate:
- Which parameters are REQUIRED vs OPTIONAL
- What types and ranges are expected
- Example values or IDs
- How to discover required IDs

## Tools That Need Updates

### Site Tools
- ❌ `moodle_test_connection` - Should say "NO PARAMETERS REQUIRED"
- ❌ `moodle_get_available_functions` - Should say "NO PARAMETERS REQUIRED, optional format"

### Course Tools
- ❌ `moodle_list_user_courses` - Should say "REQUIRED: user_id (integer)"
- ❌ `moodle_get_course_details` - Should say "REQUIRED: course_id (integer)"
- ❌ `moodle_search_courses` - Should say "REQUIRED: search_query (string)"
- ❌ `moodle_get_course_contents` - Should say "REQUIRED: course_id (integer)"
- ❌ `moodle_get_enrolled_users` - Should say "REQUIRED: course_id (integer)"
- ❌ `moodle_get_course_categories` - Should say "NO PARAMETERS REQUIRED"
- ❌ `moodle_get_recent_courses` - Should say "REQUIRED: user_id (integer)"

### User Tools
- ❌ `moodle_get_current_user` - Should say "NO PARAMETERS REQUIRED - returns current user with ID"
- ❌ `moodle_get_user_profile` - Should say "REQUIRED: user_id (integer)"
- ❌ `moodle_search_users` - Should say "REQUIRED: search_query (string, min 2 chars)"
- ❌ `moodle_get_user_preferences` - Should say "REQUIRED: user_id (integer)"
- ❌ `moodle_get_course_participants` - Should say "REQUIRED: course_id (integer)"

### Grade Tools (all need updates)
- ❌ `moodle_get_gradebook_overview` - Should say "REQUIRED: user_id (integer)"
- ❌ `moodle_get_course_grades` - Should say "REQUIRED: course_id (integer), user_id (integer)"
- ❌ `moodle_get_grade_items` - Should say "REQUIRED: course_id (integer)"
- ❌ `moodle_get_student_grade_summary` - Should say "REQUIRED: course_id (integer), user_id (integer)"
- ❌ `moodle_get_user_grades` - Should say "REQUIRED: user_id (integer)"
- ❌ `moodle_get_grade_report` - Should say "REQUIRED: course_id (integer), user_id (integer)"

### Assignment Tools
- ❌ `moodle_list_assignments` - Should say "REQUIRED: course_id (integer)"
- ❌ `moodle_get_assignment_details` - Should say "REQUIRED: assignment_id (integer)"
- ❌ `moodle_get_assignment_submissions` - Should say "REQUIRED: assignment_id (integer)"
- ❌ `moodle_get_user_assignments` - Should say "REQUIRED: user_id (integer)"

### Message Tools
- ❌ `moodle_get_conversations` - Should say "NO USER PARAMETERS REQUIRED - uses authenticated user"
- ❌ `moodle_get_messages` - Should say "REQUIRED: conversation_id (integer)"
- ❌ `moodle_get_unread_count` - Should say "NO PARAMETERS REQUIRED"

### Calendar Tools
- ❌ `moodle_get_calendar_events` - Should say "NO PARAMETERS REQUIRED - optional days_ahead (default 30)"
- ❌ `moodle_get_upcoming_events` - Should say "NO PARAMETERS REQUIRED - optional limit (default 10)"
- ❌ `moodle_get_course_events` - Should say "REQUIRED: course_id (integer)"

### Forum Tools
- ❌ `moodle_get_forum_discussions` - Should say "REQUIRED: course_id (integer)"
- ❌ `moodle_get_discussion_posts` - Should say "REQUIRED: discussion_id (integer)"
- ❌ `moodle_search_forums` - Should say "REQUIRED: search_query (string, min 2 chars)"

## Recommended Description Format

Each description should follow this pattern:

```
"[What it does]. REQUIRED: param1 (type), param2 (type). Optional: param3 (type, default=X). Example: param1=123, param2=456. Use [related_tool] to discover IDs."
```

### Examples:

**Good:**
```python
description="Get detailed course information including name, description, dates, and format. REQUIRED: course_id (integer). Optional: format ('markdown' or 'json', default='markdown'). Example: course_id=2292. Use moodle_list_user_courses to discover course IDs."
```

**Bad (current):**
```python
description="Get detailed information about a specific course"
```

## Impact

Without clear parameter documentation in descriptions:
1. **LLMs don't know which tools need which parameters**
2. **LLMs try to call tools without required parameters** → Errors
3. **LLMs don't know how to discover IDs** → Can't chain tools properly
4. **Users get confusing error messages** about missing parameters

## Solution

Need to update all `@mcp.tool()` decorators to include comprehensive descriptions with:
- Clear REQUIRED vs OPTIONAL indicators
- Parameter types and defaults
- Example values
- How to discover required IDs (e.g., "Use moodle_get_current_user to get user_id")
