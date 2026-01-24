# Write Operations Safety Configuration

**Date:** 2025-10-26
**Feature:** Course-based write operation whitelist for safe development
**Status:** ✅ Implemented and tested

---

## Overview

The Moodle MCP server now supports **WRITE operations** (create, update, delete) with multiple layers of safety:

1. **Environment-based control** (DEV vs PROD)
2. **Course whitelist** (only specific courses in DEV)
3. **Decorator-based enforcement** (automatic blocking)
4. **Production lockdown** (all writes disabled by default)

---

## Safety Guarantees

### ✅ Development Mode (Default)

**ONLY Course ID 7299 allows writes**

- Course: **Elizabeth's Moodle Playground**
- All other courses: **BLOCKED**
- Configurable via `MOODLE_DEV_COURSE_WHITELIST`

### ✅ Production Mode

**ALL writes are DISABLED**

- No course allows writes (default)
- Must explicitly enable with `MOODLE_PROD_ALLOW_WRITES=true`
- **NEVER enable this unless absolutely necessary!**

---

## Configuration

### Environment Variables

```bash
# DEV: Whitelist of course IDs that allow writes
# Comma-separated list
MOODLE_DEV_COURSE_WHITELIST=7299

# PROD: Allow writes in production (default: false)
# WARNING: Keep false!
MOODLE_PROD_ALLOW_WRITES=false
```

### Multiple Courses (DEV only)

To allow writes to multiple courses in DEV:

```bash
MOODLE_DEV_COURSE_WHITELIST=7299,8001,9543
```

---

## Usage for Tool Development

### Implementing a Write Tool

```python
from pydantic import Field
from fastmcp import Context
from ..server import mcp
from ..utils.error_handling import handle_moodle_errors, require_write_permission
from ..utils.api_helpers import get_moodle_client

@mcp.tool(
    name="moodle_create_forum_post",
    description="Create a new forum post. WRITE OPERATION - only works on whitelisted courses.",
    annotations={
        "readOnlyHint": False,  # This is a WRITE operation
        "destructiveHint": True,
        "idempotentHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')  # ← SAFETY: Enforces whitelist
async def moodle_create_forum_post(
    course_id: int = Field(description="Course ID", gt=0),
    forum_id: int = Field(description="Forum ID", gt=0),
    subject: str = Field(description="Post subject"),
    message: str = Field(description="Post message"),
    ctx: Context = None
) -> str:
    """
    Create a new forum post.

    SAFETY: This write operation is only allowed on whitelisted courses.
    Default whitelist: [7299] (Elizabeth's Moodle Playground)

    Args:
        course_id: Course ID (must be in whitelist!)
        forum_id: Forum ID
        subject: Post subject
        message: Post message
        ctx: FastMCP context

    Returns:
        Confirmation message with post ID

    Raises:
        WriteOperationError: If course_id is not whitelisted
    """
    moodle = get_moodle_client(ctx)

    # If we get here, the course is whitelisted!
    result = await moodle._make_request(
        'mod_forum_add_discussion',
        {
            'forumid': forum_id,
            'subject': subject,
            'message': message
        }
    )

    return f"✅ Created forum post (ID: {result.get('discussionid')})"
```

### Key Points

1. **Use `@require_write_permission('course_id')`** decorator
2. **Place AFTER `@handle_moodle_errors`** (order matters!)
3. **Set `readOnlyHint: False`** in annotations
4. **Set `destructiveHint: True`** if it modifies data
5. **Document in docstring** that it's a write operation

---

## How the Safety Works

### Decorator Chain

```python
@mcp.tool()                           # 1. Registers tool
@handle_moodle_errors                 # 2. Catches all errors
@require_write_permission('course_id') # 3. Checks whitelist BEFORE execution
async def my_write_tool(course_id: int, ctx: Context = None):
    # This code only runs if course_id is whitelisted
    ...
```

### Safety Flow

```
User calls tool with course_id=12544
    ↓
@require_write_permission extracts course_id
    ↓
Checks config.can_write_to_course(12544)
    ↓
DEV mode: Is 12544 in [7299]? → NO
    ↓
Raises WriteOperationError
    ↓
@handle_moodle_errors catches it
    ↓
Returns user-friendly error message
    ↓
Tool function NEVER executes ✅
```

---

## Test Results

### DEV Mode Tests

```
Course 7299 (Elizabeth's Moodle Playground):  ✅ ALLOWED
Course 13043 (MBA 525 Development):          ❌ BLOCKED
Course 12544 (Cherie's Project Space):       ❌ BLOCKED
```

### PROD Mode Tests

```
Course 7299 (even though whitelisted in DEV): ❌ BLOCKED
ALL courses:                                   ❌ BLOCKED
```

---

## Error Messages

### DEV Mode - Non-Whitelisted Course

```
Write operation blocked for safety:

Write operations are only allowed on whitelisted courses in DEV mode.
Attempted: Course 13043
Allowed: [7299]
To allow writes to this course, add it to MOODLE_DEV_COURSE_WHITELIST
```

### PROD Mode - All Writes Disabled

```
Write operation blocked for safety:

Write operations are DISABLED in PRODUCTION mode.
Attempted: Course 7299
Safety: prod_allow_writes=False
```

---

## Adding More Courses to Whitelist

### Temporary (Current Session)

```bash
export MOODLE_DEV_COURSE_WHITELIST=7299,8001,9543
python -m moodle_mcp.main
```

### Permanent (Update .env)

```bash
# Edit .env
MOODLE_DEV_COURSE_WHITELIST=7299,8001,9543
```

### Via Claude Desktop Config

```json
{
  "mcpServers": {
    "moodle": {
      "command": "uv",
      "args": [...],
      "env": {
        "PYTHONPATH": "...",
        "MOODLE_DEV_COURSE_WHITELIST": "7299,8001,9543"
      }
    }
  }
}
```

---

## Available Write Operations (Planned)

### Forum Tools
- ✏️ `moodle_create_forum_post` - Create forum discussion
- ✏️ `moodle_reply_to_post` - Reply to forum post
- 🗑️ `moodle_delete_forum_post` - Delete own post

### Message Tools
- ✏️ `moodle_send_message` - Send message to user
- 🗑️ `moodle_delete_conversation` - Delete conversation

### Calendar Tools
- ✏️ `moodle_create_event` - Create calendar event
- ✏️ `moodle_update_event` - Update event
- 🗑️ `moodle_delete_event` - Delete event

### Assignment Tools (Teacher only)
- ✏️ `moodle_grade_submission` - Grade student submission
- ✏️ `moodle_add_feedback` - Add feedback

**Note:** These are examples. Actual implementation depends on available Moodle API functions and permissions.

---

## Best Practices

### ✅ DO

1. **Always use the decorator** `@require_write_permission('course_id')`
2. **Test on course 7299** before implementing
3. **Document that it's a write operation** in tool description
4. **Use descriptive error messages** when operations fail
5. **Keep PROD writes disabled** unless absolutely necessary

### ❌ DON'T

1. **Don't bypass the decorator** - it's there for safety
2. **Don't add production courses** to DEV whitelist
3. **Don't enable PROD writes** without explicit user approval
4. **Don't assume course ID** - always require it as parameter
5. **Don't modify READ tools** to add write operations

---

## Troubleshooting

### "Write operation blocked for safety"

**Cause:** Course not in whitelist

**Solution:**
```bash
# Check current whitelist
grep MOODLE_DEV_COURSE_WHITELIST .env

# Add your course
MOODLE_DEV_COURSE_WHITELIST=7299,YOUR_COURSE_ID
```

### "Write operation requires 'course_id' parameter"

**Cause:** Tool missing `course_id` parameter or using different name

**Solution:** Ensure tool has `course_id` parameter, or specify different param name:
```python
@require_write_permission('courseid')  # If using different parameter name
```

### "Configuration not available in context"

**Cause:** `ctx` parameter missing or not passed

**Solution:** Add `ctx: Context = None` to function signature

---

## Security Considerations

### Why Whitelist?

1. **Prevents accidents** - Can't accidentally modify production courses
2. **Limits blast radius** - Even if something goes wrong, only affects test course
3. **Clear intent** - Explicit list of "okay to modify" courses
4. **Easy to audit** - One place to check what's allowed

### Defense in Depth

Multiple layers of protection:

1. **Environment check** (DEV vs PROD)
2. **Whitelist check** (course ID)
3. **Decorator enforcement** (automatic)
4. **Error handling** (prevents execution)
5. **Logging** (tracks attempts)

### Audit Trail

All write attempts are logged with:
- Attempted course ID
- Whether allowed or blocked
- Environment (DEV/PROD)
- Current whitelist

---

## Current Whitelist

**Development:** Course 7299 only

- **Course Name:** Elizabeth's Moodle Playground
- **Short Name:** MoodlePlayground
- **Course ID:** 7299
- **Purpose:** Safe testing ground for write operations

**Production:** No courses (all writes disabled)

---

## Future Enhancements

### Possible Additions

1. **User-based whitelist** - Only certain users can write
2. **Time-based restrictions** - Only allow writes during certain hours
3. **Rate limiting** - Prevent spam/abuse
4. **Approval workflow** - Require confirmation for destructive operations
5. **Rollback capability** - Undo recent writes

---

## Summary

✅ **Write operations are SAFE**

- DEV: Only course 7299 allows writes
- PROD: ALL writes blocked
- Automatic enforcement via decorator
- Clear error messages
- Easy to configure

✅ **Ready for development work**

You can now safely implement write operations knowing they will ONLY affect course 7299 unless explicitly configured otherwise.

---

**Status:** ✅ Fully Implemented and Tested
**Safety Level:** ✅ MAXIMUM
**Ready for:** ✅ Write Tool Development

