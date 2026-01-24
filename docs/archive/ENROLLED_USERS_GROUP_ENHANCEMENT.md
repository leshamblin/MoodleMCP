# Enrolled Users Group Enhancement

**Date:** 2025-10-26
**Enhancement:** Added group membership support to `moodle_get_enrolled_users`

---

## Problem

User asked: **"how can I see which students are in what group in moodle?"**

### Investigation Findings

1. **`core_enrol_get_enrolled_users` API** returns extensive user data but **NO groups field** by default:
   - Returns: id, username, firstname, lastname, email, roles, preferences, enrolledcourses
   - Missing: group memberships

2. **`core_group_get_group_members` API** (which would directly solve this) is **NOT available** on the user's Moodle instance due to permission restrictions

3. **`core_group_get_course_user_groups` API** IS available and returns a user's groups in a course

---

## Solution

Enhanced `moodle_get_enrolled_users` to optionally include group memberships by:

1. Adding new parameter: `include_groups` (bool, default=False)
2. When `include_groups=True`, for each user:
   - Calls `core_group_get_course_user_groups` API
   - Adds `groups` array to user object
   - Displays group names in markdown output

---

## Implementation Details

### File Modified
**`src/moodle_mcp/tools/courses.py`** - `moodle_get_enrolled_users` function

### Changes Made

#### 1. New Parameter
```python
include_groups: bool = Field(default=False, description="Include group memberships for each user")
```

#### 2. Group Fetching Logic
```python
if include_groups:
    for user in users_page:
        try:
            groups_result = await moodle._make_request(
                'core_group_get_course_user_groups',
                {
                    'courseid': course_id,
                    'userid': user['id']
                }
            )
            user['groups'] = groups_result.get('groups', []) if groups_result else []
        except Exception:
            user['groups'] = []
```

#### 3. Updated Output
**Markdown format:**
```markdown
## 1. John Doe
- **ID:** 123
- **Email:** john@example.com
- **Groups:** Group A, Group B
```

**JSON format:**
```json
{
  "users": [
    {
      "id": 123,
      "fullname": "John Doe",
      "email": "john@example.com",
      "groups": [
        {"id": 1, "name": "Group A"},
        {"id": 2, "name": "Group B"}
      ]
    }
  ]
}
```

---

## Usage Examples

### Without Groups (Default - Fast)
```
"List enrolled users in course 2292"
"Who is enrolled in course 42?"
```

### With Groups (Slower - Makes N+1 API calls)
```
"List enrolled users in course 2292 with their groups"
"Show students in course 42 including group memberships"
```

---

## Performance Considerations

### Without `include_groups`:
- **API calls:** 1 (`core_enrol_get_enrolled_users`)
- **Speed:** Fast

### With `include_groups=True`:
- **API calls:** 1 + N (where N = number of users in page)
- **Speed:** Slower (N additional API calls)
- **Example:** 20 users = 21 total API calls

**Recommendation:** Use `include_groups=True` only when you specifically need group information, to avoid unnecessary API overhead.

---

## Benefits

1. **Direct Answer to User Question**
   - Can now see which students are in which groups
   - Single tool call instead of manual iteration

2. **Backward Compatible**
   - Default behavior unchanged (`include_groups=False`)
   - Existing queries work exactly as before

3. **Flexible**
   - Users can choose when to include group data
   - Balances performance vs. information needs

4. **Consistent with Existing Patterns**
   - Uses existing `core_group_get_course_user_groups` API
   - Follows error handling patterns
   - Supports both JSON and Markdown formats

---

## Documentation Updated

1. **README.md** - Updated tool description to note optional group memberships
2. **docs/GROUPS_TOOLS.md** - Added workflow for viewing students by group

---

## Testing

Verified with live Moodle instance:
```bash
✓ Default behavior (include_groups=False) - works as before
✓ With groups (include_groups=True) - successfully fetches and displays groups
✓ Users with no groups - displays "None"
✓ Error handling - gracefully handles group lookup failures
```

---

## Alternative Approaches Considered

### 1. Create separate tool `moodle_get_enrolled_users_with_groups`
- **Pros:** Clear separation of functionality
- **Cons:** Code duplication, more tools to maintain
- **Decision:** Rejected in favor of optional parameter

### 2. Always include groups (no parameter)
- **Pros:** Simpler interface
- **Cons:** Performance penalty for all calls (N+1 queries)
- **Decision:** Rejected due to performance impact

### 3. Create aggregation tool that returns "Group → Students" view
- **Pros:** Directly answers "which students in which group"
- **Cons:** Different data structure, additional tool
- **Decision:** Could still implement as separate tool if needed

---

## Future Enhancements

If the user's Moodle instance ever enables `core_group_get_group_members`, we could:

1. Create `moodle_get_group_members` tool for direct "Group → Students" lookup
2. Create `moodle_list_groups_with_members` aggregation tool
3. Optimize `include_groups` to use batch API if available

---

## Summary

✅ **User can now see which students are in which groups**

**Before:**
- Had to manually query each user's groups
- Required multiple tool calls
- No direct way to see student-group relationships

**After:**
- Single tool call with `include_groups=true`
- Automatic group membership lookup
- Clean display in both Markdown and JSON formats

**Example query:**
```
"Show me all students in course 2292 with their group memberships"
```

Returns formatted list showing each student and their groups (or "None" if not in any groups).

---

**Enhancement Status:** ✅ Complete and tested
