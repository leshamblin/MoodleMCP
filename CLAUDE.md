# Claude Instructions for Moodle MCP Server Project

## Project Context

This is the **Moodle MCP Server** - a comprehensive Model Context Protocol server for Moodle LMS integration with enterprise-grade safety features.

### Key Facts
- **Location:** `/Users/wjs/Programming/MoodleAPI`
- **Status:** Production-ready with 70 tools
- **Primary User:** Elizabeth Shamblin (leshamb2@ncsu.edu)
- **Development Course:** Course 7299 "Elizabeth's Moodle Playground"

### Critical Safety Information

**WRITE OPERATIONS ARE PROTECTED:**
- Default whitelist: **ONLY course 7299** allows write operations in DEV
- Production: **ALL writes BLOCKED** by default (`MOODLE_PROD_ALLOW_WRITES=false`)
- Decorator: `@require_write_permission('course_id')` enforces automatically on
  course-scoped writes
- DO NOT bypass safety mechanisms

**Capability boundary at the Moodle role level (NOT enforceable by this MCP):**
The WS token's role does NOT grant the following, regardless of whitelist:
user create/update/delete, course create/update/delete/duplicate, course-category
mgmt, manual enrol/unenrol, group create/delete, group-member add/remove,
gradebook updates via `core_grades_update_grades`, completion override.
Tools wrapping these were removed in favor of working alternatives (e.g., grade
via `mod_assign_save_grade` instead of `core_grades_update_grades`).

### Tool inventory (70 total)

Working write surface (course-scoped, whitelist-gated):
- **Assignments**: save_grade, save_grades-batch, save_submission, submit_for_grading,
  lock/unlock submissions, revert to draft
- **Forums**: add_discussion, add_post (reply), delete_post, set_subscription
- **Calendar**: create_event, delete_event
- **Quiz** (student-side): start_attempt, save_answers, submit
- **Grades**: create_grade_category
- **Completion**: mark self-completed (course), update activity completion

Working write surface (user-scoped, no whitelist):
- **Messages**: send_message, delete_message, delete_conversation,
  mark_notifications_read

Read tools cover all major surfaces (site, courses, users, grades, assignments,
messages, calendar, forums, groups, quiz, completion, badges).

### Environment Setup

**Two Moodle Instances:**
- **DEV:** `https://moodle-projects.wolfware.ncsu.edu` (default)
- **PROD:** `https://moodle-courses2527.wolfware.ncsu.edu`

**Environment Variables** (in `.env`):
```bash
MOODLE_DEV_URL=https://moodle-projects.wolfware.ncsu.edu
MOODLE_DEV_TOKEN=[token_here]
MOODLE_PROD_URL=https://moodle-courses2527.wolfware.ncsu.edu
MOODLE_PROD_TOKEN=[token_here]
MOODLE_ENV=dev  # or 'prod'
MOODLE_DEV_COURSE_WHITELIST=7299  # Write safety
MOODLE_PROD_ALLOW_WRITES=false    # Keep false!
```

**Switch environments:**
```bash
# Use DEV (default)
python -m moodle_mcp.main

# Use PROD
MOODLE_ENV=prod python -m moodle_mcp.main
```

### Code Architecture

**Core Structure:**
```
src/moodle_mcp/
├── server.py              # FastMCP instance
├── main.py                # Entry point with lifespan
├── core/
│   ├── client.py          # Async Moodle API client
│   ├── config.py          # Configuration with write safety
│   └── exceptions.py      # Custom exceptions
├── tools/                 # Tool implementations (9 files)
│   ├── site.py
│   ├── courses.py
│   ├── users.py
│   ├── grades.py
│   ├── assignments.py
│   ├── messages.py        # READ + WRITE
│   ├── calendar.py        # READ + WRITE
│   ├── forums.py          # READ + WRITE
│   └── groups.py
└── utils/
    ├── formatting.py      # Response formatters
    ├── error_handling.py  # Error decorator + write safety
    └── api_helpers.py     # Helper functions
```

### Adding New Tools

**READ-only tool pattern:**
```python
@mcp.tool(
    name="moodle_my_tool",
    description="Clear description with examples",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_my_tool(
    param: int = Field(description="Parameter", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN),
    ctx: Context = None
) -> str:
    moodle = get_moodle_client(ctx)
    data = await moodle._make_request('moodle_api_function', {})
    return format_response(data, "Title", format)
```

**WRITE operation pattern:**
```python
@mcp.tool(
    name="moodle_create_something",
    description="WRITE OPERATION - only works on whitelisted courses",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,  # True if deletes
        "idempotentHint": False,
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')  # CRITICAL: Add this!
async def moodle_create_something(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    name: str = Field(description="Name", min_length=1),
    ctx: Context = None
) -> str:
    moodle = get_moodle_client(ctx)
    result = await moodle._make_request('api_function', {'name': name})
    return f"✅ Created successfully: {result.get('id')}"
```

### Testing

**Run server:**
```bash
# Development with UI
fastmcp dev src/moodle_mcp/main.py

# Production mode
MOODLE_ENV=prod fastmcp dev src/moodle_mcp/main.py

# Direct execution
PYTHONPATH=src python -m moodle_mcp.main
```

**Run tests:**
```bash
# All tests
PYTHONPATH=src pytest tests/

# Specific test
PYTHONPATH=src pytest tests/test_tools_integration.py -v
```

### Priority Roadmap

**Phase 1 - CRITICAL (In Progress):**
- [ ] Quiz functions (get_quizzes, start_attempt, save_attempt, process_attempt)
- [ ] Enrollment (enrol_manual_enrol_users, enrol_manual_unenrol_users)
- [ ] Assignment submissions (save_submission, submit_for_grading)
- [ ] Grading (save_grade, update_grades)

**Phase 2 - IMPORTANT:**
- [ ] Completion tracking
- [ ] Group management (add/remove members)
- [ ] Forum enhancements (subscribe, edit, delete)

**Phase 3 - NICE-TO-HAVE:**
- [ ] Glossary, Wiki, Lesson modules
- [ ] Admin functions (if needed)

### Documentation Files

**Key Reference Documents:**
- **TASKS.md** - Complete inventory of 167 Moodle functions, priority roadmap
- **README.md** - User-facing documentation
- **WRITE_OPERATIONS_SAFETY.md** - Comprehensive write safety guide
- **WRITE_SAFETY_SUMMARY.md** - Quick reference for developers

### Common Commands

```bash
# Check server starts
PYTHONPATH=src python -c "
import asyncio
from moodle_mcp.main import lifespan
from moodle_mcp.server import mcp

async def test():
    async with lifespan(mcp):
        tools = list(mcp._tool_manager._tools.keys())
        print(f'✅ {len(tools)} tools registered')

asyncio.run(test())
"

# List all tools
PYTHONPATH=src python -c "
from moodle_mcp.server import mcp
for name in sorted(mcp._tool_manager._tools.keys()):
    print(name)
"

# Git workflow
git status
git add [files]
git commit -m "feat: description"
git log --oneline -5
```

### Important Constraints

1. **NEVER** bypass `@require_write_permission` decorator for write operations
2. **ALWAYS** test write operations on course 7299 first
3. **NEVER** enable `MOODLE_PROD_ALLOW_WRITES=true` without explicit user approval
4. **ALWAYS** use `@handle_moodle_errors` for consistent error handling
5. **ALWAYS** validate inputs with Pydantic Field constraints
6. **PREFER** editing existing files over creating new ones
7. **NEVER** commit tokens or credentials

### Current Work Focus

**Next Immediate Tasks:**
1. ✅ README.md updated
2. ✅ CLAUDE.md created
3. ⏳ Comprehensive tests for all 46 tools
4. ⏳ Phase 1 implementation (Quiz, Enrollment, Assignment submissions)

**Goal:** Complete coverage of critical student/teacher workflows (Quiz taking, Assignment submission, Enrollment management).

### Quick Reference

**Test write safety:**
```python
# This should work (course 7299)
await moodle_create_forum_discussion(
    course_id=7299,
    forum_id=123,
    subject="Test",
    message="Test message",
    ctx=ctx
)

# This should BLOCK (course not whitelisted)
await moodle_create_forum_discussion(
    course_id=13043,  # Not in whitelist
    forum_id=123,
    subject="Test",
    message="Test",
    ctx=ctx
)  # Raises WriteOperationError
```

**Add course to whitelist:**
```bash
# In .env
MOODLE_DEV_COURSE_WHITELIST=7299,8001,9543
```

---

**Remember:** This is a production system with real data. Write operations must be carefully controlled and tested on course 7299 before any broader deployment.
