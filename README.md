# Moodle MCP Server

A comprehensive Model Context Protocol (MCP) server for Moodle LMS integration with **70 tools** including both READ and WRITE operations with enterprise-grade safety features.

## 🚀 Quick Start

**New to this project?** Get started in 5 minutes:

1. **[Read QUICKSTART.md](QUICKSTART.md)** - Complete setup guide
2. **Get your Moodle token** - User menu → Preferences → Security keys
3. **Install & configure** - Follow the guide
4. **Test with Claude** - Ask: "What is my Moodle user information?"

**Deploying to a team?** See [DEPLOYMENT.md](DEPLOYMENT.md) for 5-20 person deployment.

### Platform-specific setup

- **Mac users:** [Mac_Cheat_Sheet.md](Mac_Cheat_Sheet.md)
- **Windows users:** [Windows_Cheat_Sheet.md](Windows_Cheat_Sheet.md)
- **Gemini CLI:** [Gemini_CLI_Setup_Guide.md](Gemini_CLI_Setup_Guide.md)
- **Faculty download/setup guide:** [Moodle_MCP_Download_Guide.html](Moodle_MCP_Download_Guide.html) (also served at `docs/index.html` via GitHub Pages)
- **End-user instruction guide:** [Moodle_MCP_User_Guide.html](Moodle_MCP_User_Guide.html)

## 🎯 Overview

**Current Status:** 70 tools (48 READ + 22 WRITE) across 12 categories.

This MCP server provides safe, production-ready access to Moodle's Learning Management System through a modern async Python implementation with comprehensive safety controls for write operations.

> **Note on capability boundaries:** Some Moodle WS functions (user/course CRUD, manual enrol, gradebook overrides via `core_grades_update_grades`, group create/delete) are denied by the WS role at the Moodle layer regardless of MCP whitelist. Tools wrapping those functions were removed in favor of working alternatives (e.g., grade via `mod_assign_save_grade` instead of `core_grades_update_grades`).

## ✨ Features

- **70 comprehensive tools** across 12 categories (48 READ + 22 WRITE)
- **Write operation safety** with course whitelisting and environment-based controls
- **Async/await architecture** for high performance
- **Connection pooling** for efficient API usage
- **Comprehensive error handling** with actionable messages
- **Pagination support** for large datasets
- **Multiple output formats** (Markdown and JSON)
- **Type-safe** with Pydantic validation
- **DEV/PROD separation** with production lockdown
- **Character limit enforcement** to prevent overwhelming responses

## 📊 Tool Categories

Legend: ✏️ = course-scoped write (whitelist-gated) · 🗑️ = destructive · 👤 = user-scoped write (no whitelist)

### 🔧 Site (3 tools - READ only)
- `moodle_get_site_info` - Site metadata and user information
- `moodle_test_connection` - Verify API connectivity
- `moodle_get_available_functions` - List enabled API functions

### 📚 Courses (7 tools - READ only)
- `moodle_list_user_courses` - Enrolled courses for user
- `moodle_get_course_details` - Detailed course information
- `moodle_search_courses` - Search courses by name/category
- `moodle_get_course_contents` - Course structure and modules
- `moodle_get_enrolled_users` - Users enrolled in course (with groups)
- `moodle_get_course_categories` - Course category list
- `moodle_get_recent_courses` - Recently accessed courses

### 👥 Users (5 tools - READ only)
- `moodle_get_current_user` - Current user profile
- `moodle_get_user_profile` - User profile by ID
- `moodle_search_users` - Search users by criteria
- `moodle_get_user_preferences` - User preferences/settings
- `moodle_get_course_participants` - Course participants with roles

### 📊 Grades (8 tools: 6 READ + 2 WRITE)
**READ:**
- `moodle_get_user_grades` - All grades for user
- `moodle_get_course_grades` - Course gradebook
- `moodle_get_grade_items` - Grade items for course
- `moodle_get_student_grade_summary` - Student grade summary
- `moodle_get_gradebook_overview` - Grade overview across courses
- `moodle_get_grade_report` - Detailed grade report

**WRITE:**
- `moodle_save_assignment_grade` ✏️ - Grade an assignment submission
- `moodle_create_grade_category` ✏️ - Create a gradebook category

### 📝 Assignments (10 tools: 5 READ + 5 WRITE)
**READ:**
- `moodle_list_assignments` - Assignments in course
- `moodle_get_assignment_details` - Assignment details
- `moodle_get_assignment_submissions` - Assignment submissions
- `moodle_get_user_assignments` - All user assignments
- `moodle_get_submission_status` - Check submission status and capabilities

**WRITE:**
- `moodle_save_assignment_submission` ✏️ - Save assignment draft
- `moodle_submit_assignment` ✏️🗑️ - Final submit for grading
- `moodle_lock_assignment_submissions` ✏️ - Lock submissions to prevent edits
- `moodle_unlock_assignment_submissions` ✏️ - Unlock previously-locked submissions
- `moodle_revert_submissions_to_draft` ✏️ - Revert submitted work to draft for resubmission

### 💬 Messages (7 tools: 3 READ + 4 WRITE)
**READ:**
- `moodle_get_conversations` - Message conversations
- `moodle_get_messages` - Messages from conversation
- `moodle_get_unread_count` - Unread message count

**WRITE (user-scoped, no whitelist):**
- `moodle_send_message` 👤 - Send private message to user
- `moodle_delete_conversation` 👤🗑️ - Delete a conversation
- `moodle_delete_message` 👤🗑️ - Delete a single message
- `moodle_mark_notifications_read` 👤 - Mark all notifications read

### 📅 Calendar (5 tools: 3 READ + 2 WRITE)
**READ:**
- `moodle_get_calendar_events` - Events for date range
- `moodle_get_upcoming_events` - Upcoming deadlines
- `moodle_get_course_events` - Events for specific course

**WRITE:**
- `moodle_create_calendar_event` ✏️ - Create course calendar event
- `moodle_delete_calendar_event` ✏️🗑️ - Delete calendar event

### 💭 Forums (7 tools: 3 READ + 4 WRITE)
**READ:**
- `moodle_get_forum_discussions` - Forum discussions in course
- `moodle_get_discussion_posts` - Posts in discussion
- `moodle_search_forums` - Search forum content

**WRITE:**
- `moodle_create_forum_discussion` ✏️ - Create new discussion
- `moodle_add_forum_post` ✏️ - Reply to discussion post
- `moodle_delete_forum_post` ✏️🗑️ - Delete a forum post (deletes discussion if root post)
- `moodle_set_forum_subscription` ✏️ - Subscribe/unsubscribe self from a forum

### 👥 Groups (7 tools - READ only)
- `moodle_get_course_groups` - All groups in a course
- `moodle_get_course_groupings` - All groupings in a course
- `moodle_get_course_user_groups` - Groups a user belongs to
- `moodle_get_activity_allowed_groups` - Groups with access to activity
- `moodle_get_activity_groupmode` - Group mode for activity
- `moodle_get_groups_for_selector` - Groups available for a selector
- `moodle_get_group_members` - List members of a specific group

> Group create/delete and member add/remove are not supported — the Moodle WS role denies these capabilities.

### 📝 Quizzes (5 tools: 2 READ + 3 WRITE)
**READ:**
- `moodle_get_quizzes` - List all quizzes in a course
- `moodle_get_quiz_attempts` - Get user's quiz attempts and grades

**WRITE (student-side):**
- `moodle_start_quiz_attempt` ✏️ - Start new quiz attempt
- `moodle_save_quiz_answers` ✏️ - Auto-save quiz answers during attempt
- `moodle_submit_quiz` ✏️🗑️ - Final submit quiz for grading

### ✅ Completion Tracking (4 tools: 2 READ + 2 WRITE)
**READ:**
- `moodle_get_activities_completion_status` - Completion status for all activities in a course
- `moodle_get_course_completion_status` - Overall course completion status and criteria

**WRITE:**
- `moodle_mark_course_self_completed` ✏️ - Student marks course as self-completed
- `moodle_update_activity_completion_status_manually` ✏️ - Manually update activity completion status

### 🏆 Badges (2 tools - READ only)
- `moodle_get_user_badges` - Get all badges earned by a user with filtering
- `moodle_get_user_badge_by_hash` - Get detailed badge information by unique hash

## 🔒 Write Operation Safety

### Multi-Layer Protection

**All write operations** (create, update, delete) are protected by a comprehensive safety system:

#### 1. Course Whitelist (DEV mode)
- Default: **Only course 7299** (Elizabeth's Moodle Playground) allows writes
- Configurable via `MOODLE_DEV_COURSE_WHITELIST` environment variable
- Example: `MOODLE_DEV_COURSE_WHITELIST=7299,8001,9543`

#### 2. Production Lockdown
- **ALL write operations blocked** in production by default
- Requires explicit `MOODLE_PROD_ALLOW_WRITES=true` to enable
- **Recommendation:** Keep false unless absolutely necessary

#### 3. Automatic Enforcement
- `@require_write_permission` decorator validates all course-based writes
- Executes **before** any API call is made
- Clear, actionable error messages when blocked

#### 4. Tool Annotations
- All tools properly annotated:
  - `readOnlyHint: False` for write operations
  - `destructiveHint: True` for delete operations
  - Clear documentation of safety requirements

### Example Error Messages

```
Write operation blocked for safety:

Write operations are only allowed on whitelisted courses in DEV mode.
Attempted: Course 13043
Allowed: [7299]
To allow writes to this course, add it to MOODLE_DEV_COURSE_WHITELIST
```

### Non-Course Write Operations

Message tools (send, delete) are **user-to-user** operations and don't require course whitelist, but are still logged and validated.

## 📦 Installation

**👉 For first-time setup, see [QUICKSTART.md](QUICKSTART.md) for detailed instructions.**

### Prerequisites

- Python 3.11 or higher
- Moodle instance with Web Services enabled
- Valid Moodle Web Services token
- Claude Desktop app

### Quick Install

1. **Clone and install:**
   ```bash
   git clone https://github.com/yourusername/MoodleAPI.git
   cd MoodleAPI

   # Install uv (if needed)
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Install dependencies
   uv sync

   # Or with pip
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your Moodle URLs and tokens
   ```

3. **Required environment variables:**
   ```bash
   # Development instance (default)
   MOODLE_DEV_URL=https://moodle-dev.example.com
   MOODLE_DEV_TOKEN=your_dev_token_here

   # Production instance
   MOODLE_PROD_URL=https://moodle.example.com
   MOODLE_PROD_TOKEN=your_prod_token_here

   # Environment selection (default: dev)
   MOODLE_ENV=dev  # or 'prod'

   # Write operation safety
   MOODLE_DEV_COURSE_WHITELIST=7299  # Comma-separated course IDs
   MOODLE_PROD_ALLOW_WRITES=false    # Keep false!
   ```

4. **Configure Claude Desktop:**

   See [QUICKSTART.md](QUICKSTART.md) for platform-specific config file locations and complete setup instructions.

## 🔑 Getting Your Moodle Token

1. Log in to Moodle
2. Navigate to: **User menu (top right) > Preferences > Security keys**
3. Click "Create token" and give it a name (e.g., "Claude MCP")
4. Copy the token to your `.env` file

For detailed instructions with screenshots, see [QUICKSTART.md](QUICKSTART.md)

## 🚀 Usage

### Running the Server

**Development mode (DEV instance with inspection UI):**
```bash
fastmcp dev src/moodle_mcp/main.py
```

**Production mode (PROD instance):**
```bash
MOODLE_ENV=prod fastmcp dev src/moodle_mcp/main.py
```

**Direct execution:**
```bash
python -m moodle_mcp.main
```

### Integration with Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "moodle": {
      "command": "uv",
      "args": ["--directory", "/path/to/MoodleAPI", "run", "moodle-mcp"],
      "env": {
        "PYTHONPATH": "/path/to/MoodleAPI/src"
      }
    }
  }
}
```

Or using python directly:

```json
{
  "mcpServers": {
    "moodle": {
      "command": "python",
      "args": ["-m", "moodle_mcp.main"],
      "env": {
        "PYTHONPATH": "/path/to/MoodleAPI/src",
        "MOODLE_DEV_URL": "https://moodle-dev.example.com",
        "MOODLE_DEV_TOKEN": "your_token",
        "MOODLE_DEV_COURSE_WHITELIST": "7299"
      }
    }
  }
}
```

## 📖 Response Formats

### Markdown (Default)
Human-readable, token-efficient format optimized for LLMs:
```markdown
# Course List

**Total items:** 3

## 1. Introduction to Python
- **ID:** 42
- **Category:** Computer Science
- **Start Date:** 2024-01-15
```

### JSON
Machine-readable format for programmatic processing:
```json
{
  "courses": [
    {
      "id": 42,
      "fullname": "Introduction to Python",
      "category": "Computer Science",
      "startdate": 1705276800
    }
  ]
}
```

## 📄 Pagination

All list tools support pagination:
- **limit** - Maximum items to return (default: 20, max: 100)
- **offset** - Starting position for results

Example:
```python
# Get first 20 courses
moodle_list_user_courses(limit=20)

# Get next 20 courses
moodle_list_user_courses(limit=20, offset=20)
```

## ⚠️ Error Handling

Clear, actionable error messages:

```
Authentication failed: Invalid token

Please verify:
1. MOODLE_TOKEN is correct and not expired
2. Token has required web service permissions
3. Web services are enabled on the Moodle site
```

## 🏗️ Architecture

### Core Components

- **server.py** - Central FastMCP instance
- **main.py** - Entry point with lifespan management
- **core/client.py** - Async Moodle API client with connection pooling
- **core/config.py** - Pydantic configuration with write safety
- **core/exceptions.py** - Custom exception hierarchy

### Shared Utilities

- **utils/formatting.py** - JSON/Markdown response formatters
- **utils/error_handling.py** - Error decorator + write safety decorator
- **utils/api_helpers.py** - API utility functions

### Tools Organization

```
src/moodle_mcp/tools/
├── site.py           # Site information
├── courses.py        # Course management
├── users.py          # User profiles
├── grades.py         # Gradebook
├── assignments.py    # Assignments
├── messages.py       # Messaging (READ + WRITE)
├── calendar.py       # Calendar (READ + WRITE)
├── forums.py         # Forums (READ + WRITE)
└── groups.py         # Group management
```

## 🔐 Security

- **Token-based authentication** - Secure API access
- **Write operation safeguards** - Course whitelist + production lockdown
- **Error masking** - Internal errors hidden from clients
- **Input validation** - All inputs validated with Pydantic
- **Connection pooling** - Efficient resource usage
- **Environment separation** - DEV/PROD isolation

## ⚡ Performance

- **Async architecture** - Non-blocking I/O operations
- **Connection pooling** - Reusable HTTP connections (20 keepalive, 100 max)
- **Pagination** - Efficient handling of large datasets
- **Character limits** - Responses truncated at 50,000 characters
- **Caching** - Connection pool reduces API overhead

## 📈 Coverage & Roadmap

**Current Coverage:** 58 tools = **35% of Moodle Web Services API**

See [TASKS.md](./TASKS.md) for complete function inventory and implementation roadmap.

### ✅ Phase 1 Complete (High Priority):
- ✅ **Quiz Functions** - Get quizzes, start/save/submit attempts (5 tools)
- ✅ **Enrollment** - Enrol/unenrol users from courses (2 tools)

### ✅ Phase 2 Complete (Critical Student/Teacher Functions):
- ✅ **Assignment Submissions** - Save drafts and submit for grading (3 tools)
- ✅ **Grading** - Grade assignments and update gradebook (2 tools)

### 🔜 Phase 3 (Next Priority):
- **Content Management** - Upload files, create resources
- **Badge Management** - Award and manage badges
- **Advanced Forum** - Update/delete posts, manage subscriptions
- **Advanced Calendar** - Update events, manage recurring events

## 🧪 Development

### Project Structure
```
moodle-mcp-server/
├── src/moodle_mcp/
│   ├── server.py           # FastMCP instance
│   ├── main.py             # Entry point
│   ├── core/               # Core infrastructure
│   │   ├── client.py       # API client
│   │   ├── config.py       # Configuration
│   │   └── exceptions.py   # Exceptions
│   ├── models/             # Pydantic models
│   │   └── base.py         # Base models
│   ├── tools/              # Tool implementations
│   │   ├── site.py
│   │   ├── courses.py
│   │   ├── users.py
│   │   ├── messages.py     # READ + WRITE
│   │   ├── calendar.py     # READ + WRITE
│   │   └── forums.py       # READ + WRITE
│   └── utils/              # Shared utilities
│       ├── formatting.py
│       ├── error_handling.py  # Includes write safety
│       └── api_helpers.py
├── tests/
│   └── test_tools_integration.py
├── .env.example
├── pyproject.toml
├── TASKS.md                # Complete function inventory
├── WRITE_OPERATIONS_SAFETY.md
└── README.md
```

### Adding New Tools

See [WRITE_OPERATIONS_SAFETY.md](./WRITE_OPERATIONS_SAFETY.md) for comprehensive guide on implementing write operations.

**For READ operations:**
```python
@mcp.tool(
    name="moodle_my_read_tool",
    description="Description with examples",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_my_read_tool(
    param: str = Field(description="Parameter"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN),
    ctx: Context = None
) -> str:
    moodle = get_moodle_client(ctx)
    data = await moodle._make_request('api_function', {})
    return format_response(data, "Title", format)
```

**For WRITE operations:**
```python
@mcp.tool(
    name="moodle_my_write_tool",
    description="WRITE OPERATION - only works on whitelisted courses",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,  # True if deletes data
        "idempotentHint": False,
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')  # SAFETY: Add this!
async def moodle_my_write_tool(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    data: str = Field(description="Data to write"),
    ctx: Context = None
) -> str:
    moodle = get_moodle_client(ctx)
    result = await moodle._make_request('api_function', {'data': data})
    return f"✅ Operation successful: {result}"
```

## 🐛 Troubleshooting

### Connection Issues
- Verify `MOODLE_DEV_URL` / `MOODLE_PROD_URL` is correct
- Check network connectivity to Moodle server
- Ensure Web Services are enabled in Moodle

### Authentication Errors
- Verify `MOODLE_DEV_TOKEN` / `MOODLE_PROD_TOKEN` is valid
- Check token has required permissions
- Ensure user account is active

### Write Operation Blocked
```
Write operation blocked for safety:
Write operations are only allowed on whitelisted courses in DEV mode.
```

**Solution:** Add course to whitelist:
```bash
MOODLE_DEV_COURSE_WHITELIST=7299,YOUR_COURSE_ID
```

### Permission Errors
- Some tools require specific capabilities
- Verify user role has necessary permissions
- Check course-level permissions

## 📚 Documentation

- **[TASKS.md](./TASKS.md)** - Complete API function inventory and roadmap
- **[WRITE_OPERATIONS_SAFETY.md](./WRITE_OPERATIONS_SAFETY.md)** - Write operation implementation guide
- **[WRITE_SAFETY_SUMMARY.md](./WRITE_SAFETY_SUMMARY.md)** - Quick reference for developers

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please:
1. Follow existing code style
2. Use `@require_write_permission` for write operations
3. Add comprehensive docstrings
4. Include error handling
5. Test with live Moodle instance
6. Update documentation

## 🙏 Acknowledgments

- Built with [FastMCP](https://gofastmcp.com)
- Follows [MCP best practices](https://modelcontextprotocol.io)
- Integrates with [Moodle Web Services API](https://docs.moodle.org/dev/Web_services)

---

**Status:** ✅ Production Ready (58 tools with enterprise safety features)
**Coverage:** 35% of Moodle Web Services API (58/167 functions)
**Phase 1:** ✅ Complete (Quiz + Enrollment - 7 tools)
**Phase 2:** ✅ Complete (Assignment Submissions + Grading - 5 tools)
**Next Phase:** Content Management, Badges, Advanced Features
