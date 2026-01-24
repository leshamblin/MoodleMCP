# Groups Tools Documentation

New group management tools added to the Moodle MCP server.

## Overview

Groups in Moodle allow students to be organized into smaller cohorts within a course. These tools provide read-only access to group information.

## Available Tools

### 1. `moodle_get_course_groups`

Get all groups in a course.

**Parameters:**
- `course_id` (required): Course ID
- `format` (optional): Output format (markdown or json)

**Returns:**
Group information including:
- Group ID
- Group name
- Group description
- Number of members
- Related grouping information

**Example:**
```
"What groups exist in course 2292?"
"List all groups in my Programming course"
```

**API Function:** `core_group_get_course_groups`

---

### 2. `moodle_get_course_groupings`

Get all groupings in a course.

**What are groupings?**
Groupings are collections of groups. They allow you to create subsets of groups for specific activities.

**Parameters:**
- `course_id` (required): Course ID
- `format` (optional): Output format (markdown or json)

**Returns:**
Grouping information including:
- Grouping ID
- Grouping name
- Grouping description
- List of groups in the grouping

**Example:**
```
"What groupings exist in course 2292?"
"Show me the groupings for my Math course"
```

**API Function:** `core_group_get_course_groupings`

---

### 3. `moodle_get_activity_allowed_groups`

Get groups that can access a specific activity (course module).

**Parameters:**
- `cmid` (required): Course module ID (activity ID)
- `user_id` (optional): User ID (defaults to current user)
- `format` (optional): Output format (markdown or json)

**Returns:**
List of groups with access to the activity based on:
- Activity's group mode
- Group restrictions
- User's group memberships

**Example:**
```
"What groups can access assignment 456?"
"Show me which groups are in this forum"
```

**API Function:** `core_group_get_activity_allowed_groups`

---

### 4. `moodle_get_activity_groupmode`

Get the group mode for a specific activity.

**Group Modes:**
- **0: No groups** - Activity is not divided by groups
- **1: Separate groups** - Students can only see their own group
- **2: Visible groups** - Students can see all groups but work in their own

**Parameters:**
- `cmid` (required): Course module ID (activity ID)
- `format` (optional): Output format (markdown or json)

**Returns:**
Group mode information including:
- Group mode value (0, 1, or 2)
- Whether the mode is forced at course level
- Human-readable interpretation

**Example:**
```
"What is the group mode for activity 123?"
"Does this assignment use separate groups?"
```

**API Function:** `core_group_get_activity_groupmode`

---

## Finding IDs

### To get a Course ID:
Use `moodle_list_user_courses` or `moodle_search_courses`

### To get a Course Module ID (cmid):
Use `moodle_get_course_contents` - each module/activity has an `id` field

---

## Common Workflows

### 1. View all groups in a course:
```
1. Get course ID: "List my courses"
2. Get groups: "Show me all groups in course 2292"
```

### 2. See which students are in which groups:
```
1. Get enrolled users with groups: "List enrolled users in course 2292 with their groups" (include_groups=true)
2. Or individually: Get user's groups with moodle_get_course_user_groups
```

### 3. Check if an activity uses groups:
```
1. Get course contents: "Show contents of course 2292"
2. Find the activity's cmid
3. Check group mode: "What is the group mode for activity 456?"
```

### 4. See which groups can access an assignment:
```
1. Get assignment details
2. Find the cmid (course module ID)
3. Get allowed groups: "What groups can access activity 456?"
```

---

## Group Mode Explanation

### No Groups (0)
- All students work together
- No group restrictions
- Common for lectures, resources

### Separate Groups (1)
- Students see only their group's work
- Cannot interact with other groups
- Common for group projects, discussions
- Teachers see all groups

### Visible Groups (2)
- Students see all groups but submit in their own
- Can view but not interact with other groups
- Common for peer learning activities

---

## Limitations

These tools are **READ-ONLY**. You cannot:
- Create or delete groups
- Add or remove group members
- Change group modes
- Modify groupings

For these actions, use the Moodle web interface.

---

## Error Handling

Common errors:

- **"Invalid parameter"** - Check course_id or cmid is correct
- **"Access control exception"** - You may not have permission to view groups
- **"No groups found"** - The course has no groups configured

---

## Examples

### Get groups in a course:
```json
{
  "tool": "moodle_get_course_groups",
  "parameters": {
    "course_id": 2292,
    "format": "markdown"
  }
}
```

### Check activity group mode:
```json
{
  "tool": "moodle_get_activity_groupmode",
  "parameters": {
    "cmid": 456,
    "format": "markdown"
  }
}
```

---

## Total Tools

The server now has **38 tools** (previously 34):
- Site tools: 3
- Course tools: 7
- User tools: 5
- Grade tools: 6
- Assignment tools: 4
- Message tools: 3
- Calendar tools: 3
- Forum tools: 3
- **Group tools: 4** ✨ NEW
