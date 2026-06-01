# Claude Instructions for Moodle MCP Server Project

## Project Context

This is the **Moodle MCP Server** - a comprehensive Model Context Protocol server for Moodle LMS integration with enterprise-grade safety features.

### Key Facts
- **Location:** `/Users/wjs/Documents/Programming/MoodleMCP`
- **Status:** Production-ready with 70 tools (42 READ + 28 WRITE)
- **Coverage:** 28% of Moodle Web Services API (167 total functions available)
- **Primary User:** Elizabeth Shamblin (leshamb2@ncsu.edu)
- **Development Course:** Course 7299 "Elizabeth's Moodle Playground"

### Critical Safety Information

**WRITE OPERATIONS ARE PROTECTED:**
- Default whitelist: **ONLY course 7299** allows write operations in DEV
- Production: **ALL writes BLOCKED** by default
- Decorator: `@require_write_permission('course_id')` enforces automatically
- DO NOT bypass safety mechanisms

### Current Implementation

**70 Tools (42 READ + 28 WRITE)** across 14 modules: site, courses, users,
grades, assignments, quiz, calendar, messages, forums, groups, enrollment,
completion, badges, dashboard. Several overlapping readers were consolidated
(e.g. one `moodle_get_grades` and one `moodle_get_calendar_events` replace
several older per-view tools), so per-category counts drift — list the live
set instead of trusting a static table:

```bash
PYTHONPATH=src python -c "
import asyncio, moodle_mcp.main
from moodle_mcp.server import mcp
async def main():
    for t in sorted(await mcp.list_tools(), key=lambda x: x.name):
        print(sorted(t.tags), t.name)
asyncio.run(main())
"
```

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
├── core/
│   └── resolvers.py       # MoodleResolver: names/emails/shortnames -> ids
├── models/
│   └── results.py         # shared @dataclass return models
├── tools/                 # Tool implementations (14 files)
│   ├── site.py  courses.py  users.py  grades.py  assignments.py
│   ├── quiz.py  calendar.py  messages.py  forums.py  groups.py
│   └── enrollment.py  completion.py  badges.py  dashboard.py
└── utils/
    ├── formatting.py      # truncate + timestamp helpers
    ├── error_handling.py  # error decorator + write-safety decorators
    └── api_helpers.py     # get_moodle_client / get_resolver
```

### Adding New Tools

Tools use the FastMCP 3.x idiom: `Annotated[...]` params (no `Field`
defaults), `ToolAnnotations`, `tags={...}`, `moodle.call(...)`, the resolver
for human-friendly refs, and a `@dataclass` return (FastMCP emits both text and
`structuredContent`). The `description=` is the single source of truth for what
the agent sees — keep it complete and example-rich.

**READ-only tool pattern:**
```python
from typing import Annotated
from mcp.types import ToolAnnotations

@dataclass
class MyResult:
    id: int
    name: str | None = None

@mcp.tool(
    name="moodle_my_tool",
    description="Clear description with an example call.",
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_my_tool(
    course: Annotated[int | str, Field(description="Course id/shortname/name")],
    ctx: Context = None,
) -> MyResult:
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    cid = await resolver.course_id(course)
    data = await moodle.call("some_moodle_function", {"courseid": cid})
    return MyResult(id=data.get("id", 0), name=data.get("name"))
```

**WRITE operation pattern:**
```python
@mcp.tool(
    name="moodle_create_something",
    description="WRITE: ... only works on whitelisted courses (7299 in DEV).",
    tags={"write", "course"},  # add "destructive" if it deletes
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False,
        idempotentHint=False, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission("course")  # CRITICAL. Course-less writes:
                                     # @require_global_write_permission
async def moodle_create_something(
    course: Annotated[int | str, Field(description="Course (must be whitelisted)")],
    name: Annotated[str, Field(description="Name", min_length=1)],
    ctx: Context = None,
) -> WriteResult:
    moodle = get_moodle_client(ctx)
    cid = await get_resolver(ctx).course_id(course)
    result = await moodle.call("api_function", {"courseid": cid, "name": name})
    return WriteResult(operation="create_something", details={"id": result.get("id")})
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

**Done:**
1. ✅ FastMCP 3.x migration; resolver layer (names/emails/shortnames -> ids)
2. ✅ Phase 1 writes implemented (Quiz, Enrollment, Assignment submissions, Grading)
3. ✅ Consolidated overlapping readers (70 tools: 42 READ + 28 WRITE)
4. ✅ Offline (respx) + live (course 7299) test suites; comprehensive read smoke test
5. ✅ Security hardening: token in POST body, all writes gated, PROD lockdown fails closed

**Goal:** Complete coverage of critical student/teacher workflows (Quiz taking, Assignment submission, Enrollment management) — core paths now in place.

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
