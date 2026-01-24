# Moodle MCP Tool Parameters Reference

This document provides comprehensive parameter information for all Moodle MCP tools to help LLMs understand when and how to use each tool.

## Site Tools

### moodle_get_site_info
**Description:** Get comprehensive Moodle site information
**Required Parameters:** None
**Optional Parameters:**
- `format` (string): Output format - 'markdown' (default) or 'json'

**Usage:** Use this first to get the current user's ID which is needed for many other tools.

**Example:** `moodle_get_site_info(format='json')`

---

### moodle_test_connection
**Description:** Test connection to Moodle server
**Required Parameters:** None
**Optional Parameters:** None

**Usage:** Verify server is accessible and authentication works.

---

### moodle_get_available_functions
**Description:** List all available Moodle Web Services functions
**Required Parameters:** None
**Optional Parameters:**
- `format` (string): Output format - 'markdown' (default) or 'json'

---

## Course Tools

### moodle_list_user_courses
**Description:** Get list of courses a user is enrolled in
**Required Parameters:**
- `user_id` (integer): User ID - get from moodle_get_site_info or moodle_get_current_user

**Optional Parameters:**
- `include_hidden` (boolean): Include hidden courses (default: False)
- `format` (string): Output format - 'markdown' (default) or 'json'

**Example:** `moodle_list_user_courses(user_id=624, format='json')`

---

###  moodle_get_course_categories
**Description:** Get all course categories
**Required Parameters:** None
**Optional Parameters:**
- `format` (string): Output format - 'markdown' (default) or 'json'

---

### moodle_get_recent_courses
**Description:** Get recently accessed courses for a user
**Required Parameters:**
- `user_id` (integer): User ID

**Optional Parameters:**
- `limit` (integer): Maximum results (default: 10, range: 1-50)
- `format` (string): Output format - 'markdown' (default) or 'json'

**Example:** `moodle_get_recent_courses(user_id=624, limit=5)`

---

### moodle_get_course_details
**Description:** Get detailed information about a specific course
**Required Parameters:**
- `course_id` (integer): Course ID - get from moodle_list_user_courses

**Optional Parameters:**
- `format` (string): Output format - 'markdown' (default) or 'json'

**Example:** `moodle_get_course_details(course_id=2292)`

---

### moodle_get_course_contents
**Description:** Get full course content structure
**Required Parameters:**
- `course_id` (integer): Course ID

**Optional Parameters:**
- `format` (string): Output format - 'markdown' (default) or 'json'

**Example:** `moodle_get_course_contents(course_id=2292)`

---

### moodle_get_enrolled_users
**Description:** Get list of users enrolled in a course
**Required Parameters:**
- `course_id` (integer): Course ID

**Optional Parameters:**
- `limit` (integer): Maximum results (default: 50, range: 1-200)
- `format` (string): Output format - 'markdown' (default) or 'json'

---

### moodle_search_courses
**Description:** Search for courses by name or description
**Required Parameters:**
- `search_query` (string): Search term (minimum 1 character)

**Optional Parameters:**
- `limit` (integer): Maximum results (default: 20, range: 1-100)
- `format` (string): Output format - 'markdown' (default) or 'json'

**Example:** `moodle_search_courses(search_query='Python', limit=10)`

---

## User Tools

### moodle_get_current_user
**Description:** Get profile for currently authenticated user
**Required Parameters:** None
**Optional Parameters:**
- `format` (string): Output format - 'markdown' (default) or 'json'

**Usage:** Use this to get the current user's ID (userid field) for other tools.

**Example:** `moodle_get_current_user(format='json')` returns `{"userid": 624, ...}`

---

### moodle_get_user_profile
**Description:** Get detailed profile for a specific user
**Required Parameters:**
- `user_id` (integer): User ID

**Optional Parameters:**
- `format` (string): Output format - 'markdown' (default) or 'json'

**Example:** `moodle_get_user_profile(user_id=624)`

---

### moodle_get_user_preferences
**Description:** Get user preferences and settings
**Required Parameters:**
- `user_id` (integer): User ID

**Optional Parameters:**
- `format` (string): Output format - 'markdown' (default) or 'json'

---

### moodle_search_users
**Description:** Search for users by name or email
**Required Parameters:**
- `search_query` (string): Search term (minimum 1 character)

**Optional Parameters:**
- `limit` (integer): Maximum results (default: 20, range: 1-100)
- `format` (string): Output format - 'markdown' (default) or 'json'

**Example:** `moodle_search_users(search_query='Smith', limit=10)`

---

## Grade Tools

### moodle_get_gradebook_overview
**Description:** Get overview of all grades for a user across all courses
**Required Parameters:**
- `user_id` (integer): User ID

**Optional Parameters:**
- `format` (string): Output format - 'markdown' (default) or 'json'

**Example:** `moodle_get_gradebook_overview(user_id=624)`

---

### moodle_get_student_grade_summary
**Description:** Get summary of student's grades with statistics
**Required Parameters:**
- `user_id` (integer): User ID

**Optional Parameters:**
- `format` (string): Output format - 'markdown' (default) or 'json'

---

### moodle_get_course_grades
**Description:** Get all grades for a user in a specific course
**Required Parameters:**
- `course_id` (integer): Course ID
- `user_id` (integer): User ID

**Optional Parameters:**
- `format` (string): Output format - 'markdown' (default) or 'json'

**Example:** `moodle_get_course_grades(course_id=2292, user_id=624)`

---

### moodle_get_grade_items
**Description:** Get all gradable items in a course
**Required Parameters:**
- `course_id` (integer): Course ID

**Optional Parameters:**
- `format` (string): Output format - 'markdown' (default) or 'json'

**Example:** `moodle_get_grade_items(course_id=2292)`

---

## Assignment Tools

### moodle_get_user_assignments
**Description:** Get all assignments for a user across all courses
**Required Parameters:**
- `user_id` (integer): User ID

**Optional Parameters:**
- `format` (string): Output format - 'markdown' (default) or 'json'

**Example:** `moodle_get_user_assignments(user_id=624)`

---

### moodle_list_assignments
**Description:** Get all assignments in a specific course
**Required Parameters:**
- `course_id` (integer): Course ID

**Optional Parameters:**
- `format` (string): Output format - 'markdown' (default) or 'json'

**Example:** `moodle_list_assignments(course_id=2292)`

---

## Message Tools

### moodle_get_messages
**Description:** Get messages for authenticated user
**Required Parameters:** None (uses authenticated user)
**Optional Parameters:**
- `limit` (integer): Maximum messages (default: 20, range: 1-100)
- `unread_only` (boolean): Only unread messages (default: False)
- `format` (string): Output format - 'markdown' (default) or 'json'

**Example:** `moodle_get_messages(unread_only=True, limit=10)`

---

### moodle_get_unread_count
**Description:** Get count of unread messages
**Required Parameters:** None
**Optional Parameters:** None

**Returns:** Integer count of unread messages

---

## Calendar Tools

### moodle_get_calendar_events
**Description:** Get calendar events for a date range
**Required Parameters:** None (uses authenticated user's calendar)
**Optional Parameters:**
- `days_ahead` (integer): Days to look ahead (default: 30, range: 1-365)
- `format` (string): Output format - 'markdown' (default) or 'json'

**Example:** `moodle_get_calendar_events(days_ahead=60)`

---

### moodle_get_upcoming_events
**Description:** Get upcoming deadlines sorted chronologically
**Required Parameters:** None
**Optional Parameters:**
- `limit` (integer): Maximum events (default: 10, range: 1-50)
- `format` (string): Output format - 'markdown' (default) or 'json'

**Example:** `moodle_get_upcoming_events(limit=20)`

---

### moodle_get_course_events
**Description:** Get calendar events for a specific course
**Required Parameters:**
- `course_id` (integer): Course ID

**Optional Parameters:**
- `days_ahead` (integer): Days to look ahead (default: 60, range: 1-365)
- `format` (string): Output format - 'markdown' (default) or 'json'

**Example:** `moodle_get_course_events(course_id=2292, days_ahead=30)`

---

## Common Workflows

### Getting Started
1. **First call:** `moodle_get_current_user(format='json')` to get your user ID
2. **List courses:** `moodle_list_user_courses(user_id=YOUR_ID)`
3. **Get course details:** `moodle_get_course_details(course_id=COURSE_ID)`

### Checking Assignments
1. **Get all assignments:** `moodle_get_user_assignments(user_id=YOUR_ID)`
2. **Get course assignments:** `moodle_list_assignments(course_id=COURSE_ID)`

### Checking Grades
1. **Grade overview:** `moodle_get_gradebook_overview(user_id=YOUR_ID)`
2. **Course grades:** `moodle_get_course_grades(course_id=COURSE_ID, user_id=YOUR_ID)`

### Checking Calendar
1. **Upcoming events:** `moodle_get_upcoming_events(limit=10)`
2. **Course events:** `moodle_get_course_events(course_id=COURSE_ID)`

## Important Notes

1. **User ID:** Most user-specific tools require a `user_id`. Get this from:
   - `moodle_get_current_user()` for the authenticated user
   - `moodle_get_site_info()` (returns current user's ID in the response)
   - `moodle_search_users()` for other users

2. **Course ID:** Get course IDs from:
   - `moodle_list_user_courses(user_id=USER_ID)`
   - `moodle_search_courses(search_query='...')`

3. **Format Parameter:** All tools support:
   - `'markdown'` - Human-readable formatted output (default)
   - `'json'` - Machine-readable structured data

4. **Read-Only:** ALL tools are READ-ONLY. No data is ever modified.

5. **Error Handling:** If a tool requires parameters you don't have:
   - First call discovery tools (site_info, current_user, list_courses)
   - Then call specific tools with the discovered IDs
