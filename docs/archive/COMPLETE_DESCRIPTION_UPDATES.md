# Complete Tool Description Updates

This document contains the exact description text to replace for each of the remaining 30 tools.

## Status: 4/34 Complete (12%)

✅ Complete:
- moodle_get_site_info
- moodle_test_connection
- moodle_get_available_functions
- moodle_list_user_courses

## Course Tools (6 remaining)

### moodle_get_course_details
**Current:** `"Get detailed information about a specific course"`
**Replace with:** `"Get detailed course information including name, description, dates, format, and settings. REQUIRED: course_id (integer). Example: course_id=2292. Use moodle_list_user_courses to discover course IDs."`

### moodle_search_courses
**Current:** `"Search for courses by name, category, or other criteria"`
**Replace with:** `"Search for courses by name or description. REQUIRED: search_query (string, min 1 char). Optional: limit (integer, 1-100, default=20). Example: search_query='Python'. Returns course IDs that can be used with other course tools."`

### moodle_get_course_contents
**Current:** `"Get course structure including sections, modules, and activities"`
**Replace with:** `"Get full course content structure including sections, modules, activities, and resources. REQUIRED: course_id (integer). Example: course_id=2292. Use moodle_list_user_courses to get course_id."`

### moodle_get_enrolled_users
**Current:** `"Get list of users enrolled in a specific course"`
**Replace with:** `"Get list of all users enrolled in a course. REQUIRED: course_id (integer). Optional: limit (1-100, default=20), offset (default=0). Example: course_id=2292. Returns user IDs."`

### moodle_get_course_categories
**Current:** `"Get list of course categories"`
**Replace with:** `"Get all course categories from the Moodle site. NO PARAMETERS REQUIRED. Optional: format (default='markdown'). Useful for browsing course organization and discovering category IDs."`

### moodle_get_recent_courses
**Current:** `"Get recently accessed courses for the current user"`
**Replace with:** `"Get recently accessed courses for a user, sorted by most recent access. REQUIRED: user_id (integer). Optional: limit (1-50, default=10). Example: user_id=624. Use moodle_get_current_user to get user_id."`

## User Tools (5 remaining)

### moodle_get_current_user
**Current:** `"Get profile information for the currently authenticated user"`
**Replace with:** `"Get profile for currently authenticated user including user ID. NO PARAMETERS REQUIRED. Returns userid field (e.g., 624) needed for many other tools. Use this FIRST to discover your user_id. Optional: format (default='markdown')."`

### moodle_get_user_profile
**Current:** `"Get detailed profile information for a specific user by ID"`
**Replace with:** `"Get detailed user profile information. REQUIRED: user_id (integer). Example: user_id=624. Use moodle_get_current_user or moodle_search_users to get user_id."`

### moodle_search_users
**Current:** `"Search for users by name, email, or other criteria"`
**Replace with:** `"Search for users by name or email. REQUIRED: search_query (string, min 2 chars). Optional: limit (1-100, default=20). Example: search_query='Smith'. Returns user IDs."`

### moodle_get_user_preferences
**Current:** `"Get user preferences for the current or specified user"`
**Replace with:** `"Get user preferences and settings. REQUIRED: user_id (integer). Example: user_id=624. Use moodle_get_current_user to get user_id."`

### moodle_get_course_participants
**Current:** `"Get list of participants (users) in a specific course with their roles"`
**Replace with:** `"Get all participants (students, teachers, etc.) in a course with their roles. REQUIRED: course_id (integer). Optional: limit (1-100, default=20). Example: course_id=2292. Returns user IDs and role information."`

## Grade Tools (6 remaining)

### moodle_get_gradebook_overview
**Current:** `"Get all grades for a specific user across all their courses"`
**Replace with:** `"Get overview of all grades for a user across all enrolled courses. REQUIRED: user_id (integer). Example: user_id=624. Use moodle_get_current_user to get user_id."`

### moodle_get_course_grades
**Current:** `"Get all grades for a specific course (requires appropriate permissions)"`
**Replace with:** `"Get all grade items and grades for a course. REQUIRED: course_id (integer), user_id (integer). Example: course_id=2292, user_id=624. Use moodle_list_user_courses to get course_id."`

### moodle_get_grade_items
**Current:** `"Get list of grade items (graded activities) for a course"`
**Replace with:** `"Get all gradable items (assignments, quizzes, etc.) in a course. REQUIRED: course_id (integer). Optional: user_id (integer) for specific user's grades. Example: course_id=2292."`

### moodle_get_student_grade_summary
**Current:** `"Get grade summary for a student in a specific course"`
**Replace with:** `"Get grade summary with statistics for a student in a course. REQUIRED: course_id (integer), user_id (integer). Example: course_id=2292, user_id=624."`

### moodle_get_user_grades
**Current:** `"Get all grades for a specific user across all their courses"`
**Replace with:** `"Get user's grades for all items in a specific course. REQUIRED: course_id (integer), user_id (integer). Example: course_id=2292, user_id=624."`

### moodle_get_grade_report
**Current:** `"Get detailed grade report for a user in a specific course"`
**Replace with:** `"Get complete grade report for a user in a course. REQUIRED: course_id (integer), user_id (integer). Example: course_id=2292, user_id=624."`

## Assignment Tools (4 remaining)

### moodle_list_assignments
**Current:** `"Get list of assignments in a specific course"`
**Replace with:** `"Get all assignments in a course. REQUIRED: course_id (integer). Example: course_id=2292. Returns assignment IDs. Use moodle_list_user_courses to get course_id."`

### moodle_get_assignment_details
**Current:** `"Get detailed information about a specific assignment"`
**Replace with:** `"Get detailed information about an assignment including description, due date, and submission settings. REQUIRED: assignment_id (integer). Example: assignment_id=123. Use moodle_list_assignments to get assignment_id."`

### moodle_get_assignment_submissions
**Current:** `"Get submissions for an assignment (requires appropriate permissions)"`
**Replace with:** `"Get all submissions for an assignment (requires teacher/grader permissions). REQUIRED: assignment_id (integer). Example: assignment_id=123. Use moodle_list_assignments to get assignment_id."`

### moodle_get_user_assignments
**Current:** `"Get all assignments for a user across all enrolled courses"`
**Replace with:** `"Get all assignments for a user across all enrolled courses. REQUIRED: user_id (integer). Example: user_id=624. Use moodle_get_current_user to get user_id. Returns assignment IDs and due dates."`

## Message Tools (3 remaining)

### moodle_get_conversations
**Current:** `"Get list of message conversations for the current user"`
**Replace with:** `"Get message conversations for authenticated user. NO USER PARAMETERS REQUIRED - uses authenticated user automatically. Optional: limit (1-100, default=20), offset (default=0). Returns conversation IDs."`

### moodle_get_messages
**Current:** `"Get messages from a specific conversation"`
**Replace with:** `"Get messages from a specific conversation. REQUIRED: conversation_id (integer). Optional: limit (1-100, default=20). Example: conversation_id=456. Use moodle_get_conversations to get conversation_id."`

### moodle_get_unread_count
**Current:** `"Get count of unread messages for the current user"`
**Replace with:** `"Get count of unread messages for authenticated user. NO PARAMETERS REQUIRED. Returns simple integer count. Use this to check if there are new messages."`

## Calendar Tools (3 remaining)

### moodle_get_calendar_events
**Current:** `"Get calendar events for a date range"`
**Replace with:** `"Get calendar events for authenticated user's calendar over a date range. NO PARAMETERS REQUIRED. Optional: days_ahead (1-365, default=30). Example: days_ahead=60. Returns events including assignments, quizzes, and deadlines."`

### moodle_get_upcoming_events
**Current:** `"Get upcoming deadlines and important dates"`
**Replace with:** `"Get upcoming deadlines and events sorted chronologically. NO PARAMETERS REQUIRED. Optional: limit (1-50, default=10). Returns next upcoming events with dates and types."`

### moodle_get_course_events
**Current:** `"Get calendar events for a specific course"`
**Replace with:** `"Get calendar events specific to one course. REQUIRED: course_id (integer). Optional: days_ahead (1-365, default=60). Example: course_id=2292, days_ahead=30."`

## Forum Tools (3 remaining - if present)

### moodle_get_forum_discussions
**Current:** Likely `"Get list of discussions in a course forum"`
**Replace with:** `"Get forum discussions in a course. REQUIRED: course_id (integer). Optional: limit (1-100, default=20). Example: course_id=2292. Returns discussion IDs."`

### moodle_get_discussion_posts
**Current:** Likely `"Get posts from a specific forum discussion"`
**Replace with:** `"Get all posts from a forum discussion. REQUIRED: discussion_id (integer). Example: discussion_id=789. Use moodle_get_forum_discussions to get discussion_id."`

### moodle_search_forums
**Current:** Likely `"Search forum content across courses"`
**Replace with:** `"Search forum posts and discussions. REQUIRED: search_query (string, min 2 chars). Optional: course_id (integer) to limit search, limit (1-100, default=20). Example: search_query='homework', course_id=2292."`

## Implementation Instructions

For each tool above:

1. Open the corresponding file in `src/moodle_mcp/tools/`
2. Find the `@mcp.tool(` decorator
3. Locate the `description="..."` line
4. Replace the entire description string with the new text from above
5. Save the file

Files to update:
- `courses.py` - 6 tools remaining
- `users.py` - 5 tools remaining
- `grades.py` - 6 tools remaining
- `assignments.py` - 4 tools remaining
- `messages.py` - 3 tools remaining
- `calendar.py` - 3 tools remaining
- `forums.py` - 3 tools (if present)

## Priority Order

Update in this order for maximum LLM effectiveness:

1. **HIGH**: moodle_get_current_user (discovery tool)
2. **HIGH**: moodle_get_course_details (commonly used)
3. **HIGH**: moodle_get_user_assignments (commonly used)
4. **MEDIUM**: All other discovery tools (search_users, search_courses)
5. **LOW**: Specialized tools (forum, grade items)

## After Updates

Once complete, restart the MCP server and test with MCP Inspector to verify the descriptions appear correctly.
